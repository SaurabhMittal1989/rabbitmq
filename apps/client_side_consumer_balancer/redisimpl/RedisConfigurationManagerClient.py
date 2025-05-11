
import json
from typing import Any, Callable

import redis


from apps.client_side_consumer_balancer.ConfigurationManagerClient import IConfigurationManagerClient
from apps.client_side_consumer_balancer.config import CONFIG_KEY,REDIS_DB_NUMBER


class RedisConfigurationManagerClient(IConfigurationManagerClient):

    def __init__(self, host, port):
        self.redis_client = redis.StrictRedis(host=host, port=port, decode_responses=True)
        self.config_key = CONFIG_KEY

        self.redis_db_num = REDIS_DB_NUMBER
        self.current_subscribed_queues ={}
        self.pubsub = self.redis_client.pubsub(ignore_subscribe_messages=True)

    def register(self) -> bool:
        try:
            self.redis_client.ping()
            return True
        except:
            return False

    def get_value(self, key: str, default_value: Any = None) -> Any:
        value = self.redis_client.get(key)

        if value is not None:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return default_value

    def set_value(self, key: str, value: Any) -> bool:
        try:
            if not isinstance(value, str):
                value = json.dumps(value)
            return self.redis_client.set(key, value)
        except:
            return False

    def delete_value(self, key: str) -> bool:
        try:
            return bool(self.redis_client.delete(key))
        except:
            return False

    def has_value(self, key: str) -> bool:
        return self.redis_client.exists(key)



    def stop(self):
        print("Stopping listening to configuration changes...")
        if self.pubsub:
            self.pubsub.unsubscribe()
            self.pubsub.close()

        print("Conf stopped.")


if __name__ == '__main__':
    import time

    # Create Redis client as configuration manager
    config_manager = RedisConfigurationManagerClient(host="localhost", port=6379)

    # Test register
    print("Testing register:", config_manager.register())

    # Test set_value
    print("Testing set_value:", config_manager.set_value("test_key", "test_value"))

    # Test set_value with JSON
    print("Testing set_value:", config_manager.set_value("test_key_json", {"foo": "bar", "count": 42}))

    # Test get_value
    print("Testing get_value:", config_manager.get_value("test_key", "default"))

    # Test get_value with JSON
    print("Testing get_value JSON:", config_manager.get_value("test_key_json", {}))

    # Test has_value
    print("Testing has_value:", config_manager.has_value("test_key"))


    # Define callback for watch
    def config_change_callback(key, old_value, new_value):
        print(f"Config changed - Key: {key}, Old: {old_value}, New: {new_value}")



    # Update value to trigger watch
    config_manager.set_value("test_key", "new_value")
    time.sleep(1)  # Wait for callback



    # Test delete_value
    print("Testing delete_value:", config_manager.delete_value("test_key"))
