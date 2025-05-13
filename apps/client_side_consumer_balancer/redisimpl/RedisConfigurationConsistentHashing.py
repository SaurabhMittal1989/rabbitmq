import redis
import os
import threading
import uhashring
from apps.client_side_consumer_balancer.aws_handler.consumer_meta_data import IAwsMetaDataHandler
from apps.client_side_consumer_balancer.config import *
import logging
import json
import requests
import urllib.parse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
RABBITMQ_USER = 'guest' # Use appropriate credentials
RABBITMQ_PASS = 'guest'
QUEUE_CONFIG_KEY = 'cluster:config:assignments' # Hash: {consumer_id: json_list_of_queues}
QUEUE_PREFIX_FILTER = None
class ClusterManager:
    def __init__(self, aws_meta_data: IAwsMetaDataHandler):
        self.aws_meta_data = aws_meta_data
        self.redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB_NUMBER, decode_responses=True)
        self.manager_id = f"{os.uname().nodename}-{os.getpid()}" # Unique ID for this manager instance
        self._is_leader = False
        self._stop_event = threading.Event()
        self.hash_ring = uhashring.HashRing()


    def _get_active_consumers(self):
        return self.aws_meta_data.get_active_consumers()

    def _get_available_queues(self):
        """Get list of queues from RabbitMQ Management API."""
        # Construct the URL safely
        vhost_encoded = urllib.parse.quote('/', safe='')
        url = f"http://{RABBIT_MQ_HOST}:15672/api/queues/{vhost_encoded}"
        try:
            response = requests.get(url, auth=(RABBITMQ_USER, RABBITMQ_PASS), timeout=5)
            response.raise_for_status()  # Raise exception for bad status codes
            queues_data = response.json()
            # Ensure queues_data is a list
            if not isinstance(queues_data, list):
                logger.error(f"[{self.manager_id}] Unexpected response format from RabbitMQ API: {type(queues_data)}")
                return []

            queue_names = [q['name'] for q in queues_data if 'name' in q]

            if QUEUE_PREFIX_FILTER:
                queue_names = [q for q in queue_names if q.startswith(QUEUE_PREFIX_FILTER)]

            logger.info(f"[{self.manager_id}] Available queues ({len(queue_names)}): {sorted(queue_names)}")
            return sorted(queue_names)  # Sort for consistent hashing input
        except requests.exceptions.RequestException as e:
            logger.error(f"[{self.manager_id}] Error fetching queues from RabbitMQ API ({url}): {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"[{self.manager_id}] Error decoding RabbitMQ API response: {e}")
            return []
        except Exception as e:
            logger.error(f"[{self.manager_id}] Unexpected error fetching queues: {e}")
            return []

    def _calculate_assignments(self, consumers, queues):
        """Calculate queue assignments using consistent hashing."""
        assignments = {consumer_id: [] for consumer_id in consumers}
        if not consumers:
            logger.warning(f"[{self.manager_id}] No active consumers found. Cannot assign queues.")
            return assignments # Empty assignments

        # Update hash ring nodes (consumers)
        # Check if nodes changed to avoid rebuilding unnecessarily
        current_nodes = set(self.hash_ring.get_nodes())
        new_nodes = set(consumers)
        if current_nodes != new_nodes:
            logger.info(f"[{self.manager_id}] Updating hash ring nodes from {current_nodes} to {new_nodes}")
            self.hash_ring = uhashring.HashRing(nodes=consumers)
        else:
             logger.debug(f"[{self.manager_id}] Hash ring nodes unchanged.")


        # Assign queues to nodes
        for queue in queues:
            assigned_node = self.hash_ring.get_node(queue)
            if assigned_node in assignments:
                assignments[assigned_node].append(queue)
            else:
                # Should not happen if hash_ring is correctly initialized
                logger.error(f"[{self.manager_id}] Queue '{queue}' assigned to non-existent consumer '{assigned_node}' by hash ring!")

        logger.info(f"[{self.manager_id}] Calculated assignments:")
        for consumer, assigned_q in assignments.items():
            logger.info(f"  - {consumer}: {assigned_q}")

        return assignments

    def _update_redis_config(self, assignments):
        """Update the queue assignments configuration in Redis."""
        try:
            # Use a pipeline for efficiency
            pipe = self.redis_client.pipeline()
            # Get current assignments to find consumers to remove
            current_config = self.redis_client.hgetall(QUEUE_CONFIG_KEY)
            consumers_in_config = set(current_config.keys())
            consumers_with_assignments = set(assignments.keys())

            # Set assignments for active consumers
            for consumer_id, queues in assignments.items():
                queues_json = json.dumps(sorted(queues)) # Store sorted list as JSON
                # Only update if different
                if current_config.get(consumer_id) != queues_json:
                    logger.info(f"[{self.manager_id}] Updating config for {consumer_id}")
                    pipe.hset(QUEUE_CONFIG_KEY, consumer_id, queues_json)
                else:
                    logger.debug(f"[{self.manager_id}] Config for {consumer_id} unchanged.")

            # Remove consumers from config that are no longer active/assigned
            consumers_to_remove = consumers_in_config - consumers_with_assignments
            if consumers_to_remove:
                 logger.info(f"[{self.manager_id}] Removing inactive consumers from config: {consumers_to_remove}")
                 pipe.hdel(QUEUE_CONFIG_KEY, *consumers_to_remove)

            pipe.execute()
            logger.info(f"[{self.manager_id}] Redis configuration updated successfully.")
        except Exception as e:
            logger.error(f"[{self.manager_id}] Error updating Redis configuration: {e}")


    def run_leader_tasks(self):
        """Main loop executed when this instance is the leader."""

        active_consumers = self._get_active_consumers()
        available_queues = self._get_available_queues()

        # Add a delay if no consumers are found before trying to assign
        if not active_consumers:
            logger.warning(f"[{self.manager_id}] No active consumers detected. Pausing assignment.")
            # Don't wipe assignments immediately, wait a cycle perhaps?
            # Or maybe wipe assignments if consistently no consumers? For now, just log and skip calculation.
        else:
            assignments = self._calculate_assignments(active_consumers, available_queues)
            self._update_redis_config(assignments)


class AwsMetaData(IAwsMetaDataHandler):

    def get_active_consumers(self):
        return ['foo123', 'bar123']


if __name__ == '__main__':
    aws_meta = AwsMetaData()
    cluster_manager = ClusterManager(aws_meta_data=aws_meta)
    cluster_manager.run_leader_tasks()