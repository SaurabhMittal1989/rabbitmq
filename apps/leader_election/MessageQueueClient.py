from abc import ABC, abstractmethod
from typing import Any, Optional


class IMessageQueueClient(ABC):
    """
    Abstract base class defining the interface for a message queue client.
    """

    @abstractmethod
    def connect(self) -> bool:
        """
        Establish a connection to the message queue.

        Returns:
            bool: True if the connection is successful, False otherwise
        """
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        """
        Disconnect from the message queue.
        """
        raise NotImplementedError

    @abstractmethod
    def publish(self, topic: str, message: Any) -> bool:
        """
        Publish a message to a specific topic.

        Args:
            topic: The topic to publish the message to
            message: The message content to be published

        Returns:
            bool: True if message was published successfully, False otherwise
        """
        raise NotImplementedError

    @abstractmethod
    def subscribe(self, topic: str) -> bool:
        """
        Subscribe to a specific topic.

        Args:
            topic: The topic to subscribe to

        Returns:
            bool: True if subscription is successful, False otherwise
        """
        raise NotImplementedError

