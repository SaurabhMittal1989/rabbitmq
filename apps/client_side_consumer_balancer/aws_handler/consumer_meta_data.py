import abc


class IAwsMetaDataHandler(abc.ABC):

    @abc.abstractmethod
    def get_active_consumers(self):
        pass
