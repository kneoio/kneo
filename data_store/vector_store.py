import numpy as np
import faiss
import pickle
import os
from utils.loggr import logg
from sentence_transformers import SentenceTransformer


class VectorStore:
    def __init__(self):
        self.index_file = os.getenv('INDEX_FILE')
        self.metadata_file = os.getenv('METADATA_FILE')
        self.index = None
        self.texts = []
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.load_index_and_metadata()

    def load_index_and_metadata(self):
        if os.path.exists(self.index_file) and os.path.exists(self.metadata_file):
            logg.info(f"Loading existing index from {self.index_file}")
            self.index = faiss.read_index(self.index_file)

            logg.info(f"Loading metadata from {self.metadata_file}")
            with open(self.metadata_file, 'rb') as f:
                self.texts = pickle.load(f)

            logg.info(f"Loaded index with {self.index.ntotal} items and {len(self.texts)} texts")
            logg.info(f"Index dimension: {self.index.d}")
        else:
            logg.error("Index or metadata file not found. Please ensure both files exist.")
            raise FileNotFoundError("Index or metadata file not found")

    def search(self, query, top_k=3):
        if self.index is None or self.index.ntotal == 0:
            logg.warning("Search attempted on empty index")
            return []
        query_embedding = self.embedding_model.encode([query])[0]

        # Check if dimensions match
        if query_embedding.shape[0] != self.index.d:
            logg.warning(f"Dimension mismatch. Query: {query_embedding.shape[0]}, Index: {self.index.d}")
            # Adjust the embedding dimension
            if query_embedding.shape[0] > self.index.d:
                query_embedding = query_embedding[:self.index.d]
            else:
                query_embedding = np.pad(query_embedding, (0, self.index.d - query_embedding.shape[0]))

        distances, indices = self.index.search(np.array([query_embedding], dtype=np.float32), top_k)
        return [(self.texts[i], 1 - distances[0][j] / 2) for j, i in enumerate(indices[0])]

    def get_sample(self, n=5):
        sample_size = min(n, len(self.texts))
        return self.texts[:sample_size]


vector_store = VectorStore()