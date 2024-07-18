import os
import re
from git import Repo
import tempfile
from urllib.parse import urlparse
from sentence_transformers import SentenceTransformer
from .base_processor import BaseRepoProcessor
from config import GITEA_USER, GITEA_TOKEN
import javalang

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
                                        f"Imports: {', '.join(file_info['imports'])}\n"
                                        f"Classes: {', '.join(file_info['classes'])}\n"
                                        f"Methods: {', '.join(file_info['methods'])}\n"
                                        f"Fields: {', '.join(file_info['fields'])}\n"
                                        f"Content Summary:\n{file_info['content_summary']}")

                                embedding = embedding_model.encode(text)
                                self.vector_store.add(embedding, text)

                self.logger.info(f"Processed Java Git repository: {repo_url}")
            except Exception as e:
                self.logger.error(f"Error processing Git repository {repo_url}: {str(e)}")

    def is_relevant_file(self, file_path: str) -> bool:
        return file_path.endswith('.java')

    def extract_file_info(self, file_path: str, content: str) -> dict:
        try:
            tree = javalang.parse.parse(content)

            package = ""
            if tree.package:
                package = tree.package.name if hasattr(tree.package, 'name') else '.'.join(tree.package.packages)

            imports = [imp.path for imp in tree.imports]
            classes = [t.name for t in tree.types if isinstance(t, javalang.tree.ClassDeclaration)]
            methods = [m.name for c in tree.types for m in c.methods if hasattr(c, 'methods')]
            fields = [f.declarators[0].name for c in tree.types for f in c.fields if hasattr(c, 'fields')]

            # Generate a content summary
            content_summary = self.generate_content_summary(tree)

            return {
                "type": f"Java Package: {package}" if package else "Java File",
                "main_element": classes[0] if classes else "No main class found",
                "imports": imports,
                "classes": classes,
                "methods": methods,
                "fields": fields,
                "content_summary": content_summary
            }
        except Exception as e:
            self.logger.error(f"Error extracting file info for {file_path}: {str(e)}")
            return {
                "type": "Java File",
                "main_element": "Error in parsing",
                "imports": [],
                "classes": [],
                "methods": [],
                "fields": [],
                "content_summary": f"Error in parsing file content: {str(e)}"
            }

    def generate_content_summary(self, tree):
        summary = []

        try:
            # Summarize package and imports
            if tree.package:
                package_name = tree.package.name if hasattr(tree.package, 'name') else '.'.join(tree.package.packages)
                summary.append(f"Package: {package_name}")
            summary.append(f"Number of imports: {len(tree.imports)}")

            # Summarize classes
            for class_decl in tree.types:
                if isinstance(class_decl, javalang.tree.ClassDeclaration):
                    class_summary = f"Class: {class_decl.name}"
                    if class_decl.extends:
                        class_summary += f" (extends {class_decl.extends.name})"
                    if class_decl.implements:
                        implements = [i.name for i in class_decl.implements]
                        class_summary += f" (implements {', '.join(implements)})"
                    summary.append(class_summary)

                    # Summarize methods
                    methods = [m for m in class_decl.methods] if hasattr(class_decl, 'methods') else []
                    summary.append(f"  Number of methods: {len(methods)}")
                    for method in methods[:3]:  # Limit to first 3 methods for brevity
                        params = ', '.join([f"{p.type.name} {p.name}" for p in method.parameters])
                        summary.append(f"  - {method.name}({params})")

                    # Summarize fields
                    fields = [f for f in class_decl.fields] if hasattr(class_decl, 'fields') else []
                    summary.append(f"  Number of fields: {len(fields)}")
                    for field in fields[:3]:  # Limit to first 3 fields for brevity
                        summary.append(f"  - {field.type.name} {field.declarators[0].name}")

            return "\n".join(summary)
        except Exception as e:
            return f"Error generating content summary: {str(e)}"
