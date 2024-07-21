import traceback
import uuid
from collections import deque
import grpc
from concurrent import futures
from anthropic import Anthropic
from config import API_KEY, ANTHROPIC_API_KEY
from data_store.vector_store import vector_store
from utils.loggr import logg, log_user_prompt, log_context, log_server_response
import ai_service_pb2
import ai_service_pb2_grpc

anthropic = Anthropic(api_key=ANTHROPIC_API_KEY)
session_store = {}


def get_claude_response(context: str, prompt: str) -> str:
    message = anthropic.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=1000,
        messages=[
            {"role": "user",
             "content": f"Here is some relevant context based on the user's query, including full file contents:\n\n{context}\n\nPlease answer the following question or respond to the following prompt. Use the provided full file contents when answering. If you need to suggest code modifications, use the actual file content provided. If the relevant file content is not available, clearly state that.\n\nQuestion/Prompt: {prompt}"}
        ]
    )
    return message.content[0].text


def get_relevant_context(query, top_k=3):
    try:
        results = vector_store.search(query, top_k)

        context = "Relevant information:\n"
        for metadata, similarity in results:
            context += f"File: {metadata['file_name']}\n"
            context += f"Path: {metadata['file_path']}\n"
            context += f"Purpose: {metadata['file_purpose']}\n"

            if metadata['file_name'].lower() == 'pom.xml':
                context += f"Full pom.xml content:\n{metadata['content']}\n"
            else:
                content_preview = metadata['content'][:1000] + "..." if len(metadata['content']) > 1000 else metadata[
                    'content']
                context += f"Content Preview: {content_preview}\n"

            context += f"(Similarity: {similarity:.2f})\n\n"

        return context
    except Exception as e:
        logg.error(f"Error in get_relevant_context: {str(e)}")
        logg.error(traceback.format_exc())
        raise


def generate_context(session_id: str, query: str, session_store: dict) -> str:
    try:
        context = get_relevant_context(query)

        context += "\nInstructions for AI:\n"
        context += "1. Use the full content of the files provided above to answer the user's question.\n"
        context += "2. If asked about modifying a file, refer to the actual content and suggest specific changes.\n"
        context += ("3. If the relevant file content is not provided, clearly state that you don't have access to the "
                    "file content.\n")

        if session_id in session_store:
            context += "\nPrevious conversation:\n"
            context += "\n".join(session_store[session_id])

        return context
    except Exception as e:
        logg.error(f"Error in generate_context: {str(e)}")
        logg.error(traceback.format_exc())
        raise


class AIService(ai_service_pb2_grpc.AiServiceServicer):
    def GenerateAiResponse(self, request, context):
        session_id = request.session_id or str(uuid.uuid4())
        try:
            if request.api_key != API_KEY:
                context.abort(grpc.StatusCode.PERMISSION_DENIED, "Invalid API key")

            logg.info(f"{'New' if not request.session_id else 'Existing'} session: {session_id}")

            if session_id not in session_store:
                session_store[session_id] = deque(maxlen=5)  # Store last 5 interactions

            context_str = generate_context(session_id, request.prompt, session_store)

            log_user_prompt(request.prompt)
            log_context(context_str)

            ai_response = get_claude_response(context_str, request.prompt)

            # Update conversation history
            session_store[session_id].append(f"Human: {request.prompt}\nAI: {ai_response}")

            log_server_response(ai_response)

            return ai_service_pb2.AiResponse(response=ai_response, session_id=session_id)
        except Exception as e:
            error_msg = f"Error in GenerateAiResponse for session {session_id}: {str(e)}\n{traceback.format_exc()}"
            logg.error(error_msg)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(error_msg)
            return ai_service_pb2.AiResponse(response=f"An error occurred: {str(e)}", session_id=session_id)

    def GetProjectStructure(self, request, context):
        try:
            if request.api_key != API_KEY:
                context.abort(grpc.StatusCode.PERMISSION_DENIED, "Invalid API key")

            sample_files = vector_store.get_sample(10)  # Get 10 sample files
            structure_info = "Project Structure:\n"
            for metadata in sample_files:
                structure_info += f"- {metadata['file_name']} ({metadata['file_purpose']})\n"

            return ai_service_pb2.ProjectStructureResponse(structure=structure_info)
        except Exception as e:
            error_msg = f"Error in GetProjectStructure: {str(e)}\n{traceback.format_exc()}"
            logg.error(error_msg)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(error_msg)
            return ai_service_pb2.ProjectStructureResponse(structure=f"An error occurred: {str(e)}")


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10),
                         options=[
                             ('grpc.max_send_message_length', 50 * 1024 * 1024),
                             ('grpc.max_receive_message_length', 50 * 1024 * 1024)
                         ])
    ai_service_pb2_grpc.add_AiServiceServicer_to_server(AIService(), server)
    server.add_insecure_port('[::]:50052')
    server.start()
    logg.info("Server started on port 50052")
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
