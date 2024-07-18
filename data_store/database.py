import psycopg2
from sentence_transformers import SentenceTransformer
from config import DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
from .vector_store import vector_store
from utils.logging import logger

embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

data_store = {
    "tasks": {},
    "projects": {}
}

def extract_data():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )

        cur = conn.cursor()

        cur.execute("SELECT id, title, body, status FROM prj__tasks;")
        for row in cur.fetchall():
            data_store["tasks"][row[0]] = {
                "title": row[1],
                "body": row[2],
                "status": row[3]
            }
            text = f"Task: {row[1]}\nDescription: {row[2]}\nStatus: {row[3]}"
            embedding = embedding_model.encode(text)
            vector_store.add(embedding, text)

        cur.execute("SELECT id, name, description, status FROM prj__projects;")
        for row in cur.fetchall():
            data_store["projects"][row[0]] = {
                "name": row[1],
                "description": row[2],
                "status": row[3]
            }
            text = f"Project: {row[1]}\nDescription: {row[2]}\nStatus: {row[3]}"
            embedding = embedding_model.encode(text)
            vector_store.add(embedding, text)

        cur.close()
        conn.close()
        logger.info("Data extracted and embeddings generated successfully")
    except psycopg2.Error as e:
        logger.error(f"Database error: {e}")
    except Exception as e:
        logger.error(f"Error extracting data: {e}")