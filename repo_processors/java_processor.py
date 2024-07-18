import os
import re
from git import Repo
import tempfile
from urllib.parse import urlparse
from sentence_transformers import SentenceTransformer
from .base_processor import BaseRepoProcessor
from config import GITEA_USER, GITEA_TOKEN

embedding_model = SentenceTransformer('all-MiniLM-L6-v2')


class JavaRepoProcessor(BaseRepoProcessor):
    def __init__(self, vector_store, logger):
        self.vector_store = vector_store
        self.logger = logger

    def process_repo(self, repo_url: str) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                parsed_url = urlparse(repo_url)
                if 'gitea' in parsed_url.netloc:
                    auth_url = f"{parsed_url.scheme}://{GITEA_USER}:{GITEA_TOKEN}@{parsed_url.netloc}{parsed_url.path}"
                else:
                    auth_url = repo_url

                repo = Repo.clone_from(auth_url, temp_dir, branch='master')

                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if self.is_relevant_file(file_path):
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                relative_path = os.path.relpath(file_path, temp_dir)
                                file_info = self.extract_file_info(relative_path, content)

                                text = (f"File: {relative_path}\n"
                                        f"Type: {file_info['type']}\n"
                                        f"Main Element: {file_info['main_element']}\n"
                                        f"Content:\n{content[:500]}")

                                embedding = embedding_model.encode(text)
                                self.vector_store.add(embedding, text)

                self.logger.info(f"Processed Java Git repository: {repo_url}")
            except Exception as e:
                self.logger.error(f"Error processing Git repository {repo_url}: {str(e)}")

    def is_relevant_file(self, file_path: str) -> bool:
        return file_path.endswith('.java')

    def extract_file_info(self, file_path: str, content: str) -> dict:
        package_match = re.search(r'package\s+([\w.]+)', content)
        class_match = re.search(r'(public\s+)?(class|interface|enum)\s+(\w+)', content)

        if package_match:
            file_type = f"Java Package: {package_match.group(1)}"
        else:
            file_type = "Java File"

        if class_match:
            main_element = f"{class_match.group(2).capitalize()}: {class_match.group(3)}"
        else:
            main_element = "No main class or interface found"

        return {
            "type": file_type,
            "main_element": main_element
        }
