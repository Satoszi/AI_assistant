from flask import Flask, request, jsonify
from model import ChatModel, MongoDBHandler, OpenaiLlmEngine, ManyChatResponseSender
from controller import Controller 
import configs.log_config as log_config
from configs import config

logger = log_config.setup_logging()

app = Flask(__name__)


model_name = "gpt-4-1106-preview"
system_prompt = "Bądź miły nie przekraczaj max_words. Używaj emojis"
history_length = 5

mongo_db_handler = MongoDBHandler(config.MongoDBConfig.URI, config.MongoDBConfig.DB_NAME)
llm_engine = OpenaiLlmEngine(model_name, config.OpenAIConfig.API_KEY)
manychat_response_handler = ManyChatResponseSender(config.ManychatConfig.URL, config.ManychatConfig.API_KEY)

chat_model = ChatModel(mongo_db_handler,
                       llm_engine,
                       manychat_response_handler,
                       system_prompt,
                       history_length,
                       )

controller = Controller(chat_model)

@app.route('/', methods=['POST'])
def handle_request():
    response = controller.process(request)
    if isinstance(response, tuple):
        return jsonify(response[0]), response[1]
    else:
        return jsonify(response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)