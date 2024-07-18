import os
import re
from urllib.parse import urlparse

from git import Repo
import tempfile
from sentence_transformers import SentenceTransformer

from config import GITEA_USER, GITEA_TOKEN
from .base_processor import BaseRepoProcessor

embedding_model = SentenceTransformer('all-MiniLM-L6-v2')


class JoomlaPhpRepoProcessor(BaseRepoProcessor):
    def __init__(self, vector_store, logger):
        self.vector_store = vector_store
        self.logger = logger

    def process_repo(self, repo_url: str, branch: str = 'master') -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                parsed_url = urlparse(repo_url)
                if 'absolute' in parsed_url.netloc:
                    auth_url = f"{parsed_url.scheme}://{GITEA_USER}:{GITEA_TOKEN}@{parsed_url.netloc}{parsed_url.path}"
                else:
                    auth_url = repo_url

                repo = Repo.clone_from(auth_url, temp_dir, branch=branch)
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

                self.logger.info(f"Processed Joomla Git repository: {repo_url}")
            except Exception as e:
                self.logger.error(f"Error processing Git repository {repo_url}: {str(e)}")

    def is_relevant_file(self, file_path: str) -> bool:
        return file_path.endswith('.php')

    def extract_file_info(self, file_path: str, content: str) -> dict:
        component_match = re.search(r'components/com_(\w+)', file_path)
        module_match = re.search(r'modules/mod_(\w+)', file_path)
        plugin_match = re.search(r'plugins/(\w+)/(\w+)', file_path)

        if component_match:
            file_type = f"Joomla Component: {component_match.group(1)}"
        elif module_match:
            file_type = f"Joomla Module: {module_match.group(1)}"
        elif plugin_match:
            file_type = f"Joomla Plugin: {plugin_match.group(1)} - {plugin_match.group(2)}"
        else:
            file_type = "PHP File"

        class_match = re.search(r'class\s+(\w+)', content)
        function_match = re.search(r'function\s+(\w+)', content)

        if class_match:
            main_element = f"Class: {class_match.group(1)}"
        elif function_match:
            main_element = f"Function: {function_match.group(1)}"
        else:
            main_element = "No main class or function found"

        return {
            "type": file_type,
            "main_element": main_element
        }
