import openai
from pymongo import MongoClient
import config_model


class MongoDBHandler:
    def __init__(self):
        self.client = MongoClient(config_model.MongoDBConfig.URI)
        self.db = self.client[config_model.MongoDBConfig.DB_NAME]
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

class Chatbot:
    def __init__(self, model_name, history_length=6,):
        self.model_name = model_name
        self.history_length = history_length
        self.db_handler = MongoDBHandler()
        api_key = config_model.OpenAIConfig.API_KEY
        self.client = openai.OpenAI(api_key=api_key)
        self.system_message = {"role": "system", "content": "Bądź miły nie przekraczaj max_words. Używaj emojis"}

    def get_message(self, question, user_id):
        # Fetch last messages from the database
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

        # Save the new user and assistant messages
        self.db_handler.save_message(user_id, {"role": "user", "content": question})
        self.db_handler.save_message(user_id, {"role": "assistant", "content": assistant_response})

        return assistant_response
    
chatbot = Chatbot("gpt-4-1106-preview", history_length=6)

def generate_response(message, user_id):
    return chatbot.get_message(message, user_id)