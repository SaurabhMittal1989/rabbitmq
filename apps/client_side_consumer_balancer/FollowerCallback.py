import queue
import threading

from apps.client_side_consumer_balancer.ConfigurationManagerClient import IConfigurationManagerClient
from apps.client_side_consumer_balancer.FollowerBusinessLogic import FollowerBusinessLogic
from apps.client_side_consumer_balancer.MessageQueueClient import IMessageQueueClient
from apps.client_side_consumer_balancer.config import *
from apps.client_side_consumer_balancer.rabbitmq.RabbitMQDynamicConsumerClientThreadSafe import create_consumer, \
    queue_monitor

# TODO rename it to Consumer and IConsumer
class IFollowerCallback:
    pass

class FollowerCallback(IFollowerCallback):
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
        # One thread listens to configuration changes:  Start listening for notifications in a separate thread
        self.notification_thread = threading.Thread(target=self.listen_for_config_changes,
                                                    daemon=True)
        self.notification_thread.start()

        # process messages
        
        #self.message_queue_client.subscribe()

    def _fetch_config(self) -> set:
        config_data = self.configuration_manager_client.get_value(self.config_key)
        if config_data:
            return set(config_data.get("queues", []))

        return set()

    def listen_for_config_changes(self):
        # Using a pub sub model
        # Construct the keyspace notification channel name
        # __keyspace@<db>__:<key>
        notification_channel = f"__keyspace@{REDIS_DB_NUMBER}__:{self.config_key}"
        self.configuration_manager_client.pubsub.subscribe(notification_channel)
        print(f"Listening for changes on Redis key: '{self.config_key}' via channel '{notification_channel}'")


        # create the Rabbit MQ Queue Client
        dynamic_consumer = create_consumer(host=RABBIT_MQ_HOST, callback=FollowerBusinessLogic().process_job_callback)
        # Give the consumer a moment to connect
        time.sleep(3)  # Slightly longer for initial setup

        # Start the simulation of queue changes in a separate thread
        notify_consumer_message_queue = queue.Queue()
        monitor_thread = threading.Thread(target=queue_monitor, args=(dynamic_consumer, notify_consumer_message_queue))
        monitor_thread.start()

        # Initial load of configuration [to go away in polling strategy]
        if self.is_first_time:
            self._load_and_apply_config(event_type="initial_load", notify_consumer_message_queue=notify_consumer_message_queue)
            self.is_first_time = False

        for message in self.configuration_manager_client.pubsub.listen(): # blocking call
            # message format: {'type': 'message', 'pattern': None, 'channel': b'__keyspace@0__:consumer:queues_config', 'data': b'set'}
            print(f"Received notification: {message}")
            if message['type'] == 'message':
                event_type = message['data']  # e.g., "set", "del"
                key_affected = message['channel'].split(':', 1)[
                    1]  # Extract key from the channel name if using psubscribe, not needed here

                if event_type in ["set", "hset"]:  # Or other relevant commands like 'hset' if using hashes
                    self._load_and_apply_config(event_type, notify_consumer_message_queue)
                elif event_type == "del":
                    print(f"Configuration key '{self.config_key}' was deleted.")
                    # Decide what to do: unsubscribe all or revert to a default
                    self._load_and_apply_config(event_type, notify_consumer_message_queue)  # This will fetch an empty config
                # You might also want to handle 'expired' if your keys can expire

    def _load_and_apply_config(self, event_type: str, notify_consumer_message_queue):
        print(f"Config change detected (event: {event_type}), reloading...")
        new_queues_to_subscribe: set = self._fetch_config()

        notify_consumer_message_queue.put(new_queues_to_subscribe)

        self.current_subscribed_queues = new_queues_to_subscribe
        print(f"Current subscribed queues: {self.current_subscribed_queues}")

    def stop(self):
        print("Stopping consumer...")

        # Unsubscribe from all queues before exiting
        for q_name in list(self.current_subscribed_queues):  # Iterate over a copy
            self.message_queue_client.unsubscribe_from_queue(q_name)
        self.current_subscribed_queues.clear()
        print("Consumer stopped.")
        
        
if __name__ == "__main__":
    from apps.client_side_consumer_balancer.redisimpl.RedisConfigurationManagerClient import \
        RedisConfigurationManagerClient
    from apps.client_side_consumer_balancer.rabbitmq.RabbitMQMessageQueueClient import RabbitMQMessageQueueClient
    from apps.client_side_consumer_balancer.config import *
    import time


    def consumer_callback(ch, method, properties, body):
        print("hello world")
        time.sleep(1)
    
    
    config_client = RedisConfigurationManagerClient(host=REDIS_HOST, port=REDIS_PORT)
    queue_client = RabbitMQMessageQueueClient(host=RABBIT_MQ_HOST, exchange_name=RABBIT_MQ_EXCHANGE_NAME, callback=consumer_callback)
    follower = FollowerCallback(configuration_manager_client=config_client, message_queue_client=queue_client, config_key=CONFIG_KEY)
    follower.run()


    while True:
        # Keep the main thread alive, or do other work
        time.sleep(1)
    # follower.message_queue_client.subscribe_to_queue(queue_name=RABBIT_MQ_QUEUE_NAME)
    pass
    



