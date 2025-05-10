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
    def get_value(self, key: str, value) -> Any:
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

    @abstractmethod
    def register_watch(self, key: str, callback: Callable[[str, Any, Any], None]) -> str:
        """
        Register a callback function to watch for changes in a configuration value.

        Args:
            key: The configuration key to watch
            callback: A callback function that will be called when the value changes.
                     The callback should accept three parameters:
                     - key (str): The configuration key that changed
                     - old_value (Any): The previous value
                     - new_value (Any): The new value

        Returns:
            str: A unique watch ID that can be used to deregister the watch later

        Example:
            def on_config_change(key, old_value, new_value):
                print(f"Config {key} changed from {old_value} to {new_value}")

            watch_id = config_client.register_watch("server.port", on_config_change)
        """
        pass

    @abstractmethod
    def deregister_watch(self, watch_id: str) -> bool:
        """
        Remove a previously registered configuration watch.

        Args:
            watch_id: The watch ID returned from register_watch

        Returns:
            bool: True if the watch was successfully removed, False if the watch_id was not found

        Example:
            if config_client.deregister_watch(watch_id):
                print("Watch successfully removed")
            else:
                print("Watch not found")
        """
        pass
