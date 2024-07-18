import uuid
from collections import deque
import grpc
from concurrent import futures
from anthropic import Anthropic
from config import API_KEY, ANTHROPIC_API_KEY
from data_store.vector_store import vector_store
from data_store.database import embedding_model
from utils.logging import logger
import claude_service_pb2
import claude_service_pb2_grpc

anthropic = Anthropic(api_key=ANTHROPIC_API_KEY)
session_store = {}


def get_claude_response(context: str, prompt: str) -> str:
    message = anthropic.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=1000,  # Increased from 300 to 1000 for longer responses
        messages=[
            {"role": "user",
             "content": f"Here is some relevant context based on the user's query:\n\n{context}\n\nPlease answer the following question or respond to the following prompt concisely and directly. Use the provided context and conversation history if relevant. If the information is not available or if you're unsure, please state that clearly.\n\nQuestion/Prompt: {prompt}"}
        ]
    )
    return message.content[0].text


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
        # Removed the truncation logic
        # if len(processed_response) > 150:
        #     processed_response = processed_response.split('.')[0] + '.'

        # Update conversation history
        session_store[session_id].append(f"Human: {request.prompt}\nAI: {processed_response}")

        logger.info(f"Session {session_id} - AI response: {processed_response}")

        return claude_service_pb2.AiResponse(response=processed_response, session_id=session_id)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10),
                         options=[
                             ('grpc.max_send_message_length', 50 * 1024 * 1024),
                             ('grpc.max_receive_message_length', 50 * 1024 * 1024)
                         ])
    claude_service_pb2_grpc.add_AiServiceServicer_to_server(ClaudeService(), server)
    server.add_insecure_port('[::]:50052')
    server.start()
    logger.info("Server started on port 50052")
    server.wait_for_termination()