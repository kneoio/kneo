import logging
import os
import uuid
from typing import Dict
from collections import deque

import colorlog
import psycopg2
from anthropic import Anthropic
from dotenv import load_dotenv
import grpc
from concurrent import futures
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

import claude_service_pb2
import claude_service_pb2_grpc

load_dotenv()
API_KEY = os.getenv('CLIENT_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
session_store = {}
anthropic = Anthropic(api_key=ANTHROPIC_API_KEY)

# Initialize sentence transformer model for embeddings
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# Configure logging
logger = colorlog.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(asctime)s - %(levelname)s - %(message)s',
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    }
))
logger.addHandler(handler)

data_store: Dict[str, Dict] = {
    "tasks": {},
    "projects": {}
}


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


vector_store = SimpleVectorStore()


def get_claude_response(context: str, prompt: str) -> str:
    message = anthropic.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=300,
        messages=[
            {"role": "user",
             "content": f"Here is some relevant context based on the user's query:\n\n{context}\n\nPlease answer the following question or respond to the following prompt concisely and directly. Use the provided context and conversation history if relevant. If the information is not available or if you're unsure, please state that clearly.\n\nQuestion/Prompt: {prompt}"}
        ]
    )
    return message.content[0].text


def extract_data():
    db_name = os.getenv('DB_NAME')
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST')
    db_port = os.getenv('DB_PORT')

    conn = psycopg2.connect(
        dbname=db_name,
        user=db_user,
        password=db_password,
        host=db_host,
        port=db_port
    )

    cur = conn.cursor()

    cur.execute("SELECT id, title, body, status FROM prj__tasks;")
    for row in cur.fetchall():
        data_store["tasks"][row[0]] = {
            "title": row[1],
            "body": row[2],
            "status": row[3]
        }
        text = f"Task: {row[1]}\nDescription: {row[2]}\nStatus: {row[3]}"
        embedding = embedding_model.encode(text)
        vector_store.add(embedding, text)

    cur.execute("SELECT id, name, description, status FROM prj__projects;")
    for row in cur.fetchall():
        data_store["projects"][row[0]] = {
            "name": row[1],
            "description": row[2],
            "status": row[3]
        }
        text = f"Project: {row[1]}\nDescription: {row[2]}\nStatus: {row[3]}"
        embedding = embedding_model.encode(text)
        vector_store.add(embedding, text)

    cur.close()
    conn.close()
    logger.info("Data extracted and embeddings generated successfully")


def get_relevant_context(query, top_k=3):
    query_embedding = embedding_model.encode(query)
    results = vector_store.search(query_embedding, top_k)

    context = "Relevant information:\n"
    for text, similarity in results:
        context += f"{text}\n(Similarity: {similarity:.2f})\n\n"

    return context


def generate_context(session_id: str, query: str) -> str:
    context = get_relevant_context(query)

    if session_id in session_store:
        context += "Previous conversation:\n"
        context += "\n".join(session_store[session_id])

    return context


class ClaudeService(claude_service_pb2_grpc.AiServiceServicer):
    def GenerateAiResponse(self, request, context):
        if request.api_key != API_KEY:
            context.abort(grpc.StatusCode.PERMISSION_DENIED, "Invalid API key")

        session_id = request.session_id or str(uuid.uuid4())
        logger.info(f"{'New' if not request.session_id else 'Existing'} session: {session_id}")

        if session_id not in session_store:
            session_store[session_id] = deque(maxlen=5)  # Store last 5 interactions

        context_str = generate_context(session_id, request.prompt)

        logger.info(f"Session {session_id} - User prompt: {request.prompt}")

        claude_response = get_claude_response(context_str, request.prompt)

        processed_response = claude_response.strip()
        if len(processed_response) > 150:
            processed_response = processed_response.split('.')[0] + '.'

        # Update conversation history
        session_store[session_id].append(f"Human: {request.prompt}\nAI: {processed_response}")

        logger.info(f"Session {session_id} - AI response: {processed_response}")

        return claude_service_pb2.AiResponse(response=processed_response, session_id=session_id)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    claude_service_pb2_grpc.add_AiServiceServicer_to_server(ClaudeService(), server)
    server.add_insecure_port('[::]:50052')
    server.start()
    logger.info("Server started on port 50052")
    server.wait_for_termination()


if __name__ == "__main__":
    extract_data()
    serve()