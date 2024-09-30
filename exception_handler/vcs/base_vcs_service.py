from abc import ABC, abstractmethod

class BaseVCSService(ABC):
    def __init__(self, config):
        self.config = config

    @abstractmethod
    def get_repo(self, repo_name):
        pass

    @abstractmethod
    def get_file_content(self, repo, file_path):
        pass

    @abstractmethod
    def create_pull_request(self, data, repo_name):
        pass

    @abstractmethod
    def pull_request_exists(self, repo_name, issue_id):
        pass