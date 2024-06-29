import logging
import os
import uuid
from typing import Dict, Optional
from collections import deque

import colorlog
import psycopg2
from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

app = FastAPI()
load_dotenv()
API_KEY = os.getenv('CLIENT_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
api_key_header = APIKeyHeader(name="X-API-key")
session_store = {}
anthropic = Anthropic(api_key=ANTHROPIC_API_KEY)

# Configure logging
logger = colorlog.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(asctime)s - %(levelname)s - %(message)s',
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    }
))
logger.addHandler(handler)


def get_api_key(api_key: str = Depends(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Could not validate credentials")
    return api_key


data_store: Dict[str, Dict] = {
    "tasks": {},
    "projects": {}
}


def get_claude_response(context: str, prompt: str) -> str:
    message = anthropic.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=300,
        messages=[
            {"role": "user",
             "content": f"Here is a summary of all available projects, along with our previous conversation:\n\n{context}\n\nPlease answer the following question or respond to the following prompt concisely and directly. Use the provided project information and our conversation history if relevant. If the information is not available or if you're unsure, please state that clearly.\n\nQuestion/Prompt: {prompt}"}
        ]
    )
    return message.content[0].text


class Prompt(BaseModel):
    text: str


def extract_data():
    db_name = os.getenv('DB_NAME')
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST')
    db_port = os.getenv('DB_PORT')

    conn = psycopg2.connect(
        dbname=db_name,
        user=db_user,
        password=db_password,
        host=db_host,
        port=db_port
    )

    cur = conn.cursor()

    cur.execute("SELECT id, title, body, status FROM prj__tasks;")
    for row in cur.fetchall():
        data_store["tasks"][row[0]] = {
            "title": row[1],
            "body": row[2],
            "status": row[3]
        }

    cur.execute("SELECT id, name, description, status FROM prj__projects;")
    for row in cur.fetchall():
        data_store["projects"][row[0]] = {
            "name": row[1],
            "description": row[2],
            "status": row[3]
        }

    cur.close()
    conn.close()
    logger.info("Data extracted successfully")


def generate_context(session_id: str) -> str:
    context = "Available Projects:\n"
    for project in data_store["projects"].values():
        context += f"Name: {project['name'] or 'N/A'}\n"
        context += f"Description: {project['description'] or 'N/A'}\n"
        context += f"Status: {project['status'] or 'N/A'}\n\n"

    context += "Available Tasks:\n"
    for task in data_store["tasks"].values():
        context += f"Title: {task['title'] or 'N/A'}\n"
        context += f"Description: {task['body'] or 'N/A'}\n"
        context += f"Status: {task['status'] or 'N/A'}\n\n"

    if session_id in session_store:
        context += "Previous conversation:\n"
        context += "\n".join(session_store[session_id])

    return context


@app.post("/generate")
async def generate_response(prompt: Prompt, api_key: str = Depends(get_api_key),
                            session_id: Optional[str] = Query(None)):
    if not session_id:
        session_id = str(uuid.uuid4())
        logger.info(f"New session created: {session_id}")
    else:
        logger.info(f"Existing session: {session_id}")

    if session_id not in session_store:
        session_store[session_id] = deque(maxlen=5)  # Store last 5 interactions

    context = generate_context(session_id)

    logger.info(f"Session {session_id} - User prompt: {prompt.text}")

    claude_response = get_claude_response(context, prompt.text)

    processed_response = claude_response.strip()
    if len(processed_response) > 150:
        processed_response = processed_response.split('.')[0] + '.'

    # Update conversation history
    session_store[session_id].append(f"Human: {prompt.text}\nAI: {processed_response}")

    logger.info(f"Session {session_id} - AI response: {processed_response}")

    return {"response": processed_response, "session_id": session_id}


if __name__ == "__main__":
    extract_data()
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
