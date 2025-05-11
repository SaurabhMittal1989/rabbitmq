import uuid
from abc import ABC, abstractmethod
from typing import Any, Callable
import redis
from apps.client_side_consumer_balancer.ConfigurationManagerClient import IConfigurationManagerClient



class RedisConfigurationManagerClient(IConfigurationManagerClient):
    """
    Abstract base class defining the interface for a configuration manager client.
    This interface provides methods for reading, writing, and managing configuration settings.
    """

    def __init__(self, host, port):
        self.redis_client = redis.Redis(host=host, port=port, decode_responses=True)


    def register(self) -> bool:
        """
        Load configuration from a specified path.
        #
    
        Returns:
            bool: True if the configuration was loaded successfully, False otherwise
        """
        try:
            self.redis_client.ping()
            return True
        except:
            return False

    def get_value(self, key: str, default_value: Any) -> Any:
        """
        Retrieve a configuration value by its key.
    
        Args:
            key: The configuration key to lookup
            default_value: Value to return if key is not found
    
        Returns:
            Any: The configuration value associated with the key,
                 or default_value if key doesn't exist
        """
        value = self.redis_client.get(key)
        return value if value is not None else default_value

    def set_value(self, key: str, value: Any) -> bool:
        """
        Set a configuration value for a given key.
    
        Args:
            key: The configuration key to set
            value: The value to associate with the key
    
        Returns:
            bool: True if value was set successfully, False otherwise
        """
        try:
            return self.redis_client.set(key, value)
        except:
            return False

    def delete_value(self, key: str) -> bool:
        """
        Delete a configuration key and its associated value.
    
        Args:
            key: The configuration key to delete
    
        Returns:
            bool: True if key was deleted successfully, False otherwise
        """
        try:
            return bool(self.redis_client.delete(key))
        except:
            return False

    def has_value(self, key: str) -> bool:
        """
        Check if a configuration key exists.
    
        Args:
            key: The configuration key to check
    
        Returns:
            bool: True if key exists, False otherwise
        """
        return self.redis_client.exists(key)

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
        watch_id = str(uuid.uuid4())
        old_value = self.get_value(key, None)
        self.redis_client.config_set('notify-keyspace-events', 'KEA')
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe(
            **{f'__keyspace@0__:{key}': lambda message: callback(key, old_value, self.get_value(key, None))})
        return watch_id

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
        try:
            pubsub = self.redis_client.pubsub()
            pubsub.unsubscribe()
            return True
        except:
            return False


if __name__ == '__main__':

    import time

    # Create Redis client

    # Create configuration manager
    config_manager = RedisConfigurationManagerClient(host="localhost", port=6379)

    # Test register
    print("Testing register:", config_manager.register())

    # Test set_value
    print("Testing set_value:", config_manager.set_value("test_key", "test_value"))

    # Test get_value
    print("Testing get_value:", config_manager.get_value("test_key", "default"))

    # Test has_value
    print("Testing has_value:", config_manager.has_value("test_key"))


    # Define callback for watch
    def config_change_callback(key, old_value, new_value):
        print(f"Config changed - Key: {key}, Old: {old_value}, New: {new_value}")


    # Test register_watch
    watch_id = config_manager.register_watch("test_key", config_change_callback)
    print("Watch registered with ID:", watch_id)

    # Update value to trigger watch
    config_manager.set_value("test_key", "new_value")
    time.sleep(1)  # Wait for callback

    # Test deregister_watch
    print("Testing deregister_watch:", config_manager.deregister_watch(watch_id))

    # Test delete_value
    print("Testing delete_value:", config_manager.delete_value("test_key"))
