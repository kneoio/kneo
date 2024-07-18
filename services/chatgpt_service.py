import openai
from config import OPENAI_API_KEY
import logging

openai.api_key = OPENAI_API_KEY
logger = logging.getLogger(__name__)


def get_chatgpt_response(context: str, prompt: str) -> str:
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # or "gpt-4" if you have access
            messages=[
                {"role": "system",
                 "content": "You are an AI assistant with knowledge about various programming languages and software development concepts. Use the provided context to answer questions accurately."},
                {"role": "user",
                 "content": f"Context:\n{context}\n\nBased on the above context, please answer the following question:\n{prompt}"}
            ],
            max_tokens=1000
        )
        return response.choices[0].message['content'].strip()
    except Exception as e:
        logger.error(f"Error in getting ChatGPT response: {str(e)}")
        return "I apologize, but I encountered an error while processing your request."
