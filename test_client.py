import grpc
import claude_service_pb2
import claude_service_pb2_grpc


def run():
    channel = grpc.insecure_channel('localhost:50052')
    stub = claude_service_pb2_grpc.AiServiceStub(channel)

    request = claude_service_pb2.AIRequest(
        prompt="what is TaskController ?",
        api_key="1234567890",
        session_id="test_session"
        # Remove the ai_model field
    )

    try:
        response = stub.GenerateAiResponse(request)
        print("AI response received:")
        print(f"Response: {response.response}")
        print(f"Session ID: {response.session_id}")
    except grpc.RpcError as e:
        print(f"An error occurred: {e}")
        print(f"Details: {e.details()}")  # This will print more details about the error


if __name__ == '__main__':
    run()
