import os
import time
from dotenv import load_dotenv
from data_store.vector_store import VectorStore
from services.ai_service import serve
from utils.logging import logger


def main():
    load_dotenv()

    start_time = time.time()
    logger.info("Loading FAISS index and metadata...")

    vector_store = VectorStore(
        index_file='C:\\Users\\justa\\PycharmProjects\\javaObsession\\quarkus_embeddings_with_ast_20240720_142042.index',
        metadata_file='C:\\Users\\justa\\PycharmProjects\\javaObsession\\quarkus_metadata_with_ast_20240720_142042.pkl'
    )

    index_load_end = time.time()
    logger.info(f"FAISS index and metadata loaded. Time taken: {index_load_end - start_time:.2f} seconds")
    logger.info(f"Number of items in vector store: {vector_store.index.ntotal}")

    end_time = time.time()
    logger.info(f"Total loading time: {end_time - start_time:.2f} seconds")

    # Start the gRPC server
    logger.info("Starting gRPC server...")
    serve()


if __name__ == "__main__":
    main()
