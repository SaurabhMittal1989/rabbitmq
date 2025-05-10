import threading
import time
from typing import Callable, Any

from apps.client_side_consumer_balancer.ConfigurationManagerClient import IConfigurationManagerClient
from apps.client_side_consumer_balancer.Follower import IFollower
from apps.client_side_consumer_balancer.Leader import ILeader
from apps.client_side_consumer_balancer.MessageQueueClient import IMessageQueueClient
from apps.client_side_consumer_balancer.Register import IRegister
from apps.client_side_consumer_balancer.Singleton import singleton


@singleton
class ConsumerSideClientBalancer:

    def __init__(self, register: IRegister, leader: ILeader, follower: IFollower):
        self.register = register
        self.leader = leader
        self.follower = follower

    def balance(self):
        self.register.register()
        leader_thread = self.start_thread(self.leader.leader_callback)
        follower_thread = self.start_thread(self.follower.follower_callback)
        leader_thread.join()
        follower_thread.join()

    def start_thread(self, func: Callable, *args, **kwargs):
        perpetual_run_func = self.perpetual_running_job(func, *args, **kwargs)
        thread = threading.Thread(target=perpetual_run_func)
        # Start the thread
        thread.start()
        return thread

    @staticmethod
    def perpetual_running_job(func_obj: Callable, *args, **kwargs) -> Callable:
        def func(*args, **kwargs):
            while True:
                try:
                    func_obj(*args, **kwargs)
                except Exception as e:
                    message = f"The {func_obj.__name__} process has stopped with exception: {e}"
                    print(message)
                    time.sleep(10)

        return func

if __name__ =="__main__":
    # fixtures
    class Leader(ILeader):

        def leader_callback(self):
            print(f"I am the leader. Thread ID: {threading.get_ident()}")
            time.sleep(2)
            print("Leader exiting")

    class Follower(IFollower):
        def follower_callback(self):
            print(f"I am the follower. Thread ID: {threading.get_ident()}")
            time.sleep(2)
            print("Follower exiting")

    class Register(IRegister):
        def register(self):
            print(f"Registered. Thread ID: {threading.get_ident()}")
            time.sleep(2)
            print("Register exiting")

    class ConfigurationManagerClient(IConfigurationManagerClient):
        def register(self) -> bool:
            pass

        def get_value(self, key: str, value) -> Any:
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

        def publish(self, topic: str, message: Any) -> bool:
            pass

        def subscribe(self, topic: str) -> bool:
            pass

        def __init__(self):
            pass

    config_client = ConfigurationManagerClient()
    message_queue_client = MessageQueueClient()
    leader = Leader(configuration_manager_client=config_client, message_queue_client=message_queue_client)
    follower = Follower(configuration_manager_client=config_client, message_queue_client=message_queue_client)
    register = Register(configuration_manager_client=config_client)

    # test 1: Singleton:
    balancer1 = ConsumerSideClientBalancer(leader=leader, follower=follower, register=register)
    balancer2 = ConsumerSideClientBalancer(leader=leader, follower=follower, register=register)
    assert (balancer1 is balancer2)

    # test 2: balancer1 will start
    balancer1.balance()
