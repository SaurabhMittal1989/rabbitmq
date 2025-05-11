from abc import ABC, abstractmethod
from typing import Any, Callable


class IConfigurationManagerClient(ABC):
    """
    Abstract base class defining the interface for a configuration manager client.
    This interface provides methods for reading, writing, and managing configuration settings.
    """

    @abstractmethod
    def register(self) -> bool:
        """
        Load configuration from a specified path.


        Returns:
            bool: True if the configuration was loaded successfully, False otherwise
        """
        pass

    @abstractmethod
    def get_value(self, key: str, default_value: Any = None) -> Any:
        """
        Retrieve a configuration value by its key.

        Args:
            key: The configuration key to lookup
            default_value: Value to return if key is not found

        Returns:
            Any: The configuration value associated with the key,
                 or default_value if key doesn't exist
        """
        pass

    @abstractmethod
    def set_value(self, key: str, value: Any) -> bool:
        """
        Set a configuration value for a given key.

        Args:
            key: The configuration key to set
            value: The value to associate with the key

        Returns:
            bool: True if value was set successfully, False otherwise
        """
        pass

    @abstractmethod
    def delete_value(self, key: str) -> bool:
        """
        Delete a configuration key and its associated value.

        Args:
            key: The configuration key to delete

        Returns:
            bool: True if key was deleted successfully, False otherwise
        """
        pass

    @abstractmethod
    def has_value(self, key: str) -> bool:
        """
        Check if a configuration key exists.

        Args:
            key: The configuration key to check

        Returns:
            bool: True if key exists, False otherwise
        """
        pass
    #
    # @abstractmethod
    # def listen_for_config_changes(self, apply_config: Callable):
    #     pass

    @abstractmethod
    def stop(self):
        pass
