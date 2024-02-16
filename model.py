import openai
from pymongo import MongoClient
import requests
from common import ClientType
from abc import ABC, abstractmethod


class Model:
    def __init__(self, logger, config):
        self.logger = logger
        self.db_handler = MongoDBHandler(config.MongoDBConfig.URI, config.MongoDBConfig.DB_NAME)
        self.chatbot = ChatBot("gpt-4-1106-preview", self.db_handler, config.OpenAIConfig.API_KEY, history_length=6)
        self.response_generator = ResponseGenerator(self.chatbot, self.logger)
        self.response_handler = ResponseSender(config.ManychatConfig.URL, config.ManychatConfig.API_KEY)
        
    def handle_message(self, normalized_request):
        bot_response = self.response_generator.generate(normalized_request)
        try:
            status = self.response_handler.send_response(bot_response, normalized_request)
            self.logger.warning(status)
        except Exception as e:
            self.logger.error(str(e))
            status = {"Error": "Error in sending response"}
        return status


class ResponseSender:
    def __init__(self, manychat_url, manychat_api_key):
        self.manychat_url = manychat_url
        self.manychat_api_key = manychat_api_key

    def send_response(self, message_content, normalized_request_info):
        client_type = normalized_request_info.get("client_type")
        if client_type == ClientType.MANYCHAT:
            subscriber_id = normalized_request_info.get("user_id")
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
                print(f"ManyChat Response: {response.json()}")
                return response.json(), response.status_code
            except requests.RequestException as e:
                print(f"Error sending request to ManyChat: {e}")
                return {"error": str(e)}, 500

        elif client_type == ClientType.CHATFUEL:
            response = {"messages": [{"text": message_content}]}
            return jsonify(response), 200

        else:
            print("Unsupported client type.")
            return {"Error": "Client type not supported"}, 400


class MongoDBHandler:
    def __init__(self, uri, db_name):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self.collection = self.db.chat_histories

    def get_last_messages(self, user_id, history_length):
        query = {"user_id": user_id}
        result = list(self.collection.find(query))

        if result:  # Check if the result is not empty
            messages = result[0]['chat_history'][-history_length:]
        else:
            messages = []  # Return an empty list if no documents are found

        return messages

    def save_message(self, user_id, message):
        if self.collection.count_documents({"user_id": user_id}) == 0:
            self.collection.insert_one({"user_id": user_id, "chat_history": [message]})
        else:
            self.collection.update_one({"user_id": user_id}, {"$push": {"chat_history": message}})


class ChatBot:
    def __init__(self, model_name, db_handler, api_key, history_length=6):
        self.model_name = model_name
        self.history_length = history_length
        self.db_handler = db_handler
        self.client = openai.OpenAI(api_key=api_key)
        self.system_message = {"role": "system", "content": "Bądź miły nie przekraczaj max_words. Używaj emojis"}

    def get_message(self, question, user_id):
        chat_history_with_meta = self.db_handler.get_last_messages(user_id, self.history_length)
        if len(chat_history_with_meta) > 0:
            chat_history = chat_history_with_meta
        else:
            chat_history = []
        chat_history.insert(0, self.system_message)
        chat_history.append({"role": "user", "content": question + " <max_words=medium>"})
        
        chat_completion = self.client.chat.completions.create(
            messages=chat_history,
            model=self.model_name
        )
        assistant_response = chat_completion.choices[0].message.content

        self.db_handler.save_message(user_id, {"role": "user", "content": question})
        self.db_handler.save_message(user_id, {"role": "assistant", "content": assistant_response})

        return assistant_response

    
class ResponseGenerator:
    def __init__(self, chatbot, logger):
        self.chatbot = chatbot
        self.logger = logger

    def generate(self, normalized_request):
        message = normalized_request["message"]
        user_id = normalized_request["user_id"]
        try:
            bot_response = self.chatbot.get_message(message, user_id)
            self.logger.warning('Bot response: %s', bot_response)
        except Exception as e:
            self.logger.error(str(e))
            bot_response = "Chyba mam przegrzane styki"

        return bot_response