from dotenv import load_dotenv
from services.ai_service import serve
from utils.logging import logger


def main():
    load_dotenv()
    logger.info("Starting gRPC server...")
    serve()


if __name__ == "__main__":
    main()
