import numpy as np
import faiss
import pickle
import os
from utils.logging import logger

class FaissVectorStore:
    def __init__(self, dimension=384, index_file='faiss_index.pkl'):
        self.dimension = dimension
        self.index_file = index_file
        self.index = None
        self.texts = []
        self.load_or_create_index()

    def load_or_create_index(self):
        if os.path.exists(self.index_file):
            logger.info(f"Loading existing index from {self.index_file}")
            with open(self.index_file, 'rb') as f:
                saved_data = pickle.load(f)
                self.index = saved_data['index']
                self.texts = saved_data['texts']
            logger.info(f"Loaded index with {self.index.ntotal} items and {len(self.texts)} texts")
        else:
            logger.info("Creating new FAISS index")
            self.index = faiss.IndexFlatL2(self.dimension)
            logger.info("New FAISS index created")

    def add(self, embedding, text):
        if self.index is None:
            logger.warning("Index not initialized. Creating new index.")
            self.index = faiss.IndexFlatL2(self.dimension)
        self.index.add(np.array([embedding], dtype=np.float32))
        self.texts.append(text)
        logger.info(f"Added new item. Current index size: {self.index.ntotal}")
        self.save_index()

    def save_index(self):
        logger.info(f"Saving index to {self.index_file}")
        with open(self.index_file, 'wb') as f:
            pickle.dump({'index': self.index, 'texts': self.texts}, f)
        logger.info("Index saved successfully")

    def search(self, query_embedding, top_k=3):
        if self.index is None or self.index.ntotal == 0:
            logger.warning("Search attempted on empty index")
            return []
        distances, indices = self.index.search(np.array([query_embedding], dtype=np.float32), top_k)
        return [(self.texts[i], 1 - distances[0][j] / 2) for j, i in enumerate(indices[0])]

    def get_sample(self, n=5):
        sample_size = min(n, len(self.texts))
        return self.texts[:sample_size]

vector_store = FaissVectorStore()