import grpc
import project_pb2
import project_pb2_grpc


def run():
    # NOTE: Do not use secure channel credentials for production
    with grpc.insecure_channel('localhost:9000') as channel:
        stub = project_pb2_grpc.ProjectGrpcServiceStub(channel)

        # Create a project request
        request = project_pb2.ProjectRequest(name="Test Project", description="This is a test project")

        try:
            # Call the AddProject method
            response = stub.AddProject(request)
            print(f"Project added successfully. ID: {response.id}")
        except grpc.RpcError as e:
            print(f"An error occurred: {e.details()}")


if __name__ == '__main__':
    run()
