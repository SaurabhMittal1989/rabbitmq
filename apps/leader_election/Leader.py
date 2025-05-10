from abc import abstractmethod, ABC

from apps.leader_election.ConfigurationManagerClient import IConfigurationManagerClient
from apps.leader_election.MessageQueueClient import IMessageQueueClient


class ILeader(ABC):

    def __init__(self, configuration_manager_client: IConfigurationManagerClient, message_queue_client:IMessageQueueClient):
        self.configuration_manager_client = configuration_manager_client
        self.message_queue_client = message_queue_client

    @abstractmethod
    def leader_callback(self):
        pass
