import json
import time
from typing import Any, Callable

import pika

from apps.client_side_consumer_balancer.Message import Message
from apps.client_side_consumer_balancer.MessageQueueClient import IMessageQueueClient


class RabbitMQMessageQueueClient (IMessageQueueClient):

    def __init__(self, host: str, exchange_name: str, callback: Callable ):
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
        self.channel = connection.channel()
        self.exchange_name = exchange_name
        self.callback = callback


    def publish(self,  message: Message) -> bool:
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
        try:
            self.channel.basic_consume(
                queue=queue_name,
                on_message_callback=self.callback,
                auto_ack=True
            )
            self.channel.start_consuming()
            print(f'Subscribed to queue: {queue_name}')
            return True
        except Exception as e:
            print(f"Error subscribing to queue {queue_name}: {e}")
            return False

    def unsubscribe_from_queue(self, queue_name):
        try:
            self.channel.basic_cancel(consumer_tag=queue_name)
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

            # Subscribe to queue
    # Initialize client
    client = RabbitMQMessageQueueClient(host='localhost',exchange_name = "my_exchange", callback=process_message)

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
        client.publish( message)





    client.subscribe_to_queue(queue_name)

    # Close connection when done
    client.close()
