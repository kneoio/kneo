import os
import pickle

import faiss
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


class FaissVectorStore:
    def __init__(self, dimension=384, index_file='faiss_index.pkl'):
        self.dimension = dimension
        self.index_file = index_file
        self.index = None
        self.texts = []
        self.load_or_create_index()

    def load_or_create_index(self):
        if os.path.exists(self.index_file):
            with open(self.index_file, 'rb') as f:
                saved_data = pickle.load(f)
                self.index = saved_data['index']
                self.texts = saved_data['texts']
        else:
            self.index = faiss.IndexFlatL2(self.dimension)

    def add(self, embedding, text):
        if self.index is None:
            self.index = faiss.IndexFlatL2(self.dimension)
        self.index.add(np.array([embedding], dtype=np.float32))
        self.texts.append(text)
        self.save_index()

    def save_index(self):
        with open(self.index_file, 'wb') as f:
            pickle.dump({'index': self.index, 'texts': self.texts}, f)

    def search(self, query_embedding, top_k=3):
        if self.index is None or self.index.ntotal == 0:
            return []
        distances, indices = self.index.search(np.array([query_embedding], dtype=np.float32), top_k)
        return [(self.texts[i], 1 - distances[0][j] / 2) for j, i in enumerate(indices[0])]

    def get_sample(self, n=5):
        sample_size = min(n, len(self.texts))
        return self.texts[:sample_size]


vector_store = FaissVectorStore()


class SimpleVectorStore:
    def __init__(self):
        self.embeddings = []
        self.texts = []

    def add(self, embedding, text):
        self.embeddings.append(embedding)
        self.texts.append(text)

    def search(self, query_embedding, top_k=3):
        if not self.embeddings:
            return []
        similarities = cosine_similarity([query_embedding], self.embeddings)[0]
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        return [(self.texts[i], similarities[i]) for i in top_indices]

    def get_sample(self, n=5):
        """
        Return a sample of n items from the vector store.
        """
        sample_size = min(n, len(self.texts))
        return self.texts[:sample_size]


vector_store = SimpleVectorStore()
