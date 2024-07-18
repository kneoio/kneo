import uuid
from collections import deque
import grpc
from concurrent import futures
from config import API_KEY
from data_store.vector_store import vector_store
from data_store.database import embedding_model
from server import get_claude_response
from services.chatgpt_service import get_chatgpt_response
from utils.logging import logger
import claude_service_pb2
import claude_service_pb2_grpc


session_store = {}


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


class AIService(claude_service_pb2_grpc.AiServiceServicer):
    def GenerateAiResponse(self, request, context):
        if request.api_key != API_KEY:
            context.abort(grpc.StatusCode.PERMISSION_DENIED, "Invalid API key")

        session_id = request.session_id or str(uuid.uuid4())
        logger.info(f"{'New' if not request.session_id else 'Existing'} session: {session_id}")

        if session_id not in session_store:
            session_store[session_id] = deque(maxlen=5)  # Store last 5 interactions

        context_str = generate_context(session_id, request.prompt)

        logger.info(f"Session {session_id} - User prompt: {request.prompt}")
        logger.info(f"Full context string: {context_str}")

        # Choose AI model based on request
        if request.ai_model == "claude":
            ai_response = get_claude_response(context_str, request.prompt)
        elif request.ai_model == "chatgpt":
            ai_response = get_chatgpt_response(context_str, request.prompt)
        else:
            ai_response = "Invalid AI model specified. Please choose 'claude' or 'chatgpt'."

        # Update conversation history
        session_store[session_id].append(f"Human: {request.prompt}\nAI: {ai_response}")

        logger.info(f"Session {session_id} - AI response: {ai_response}")

        return claude_service_pb2.AiResponse(response=ai_response, session_id=session_id)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10),
                         options=[
                             ('grpc.max_send_message_length', 50 * 1024 * 1024),
                             ('grpc.max_receive_message_length', 50 * 1024 * 1024)
                         ])
    claude_service_pb2_grpc.add_AiServiceServicer_to_server(AIService(), server)
    server.add_insecure_port('[::]:50052')
    server.start()
    logger.info("Server started on port 50052")
    server.wait_for_termination()
