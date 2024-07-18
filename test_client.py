import grpc
import claude_service_pb2
import claude_service_pb2_grpc


def run():
    channel = grpc.insecure_channel('localhost:50052')
    stub = claude_service_pb2_grpc.AiServiceStub(channel)

    request = claude_service_pb2.AIRequest(
        prompt="What languages mentioned in the enum ?",
        api_key="1234567890",
        session_id="test_session"
    )

    try:
        response = stub.GenerateAiResponse(request)
        print("AI response received:")
        print(f"Response: {response.response}")
        print(f"Session ID: {response.session_id}")
    except grpc.RpcError as e:
        print(f"An error occurred: {e}")


if __name__ == '__main__':
    run()
