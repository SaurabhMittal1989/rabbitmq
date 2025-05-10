from abc import abstractmethod, ABC

from apps.client_side_consumer_balancer.ConfigurationManagerClient import IConfigurationManagerClient
from apps.client_side_consumer_balancer.MessageQueueClient import IMessageQueueClient


class IFollower(ABC):
    def __init__(self, configuration_manager_client: IConfigurationManagerClient, message_queue_client:IMessageQueueClient):
        self.configuration_manager_client = configuration_manager_client
        self.message_queue_client = message_queue_client

    @abstractmethod
    def follower_callback(self):
        pass


