import json
import threading
import uuid
from typing import Callable

import pika

from apps.client_side_consumer_balancer.Message import Message
from apps.client_side_consumer_balancer.MessageQueueClient import IMessageQueueClient
from apps.client_side_consumer_balancer.config import RABBITMQ_PREFETCH_COUNT


class RabbitMQMessageQueueClient(IMessageQueueClient):

    def __init__(self, host: str, exchange_name: str, callback: Callable):
        self.consumer_tags = {}
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
        self.channel = self.connection.channel()
        self.exchange_name = exchange_name
        self.callback = callback
        self.subscription_threads = []
        self.unsubscription_threads = []

    def publish(self, message: Message) -> bool:
        """
        Publish a message to RabbitMQ with the routing key and headers.

        Args:
            message: Message object containing payload, routing key and headers

        Returns:
            bool: True if the message was published successfully, False otherwise
        """
        try:
            properties = pika.BasicProperties(
                headers=message.headers
            )

            # Convert payload to string if it's not already
            body = json.dumps(message.payload) if not isinstance(message.payload, (str, bytes)) else message.payload

            self.channel.basic_publish(
                exchange=self.exchange_name,
                routing_key=message.routing_key,
                body=body,
                properties=properties
            )

            print(f'Published: exchange={exchange_name}, routing_key={message.routing_key}, headers={message.headers}')
            return True

        except Exception as e:
            print(f"Error publishing message: {e}")
            return False

    def close(self) -> None:
        """
        Disconnect from the message queue.
        """
        if self.channel:
            try:
                self.channel.close()
            except Exception as e:
                print(f"Error closing channel: {e}")

        if self.channel.is_open:
            try:
                self.channel.connection.close()
            except Exception as e:
                print(f"Error closing connection: {e}")

    def subscribe_to_queue(self, queue_name):
        """Make it a non blocking queue registration"""
        subscription_thread = threading.Thread(target=self.subscribe, args=(queue_name,))
        subscription_thread.daemon = True
        subscription_thread.start()
        self.subscription_threads.append(subscription_thread)

    def subscribe(self, queue_name):

        try:
            consumer_tag = uuid.uuid4().hex
            self.channel.basic_consume(
                queue=queue_name,
                on_message_callback=self.callback,
                consumer_tag=consumer_tag
            )
            self.consumer_tags[queue_name] = consumer_tag
            self.channel.basic_qos(prefetch_count=RABBITMQ_PREFETCH_COUNT)
            if not getattr(self, '_consuming', False):
                self._consuming = True
                self.channel.start_consuming()
            print(f'Subscribed to queue: {queue_name}')
            return True
        except Exception as e:
            print(f"Error subscribing to queue {queue_name}: {e}")
            return False

    def unsubscribe_from_queue(self, queue_name):
        """Make it a non blocking queue registration"""
        unsubscription_thread = threading.Thread(target=self.unsubscribe, args=(queue_name,))
        unsubscription_thread.daemon = True
        unsubscription_thread.start()
        self.unsubscription_threads.append(unsubscription_thread)
        
    def unsubscribe(self, queue_name):
        try:
            self.channel.basic_cancel(consumer_tag=self.consumer_tags[queue_name])
            print(f'Unsubscribed from queue: {queue_name}')
            return True
        except Exception as e:
            print(f"Error unsubscribing from queue {queue_name}: {e}")
            return False


if __name__ == "__main__":
    """
    Example usage of RabbitMQ client with a local server.
    """

    # Define callback for received messages
    def process_message(ch, method, properties, body):
        print(f"Received message: {body}")

    # Initialize client
    client = RabbitMQMessageQueueClient(host='localhost', exchange_name="my_exchange", callback=process_message)

    # Define example exchange and queue
    exchange_name = "my_exchange"
    queue_name = "q0001"

    # Create a message
    message = Message(
        payload={"test": "Hello RabbitMQ!"},
        routing_key='1',
        headers={"content_type": "application/json"}
    )

    # Publish message
    for i in range(100):
        m = message.routing_key = f"{i}"
        client.publish(message)

    client.subscribe_to_queue(queue_name)

    # Close connection when done
    client.close()
