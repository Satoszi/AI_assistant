import openai
from pymongo import MongoClient
import requests


class MongoDBHandler:
    def __init__(self, uri: str, db_name: str):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self.collection = self.db.chat_histories

    def fetch_recent_messages(self, user_id, limit):
        document = self.collection.find_one(
            {"user_id": user_id}, 
            {'chat_history': {'$slice': -limit}}
        )
        return document['chat_history'] if document else []

    def append_message(self, user_id, message):
        self.collection.update_one(
            {"user_id": user_id},
            {"$addToSet": {"chat_history": message}},
            upsert=True
        )


# Openai LLM chat model
class OpenaiLlmEngine:
    def __init__(self, model_name: str, api_key: str):
        self.model_name = model_name
        self.client = openai.OpenAI(api_key=api_key)

    def generate_response(self, system_prompt: str, messages: list):
        messages = [{'role': 'system', 'content': system_prompt}] + messages
        chat_completion = self.client.chat.completions.create(
            messages=messages,
            model=self.model_name
        )
        assistant_response = chat_completion.choices[0].message.content
        return assistant_response


# Dummy LLM chat model
class DummyLlmEngine:
    def generate_response(self, system_prompt: str, messages):
        return "Hello. I am a dummy AI"


class ManyChatResponseSender:
    def __init__(self, manychat_url: str, manychat_api_key: str):
        self.manychat_url = manychat_url
        self.manychat_api_key = manychat_api_key

    def send_response(self, message_content: str, subscriber_id: str):
        headers = {
            "Authorization": f"Bearer {self.manychat_api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "subscriber_id": subscriber_id,
            "data": {
                "version": "v2",
                "content": {
                    "messages": [{"type": "text", "text": message_content}]
                }
            }
        }
        try:
            response = requests.post(self.manychat_url, json=data, headers=headers)
            return response.json(), response.status_code
        except requests.RequestException as e:
            return {"error": str(e)}, 500


class ChatModel:
    def __init__(self, 
                 mongo_db_handler: MongoDBHandler, 
                 llm_engine: OpenaiLlmEngine | DummyLlmEngine, 
                 manychat_response_handler: ManyChatResponseSender, 
                 system_prompt: str,
                 history_length: int = 6):
        self.mongo_db_handler = mongo_db_handler
        self.llm_engine = llm_engine
        self.manychat_response_handler = manychat_response_handler
        self.system_prompt = system_prompt
        self.history_length = history_length

    def handle_message(self, normalized_request):

        user_id = normalized_request["user_id"]
        last_message = normalized_request["message"]
        last_prompt = last_message + " <max_words=medium>"

        recent_messages = self.mongo_db_handler.fetch_recent_messages(user_id, self.history_length)
        recent_messages = recent_messages + [{'role': 'user', 'content': last_prompt}]

        assistant_response = self.llm_engine.generate_response(self.system_prompt, recent_messages)
        self.mongo_db_handler.append_message(user_id, {"role": "user", "content": last_message})
        self.mongo_db_handler.append_message(user_id, {"role": "assistant", "content": assistant_response})
        status = self.manychat_response_handler.send_response(assistant_response, user_id)
        return status