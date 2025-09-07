import threading

from apps.client_side_consumer_balancer.FollowerCallback import FollowerCallback
from apps.client_side_consumer_balancer.redisimpl.RedisConfigurationManagerClient import \
    RedisConfigurationManagerClient
from apps.client_side_consumer_balancer.rabbitmq.RabbitMQMessageQueueClient import RabbitMQMessageQueueClient
from apps.client_side_consumer_balancer.config import *
import time


def callback(ch, method, properties, body):
    """Process function : on message callback"""
    time.sleep(4)
    try:
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"Error acknowledging message: {e}. message: {body}")

    print(f"Received and Acknowledged: {threading.current_thread().name} :  {body}")


config_client = RedisConfigurationManagerClient(host=REDIS_HOST, port=REDIS_PORT)
queue_client = RabbitMQMessageQueueClient(host=RABBIT_MQ_HOST, exchange_name=RABBIT_MQ_EXCHANGE_NAME,
                                          callback=callback)
follower = FollowerCallback(configuration_manager_client=config_client, message_queue_client=queue_client,
                            config_key=CONFIG_KEY)
follower.run()

while True:
    # Keep the main thread alive, or do other work
    time.sleep(1)
# follower.message_queue_client.subscribe_to_queue(queue_name=RABBIT_MQ_QUEUE_NAME)
pass