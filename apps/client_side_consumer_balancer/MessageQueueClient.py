from abc import ABC, abstractmethod
from typing import Any, Optional, Callable


class IMessageQueueClient(ABC):
    """
    Abstract base class defining the interface for a message queue client.
    """


    @abstractmethod
    def close(self) -> None:
        """
        Disconnect from the message queue.
        """
        raise NotImplementedError

    @abstractmethod
    def publish(self, message: Any) -> bool:
        """
        Publish a message to a specific topic.

        Args:
            message: The message content to be published

        Returns:
            bool: True if message was published successfully, False otherwise
        """
        raise NotImplementedError

    @abstractmethod
    def subscribe_to_queue(self, queue_name):
        pass


    @abstractmethod
    def unsubscribe_from_queue(self, queue_name):
        pass

