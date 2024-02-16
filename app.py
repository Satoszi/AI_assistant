from flask import Flask, request, jsonify
from model import Model
from controller import Controller 
import configs.log_config as log_config
from configs import config

logger = log_config.setup_logging()

app = Flask(__name__)

model = Model(logger, config)
controller = Controller(model)

@app.route('/', methods=['POST'])
def handle_request():
    response = controller.process(request)
    if isinstance(response, tuple):
        return jsonify(response[0]), response[1]
    else:
        return jsonify(response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)