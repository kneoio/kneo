import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('CLIENT_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
GITEA_USER = os.getenv('GITEA_USER')
GITEA_TOKEN = os.getenv('GITEA_TOKEN')

# Ensure all required environment variables are set
required_env_vars = [
    'CLIENT_API_KEY', 'ANTHROPIC_API_KEY', 'DB_NAME', 'DB_USER',
    'DB_PASSWORD', 'DB_HOST', 'DB_PORT', 'GITEA_USER', 'GITEA_TOKEN'
]

for var in required_env_vars:
    if os.getenv(var) is None:
        raise ValueError(f"Environment variable {var} is not set")