from services.ai_service import serve
from utils.loggr import logg


def main():
    logg.info("Starting gRPC server...")
    serve()


if __name__ == "__main__":
    main()
