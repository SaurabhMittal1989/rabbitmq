import json
import time
from typing import Any, Callable

import pika

from apps.client_side_consumer_balancer.Message import Message


class RabbitMQMessageQueueClient:

    def __init__(self, host):
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
        self.channel = connection.channel()

    def publish(self, exchange_name: str, message: Message) -> bool:
        """
        Publish a message to RabbitMQ with routing key and headers.

        Args:
            exchange_name: The name of the exchange to publish to
            message: Message object containing payload, routing key and headers

        Returns:
            bool: True if message was published successfully, False otherwise
        """
        try:
            properties = pika.BasicProperties(
                headers=message.headers
            )

            # Convert payload to string if it's not already
            body = json.dumps(message.payload) if not isinstance(message.payload, (str, bytes)) else message.payload

            self.channel.basic_publish(
                exchange=exchange_name,
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



    def subscribe(self, queue: str, callback: Callable) -> bool:
        """
        Subscribe to a specific queue and set up a callback for message processing.
    
        Args:
            queue: The name of the queue to subscribe to
            callback: The callback function to process received messages
    
        Returns:
            bool: True if subscription is successful, False otherwise
        """
        try:
            self.channel.basic_consume(
                queue=queue,
                on_message_callback=callback,
                auto_ack=True
            )
            print(f'Subscribed to queue: {queue}')
            self.channel.start_consuming()
            return True

        except Exception as e:
            print(f"Error subscribing to queue: {e}")
            return False
        finally:
            self.close()


if __name__ == "__main__":
    """
    Example usage of RabbitMQ client with a local server.
    """
    # Initialize client
    client = RabbitMQMessageQueueClient(host='localhost')

    # Define example exchange and queue
    exchange_name = "my_exchange"
    queue_name = "q0001"

    # Create a message
    message = Message(
        payload={"test": "Hello RabbitMQ!"},
        routing_key=1,
        headers={"content_type": "application/json"}
    )

    # Publish message
    client.publish(exchange_name, message)


    # Define callback for received messages
    def process_message(ch, method, properties, body):

            print(f"Received message: {body}")

            # Subscribe to queue
    client.subscribe(queue_name, process_message)

    # Close connection when done
    client.close()
