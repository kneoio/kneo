import traceback
import uuid
from collections import deque
import grpc
from concurrent import futures
from anthropic import Anthropic
from config import API_KEY, ANTHROPIC_API_KEY
from data_store.vector_store import vector_store
from utils.logging import logger
import claude_service_pb2
import claude_service_pb2_grpc

anthropic = Anthropic(api_key=ANTHROPIC_API_KEY)
session_store = {}


def get_claude_response(context: str, prompt: str) -> str:
    message = anthropic.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=1000,
        messages=[
            {"role": "user",
             "content": f"Here is some relevant context based on the user's query:\n\n{context}\n\nPlease answer the following question or respond to the following prompt concisely and directly. Use the provided context and conversation history if relevant. If the information is not available or if you're unsure, please state that clearly.\n\nQuestion/Prompt: {prompt}"}
        ]
    )
    return message.content[0].text


def get_relevant_context(query, top_k=3):
    try:
        results = vector_store.search(query, top_k)

        context = "Relevant information:\n"
        for text, similarity in results:
            context += f"{text}\n(Similarity: {similarity:.2f})\n\n"

        return context
    except Exception as e:
        logger.error(f"Error in get_relevant_context: {str(e)}")
        logger.error(traceback.format_exc())
        raise


def generate_context(session_id: str, query: str) -> str:
    try:
        context = get_relevant_context(query)

        if session_id in session_store:
            context += "Previous conversation:\n"
            context += "\n".join(session_store[session_id])

        return context
    except Exception as e:
        logger.error(f"Error in generate_context: {str(e)}")
        logger.error(traceback.format_exc())
        raise


class AIService(claude_service_pb2_grpc.AiServiceServicer):
    def GenerateAiResponse(self, request, context):
        print(f"Received request: {request}")
        print(f"API Key: {request.api_key}")
        print(f"Prompt: {request.prompt}")
        print(f"Session ID: {request.session_id}")
        try:
            if request.api_key != API_KEY:
                context.abort(grpc.StatusCode.PERMISSION_DENIED, "Invalid API key")

            session_id = request.session_id or str(uuid.uuid4())
            logger.info(f"{'New' if not request.session_id else 'Existing'} session: {session_id}")

            if session_id not in session_store:
                session_store[session_id] = deque(maxlen=5)  # Store last 5 interactions

            context_str = generate_context(session_id, request.prompt)

            logger.warning(f"Session {session_id} - User prompt: {request.prompt}")
            logger.warning(f"Full context string: {context_str}")

            ai_response = get_claude_response(context_str, request.prompt)

            # Update conversation history
            session_store[session_id].append(f"Human: {request.prompt}\nAI: {ai_response}")

            logger.info(f"Session {session_id} - AI response: {ai_response}")

            return claude_service_pb2.AiResponse(response=ai_response, session_id=session_id)
        except Exception as e:
            error_msg = f"Error in GenerateAiResponse: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(error_msg)
            return claude_service_pb2.AiResponse(response=f"An error occurred: {str(e)}", session_id=session_id)


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


if __name__ == '__main__':
    serve()
