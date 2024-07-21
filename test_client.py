import grpc
import ai_service_pb2
import ai_service_pb2_grpc


def run():
    channel = grpc.insecure_channel('localhost:50052')
    stub = ai_service_pb2_grpc.AiServiceStub(channel)

    request = ai_service_pb2.AiRequest(
         prompt="Look for PolicyController ?",
        # prompt="Is it based on spring or jax-rs ?",
        #prompt="Potentially modify controller files (purpose: 'REST Controller') to add authentication checks or annotations.",
        #prompt="can you print calculate method  with the annotation that we mentioned earlier so I can past it ",
        #prompt="can you print all dependecies ",

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
