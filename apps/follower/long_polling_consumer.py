"""
QueueConsumerLongPoll implements a Redis-based queue consumer that uses long polling
to monitor configuration changes. It maintains subscriptions to multiple queues and
dynamically updates these subscriptions based on configuration changes in Redis.
"""

from random import randint

import redis
import json
import threading
import time
import uuid

class QueueConsumerLongPoll:
    def __init__(self, follower_id: str, redis_host='localhost', redis_port=6379, redis_db=0):
        """Initialize a new queue consumer with long polling capabilities.
        
        Args:
            follower_id: Unique identifier for this consumer
            redis_host: Redis server hostname
            redis_port: Redis server port
            redis_db: Redis database number
        """
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, db=redis_db, decode_responses=True)
        self.config_key = f"consumer:queues_config:{follower_id}"
        self.signal_key = f"consumer:config_update_signal:{follower_id}" # Key for BRPOP
        self.current_subscribed_queues = set()
        self.current_config_version = None
        self.is_running = True
        self.poll_timeout = 30 # Seconds for BRPOP timeout

        # Initial load of configuration
        self._load_and_apply_config(reason="initial_startup")

        # Start polling in a separate thread
        self.polling_thread = threading.Thread(target=self._long_poll_for_config_changes, daemon=True)
        self.polling_thread.start()

    def _fetch_config_data(self):
        config_json = self.redis_client.get(self.config_key)
        if config_json:
            try:
                return json.loads(config_json)
            except json.JSONDecodeError:
                print(f"Error: Could not decode JSON from '{self.config_key}'")
        return None

    def _load_and_apply_config(self, reason="unknown", expected_version=None):
        print(f"Attempting to load and apply config (reason: {reason})...")
        config_data = self._fetch_config_data()

        if not config_data:
            print(f"No configuration found for key '{self.config_key}' or failed to parse.")
            new_queues_to_subscribe = set()
            new_config_version = None
        else:
            new_queues_to_subscribe = set(config_data.get("queues", []))
            new_config_version = config_data.get("version", None)

        # If an expected_version was provided by a signal, we might choose to only update if it matches.
        # For simplicity here, we'll always apply if different from current.
        if new_config_version != self.current_config_version or self.current_config_version is None:
            print(f"New config version '{new_config_version}' (current: '{self.current_config_version}'). Applying changes.")
            # ... (same subscription logic as before) ...
            queues_to_add = new_queues_to_subscribe - self.current_subscribed_queues
            queues_to_remove = self.current_subscribed_queues - new_queues_to_subscribe
            for q_name in queues_to_add: self._subscribe_to_queue(q_name)
            for q_name in queues_to_remove: self._unsubscribe_from_queue(q_name)

            self.current_subscribed_queues = new_queues_to_subscribe
            self.current_config_version = new_config_version
            print(f"Applied config version '{self.current_config_version}'. Current queues: {self.current_subscribed_queues}")
        else:
            print(f"Fetched config version '{new_config_version}' is same as current. No changes applied.")

    def _subscribe_to_queue(self, queue_name):
        print(f"SIM: Subscribing to queue: {queue_name}")
    def _unsubscribe_from_queue(self, queue_name):
        print(f"SIM: Unsubscribing from queue: {queue_name}")

    def _long_poll_for_config_changes(self):
        while self.is_running:
            try:
                print(f"Long polling on '{self.signal_key}' with timeout {self.poll_timeout}s...")
                # BRPOP returns a tuple (list_name, value) or None on timeout
                message = self.redis_client.brpop(self.signal_key, timeout=self.poll_timeout)

                if not self.is_running:
                    break # Check immediately after blocking call

                if message:
                    list_name, signal_data = message
                    print(f"Received signal on '{list_name}': {signal_data}. Reloading config.")
                    # signal_data could be the new version, or just "update"
                    self._load_and_apply_config(reason="signal_received", expected_version=signal_data if signal_data != "update" else None)
                else: # Timeout
                    print("Long poll timed out. Proactively reloading config as a safety measure.")
                    # This periodic reload on timeout acts as a fallback/resync mechanism
                    self._load_and_apply_config(reason="poll_timeout_resync")

            except redis.exceptions.ConnectionError as e:
                print(f"Redis connection error during long poll: {e}. Retrying in 5s.")
                time.sleep(5)
            except Exception as e:
                print(f"Unexpected error in long poll loop: {e}. Retrying in 5s.")
                time.sleep(5) # Avoid busy-looping on unexpected errors
        print("Long polling thread stopped.")


    def stop(self):
        """Stop the consumer, unsubscribe from all queues and cleanup resources.
        Interrupts the long polling thread and waits for it to complete.
        """
        print("Stopping consumer (long poll)...")
        self.is_running = False
        # To interrupt BRPOP if it's blocking:
        # One way is to push a dummy message to the signal list from another thread/connection
        # Or, if the client library supports it, close the connection, which should raise an error in BRPOP.
        # For simplicity, we'll rely on the timeout or the next loop iteration checking self.is_running.
        # A more robust stop would actively unblock BRPOP.
        try:
            # This is a trick to potentially unblock BRPOP if it's waiting.
            # It's not guaranteed to be immediate but helps.
            # Ensure this client is not the one blocked in BRPOP itself, use a new one or manage carefully.
            temp_client = redis.Redis(host=self.redis_client.connection_pool.connection_kwargs.get('host', 'localhost'),
                                      port=self.redis_client.connection_pool.connection_kwargs.get('port', 6379),
                                      db=self.redis_client.connection_pool.connection_kwargs.get('db',0))
            temp_client.lpush(self.signal_key, "shutdown_signal")
            temp_client.close()
        except Exception as e:
            print(f"Minor error trying to send shutdown signal: {e}")


        if self.polling_thread.is_alive():
            self.polling_thread.join(timeout=self.poll_timeout + 5) # Wait a bit longer than poll timeout

        for q_name in list(self.current_subscribed_queues):
            self._unsubscribe_from_queue(q_name)
        self.current_subscribed_queues.clear()
        print("Consumer (long poll) stopped.")

# --- Config Updater (for long polling) ---
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--follower_id',  default=randint(10000, 100000))
    args = parser.parse_args()
    consumer = QueueConsumerLongPoll(follower_id=args.follower_id) # Assuming Redis DB 0

    print(f"Consumer started. It will react to changes in the Redis key 'consumer:queues_config:{args.follower_id}'.")

    try:
        while True:
            # Keep the main thread alive, or do other work
            time.sleep(1)
            # In a real app, this might be where your consumer processes messages from its subscribed queues
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        consumer.stop()