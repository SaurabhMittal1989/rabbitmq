from abc import abstractmethod, ABC

from apps.client_side_consumer_balancer.ConfigurationManagerClient import IConfigurationManagerClient


class IRegister(ABC):
    @abstractmethod
    def register(self):
        pass
