from abc import ABC, abstractmethod


class BaseRepoProcessor(ABC):
    @abstractmethod
    def process_repo(self, repo_url: str, branch: str = 'main') -> None:
        pass

    @abstractmethod
    def is_relevant_file(self, file_path: str) -> bool:
        pass

    @abstractmethod
    def extract_file_info(self, file_path: str, content: str) -> dict:
        pass
