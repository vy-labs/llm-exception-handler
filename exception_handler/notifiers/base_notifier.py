from abc import ABC, abstractmethod

class BaseNotifier(ABC):
    def __init__(self, config):
        self.config = config

    @abstractmethod
    def process_exception(self, payload):
        pass