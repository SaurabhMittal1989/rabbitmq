import signal
import time  # For sleep or time management during operations
import threading  # For multithreading (e.g., balancing thread, leader thread, follower thread)
import uuid  # For generating unique identifiers (e.g., for configuration keys)
from typing import Any, Callable  # For type hints in methods and callbacks

import redis

from apps.client_side_consumer_balancer.ConfigurationManagerClient import IConfigurationManagerClient
from apps.client_side_consumer_balancer.ConsumerSideClientBalancer import ConsumerSideClientBalancer
from apps.client_side_consumer_balancer.FollowerCallback import IFollowerCallback
from apps.client_side_consumer_balancer.LeaderCallback import ILeaderCallback
from apps.client_side_consumer_balancer.MessageQueueClient import IMessageQueueClient
from apps.client_side_consumer_balancer.Register import IRegister
from apps.client_side_consumer_balancer.aws_handler.consumer_meta_data import IAwsMetaDataHandler
from apps.client_side_consumer_balancer.config import REDIS_HOST, REDIS_PORT, LOCK_KEY, LEASE_DURATION_MS, \
    RENEWAL_INTERVAL_S, UUID
from apps.client_side_consumer_balancer.redisimpl.RedisConfigurationConsistentHashing import  ClusterManager
from apps.client_side_consumer_balancer.redisimpl.RedisLeaderElector import RedisLeaderElector
from apps.client_side_consumer_balancer.redisimpl.RedisRegister import Register


class AwsMetaData(IAwsMetaDataHandler):

    def get_active_consumers(self):
        return ['foo123', 'bar123']

def leader_callback():
    print("[LEADER] Watching for Configuration changes...")
    aws_meta = AwsMetaData()
    cluster_manager = ClusterManager(aws_meta_data=aws_meta)
    cluster_manager.run_leader_tasks()
    time.sleep(5)

# TODO how to use elect leader here?
def elect_leader(leader_callback: Callable):
    node_id = str(uuid.uuid4())  # Generate a unique ID for this instance
    print(f"Starting instance with Node ID: {node_id}")

    try:
        r_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        r_client.ping()
        print("Successfully connected to Redis.")
    except redis.exceptions.ConnectionError as e:
        print(f"Could not connect to Redis: {e}")
        return

    elector = RedisLeaderElector(
        redis_client=r_client,
        lock_key=LOCK_KEY,
        node_id=node_id,
        lease_duration_ms=LEASE_DURATION_MS,
        renewal_interval_s=RENEWAL_INTERVAL_S,
        leader_callback=leader_callback
    )

    elector.run_election_loop()
    print(f"Node {node_id}: Application finished.")




class Leader(ILeaderCallback):

    def run(self):
        # print(f"I am the leader. Thread ID: {threading.get_ident()}")
        elect_leader(leader_callback=leader_callback)




class Follower(IFollowerCallback):
    def __init__(self,
                 configuration_manager_client: IConfigurationManagerClient,
                 message_queue_client: IMessageQueueClient,
                 config_key: str):
        self.configuration_manager_client = configuration_manager_client
        self.message_queue_client = message_queue_client
        self.config_key = config_key
        self.current_subscribed_queues: set = set()
        self.notification_thread = None
        self.is_first_time = True

    def run(self):
        # print(f"I am the follower. Thread ID: {threading.get_ident()}")
        print("[CONSUMER] Consuming Messages")
        time.sleep(2)


# class Register(IRegister):
#     def register(self):
#
#         #TODO
#         membership_key = LOCK_KEY
#         # r_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
#         # #setting membership
#         # acquired = r_client.set(self.lock_key, self.node_id, nx=True, px=self.lease_duration_ms)
#         # print(f"Registered for Leader Election. Thread ID: {threading.get_ident()}")
#         # #register
#         #
#         # # renew
#         # renewed = r_client.evalsha(self._renew_script_sha, 1, self.lock_key, self.node_id, self.lease_duration_ms)
#
#         time.sleep(2)


class ConfigurationManagerClient(IConfigurationManagerClient):
    def register(self) -> bool:
        pass

    def get_value(self, key: str, default_value: Any = None) -> Any:
        pass

    def set_value(self, key: str, value: Any) -> bool:
        pass

    def delete_value(self, key: str) -> bool:
        pass

    def has_value(self, key: str) -> bool:
        pass

    def register_watch(self, key: str, callback: Callable[[str, Any, Any], None]) -> str:
        pass

    def deregister_watch(self, watch_id: str) -> bool:
        pass

    def __init__(self):
        pass


class MessageQueueClient(IMessageQueueClient):
    def connect(self) -> bool:
        pass

    def close(self) -> None:
        pass

    def publish(self, message: Any) -> bool:
        pass

    def subscribe(self, topic: str) -> bool:
        pass

    def unsubscribe_from_queue(self, queue_name: str) -> bool:
        pass

    def subscribe_to_queue(self, queue_name: str) -> bool:
        pass

    def __init__(self):
        pass


if __name__ == "__main__":
    stop_event = threading.Event()

    # Signal handling in main thread
    def signal_handler(signum, frame):
        print(f"Signal {signum} received. Shutting down...")
        stop_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

config_client = ConfigurationManagerClient()
message_queue_client = MessageQueueClient()
leader = Leader(configuration_manager_client=config_client, message_queue_client=message_queue_client)
follower = Follower(configuration_manager_client=config_client, message_queue_client=message_queue_client,
                    config_key=UUID)
# register = Register(configuration_manager_client=config_client)
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
register = Register(redis_client, UUID)

balancer1 = ConsumerSideClientBalancer(leader=leader, follower=follower, register=register)
try:
    balancer1.balance()
except Exception as e:
    print(e)
finally:
    register.stop()
