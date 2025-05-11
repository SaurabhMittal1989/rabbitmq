"""
Example implementation of a consumer-side client balancer application.
This module demonstrates:
- Leader-follower pattern implementation using callback interfaces
- Configuration and message queue client implementations
- Singleton pattern usage in balancer implementation
- Basic balancing functionality
"""
from apps.client_side_consumer_balancer.ConsumerSideClientBalancer import ConsumerSideClientBalancer
import threading
import time
from typing import Callable, Any

from apps.client_side_consumer_balancer.ConfigurationManagerClient import IConfigurationManagerClient
from apps.client_side_consumer_balancer.FollowerCallback import IFollowerCallback
from apps.client_side_consumer_balancer.LeaderCallback import ILeaderCallback
from apps.client_side_consumer_balancer.MessageQueueClient import IMessageQueueClient
from apps.client_side_consumer_balancer.Register import IRegister
from apps.client_side_consumer_balancer.rabbitmq.RabbitMQMessageQueueClient import RabbitMQMessageQueueClient
from apps.client_side_consumer_balancer.redisimpl.RedisConfigurationManagerClient import RedisConfigurationManagerClient

config_client = RedisConfigurationManagerClient()
message_queue_client = RabbitMQMessageQueueClient()

leader = Leader(configuration_manager_client=config_client, message_queue_client=message_queue_client)
follower = Follower(configuration_manager_client=config_client, message_queue_client=message_queue_client)
register = Register(configuration_manager_client=config_client)

# Example 1: Demonstrating Singleton pattern
balancer1 = ConsumerSideClientBalancer(leader=leader, follower=follower, register=register)
balancer2 = ConsumerSideClientBalancer(leader=leader, follower=follower, register=register)
assert (balancer1 is balancer2)

# Example 2: Starting the balancer
balancer1.balance()