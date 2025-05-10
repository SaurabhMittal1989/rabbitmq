from abc import abstractmethod, ABC

from apps.client_side_consumer_balancer.ConfigurationManagerClient import IConfigurationManagerClient


class IRegister(ABC):

    def __init__(self, configuration_manager_client: IConfigurationManagerClient):
        self.configuration_manager_client = configuration_manager_client

    @abstractmethod
    def register(self):
        pass
