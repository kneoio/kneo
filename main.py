import os
import time
from dotenv import load_dotenv
from data_store.database import extract_data
from data_store.vector_store import FaissVectorStore
from repo_processors.joomla_processor import JoomlaPhpRepoProcessor
from repo_processors.java_processor import JavaRepoProcessor
from repo_processors.vuejs_processor import VueJSRepoProcessor
from services.claude_service import serve
from utils.logging import logger

vector_store = FaissVectorStore()


def check_stored_context():
    logger.info(f"Total items in vector store: {vector_store.index.ntotal if vector_store.index else 0}")

    logger.info("Checking stored context...")
    sample = vector_store.get_sample(5)
    for i, text in enumerate(sample, 1):
        logger.info(f"Sample {i}:\n{text}\n")

    joomla_items = [text for text in vector_store.texts if "Joomla Component" in text]
    logger.info(f"Number of Joomla components: {len(joomla_items)}")

    java_items = [text for text in vector_store.texts if "Java Package" in text]
    logger.info(f"Number of Java packages: {len(java_items)}")

    vue_items = [text for text in vector_store.texts if "Vue Component" in text]
    logger.info(f"Number of Vue components: {len(vue_items)}")


def process_repositories(repo_processors, repos, max_retries=3, retry_delay=5):
    for repo_type, repo_list in repos.items():
        processor = repo_processors[repo_type]
        for repo_url in repo_list:
            for attempt in range(max_retries):
                try:
                    logger.info(f"Processing {repo_type} repository: {repo_url}")
                    start_time = time.time()
                    processor.process_repo(repo_url)
                    end_time = time.time()
                    logger.info(f"Finished processing {repo_url}. Time taken: {end_time - start_time:.2f} seconds")
                    break  # Success, break the retry loop
                except Exception as e:
                    logger.error(f"Attempt {attempt + 1} failed. Error processing {repo_url}: {str(e)}")
                    if attempt < max_retries - 1:
                        logger.info(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        logger.error(f"Max retries reached for {repo_url}. Moving to next repository.")


def main():
    load_dotenv()

    start_time = time.time()
    logger.info("Loading or creating FAISS index...")
    index_load_start = time.time()
    vector_store.load_or_create_index()
    index_load_end = time.time()
    logger.info(f"FAISS index loaded or created. Time taken: {index_load_end - index_load_start:.2f} seconds")
    logger.info(f"Initial number of items in vector store: {vector_store.index.ntotal if vector_store.index else 0}")

    logger.info("Extracting data from database...")
    db_start = time.time()
    extract_data()
    db_end = time.time()
    logger.info(f"Data extracted from database. Time taken: {db_end - db_start:.2f} seconds")

    repo_processors = {
        'joomla': JoomlaPhpRepoProcessor(vector_store, logger),
        'java': JavaRepoProcessor(vector_store, logger),
        'vuejs': VueJSRepoProcessor(vector_store, logger)
    }

    repos = {
        'joomla': [
            # "https://github.com/Semantyca/Semantyca-Joomla.git"
        ],
        'java': [
            "https://github.com/kneoio/Keypractica.git",
        ],
        'vuejs': [
            # "https://github.com/kneoio/kneox.git",
        ]
    }

    logger.info("Processing repositories...")
    repo_start = time.time()
    process_repositories(repo_processors, repos)
    repo_end = time.time()
    logger.info(f"Repository processing completed. Time taken: {repo_end - repo_start:.2f} seconds")

    # Check stored context
    check_stored_context()

    end_time = time.time()
    logger.info(f"Total processing time: {end_time - start_time:.2f} seconds")

    # Start the gRPC server
    logger.info("Starting gRPC server...")
    serve()


if __name__ == "__main__":
    main()
