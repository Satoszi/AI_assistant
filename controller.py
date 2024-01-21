from flask import Flask, request, jsonify
import requests
from enum import Enum
from configs import config_controller
import model

app = Flask(__name__)

class ClientType(Enum):
    CHATFUEL = 'chatfuel'
    MANYCHAT = 'manychat'
    UNKNOWN = 'unknown'

def recognize_client(request_info):
    user_agent = request_info['headers'].get('User-Agent', '').lower()
    if 'chatfuel' in user_agent:
        return ClientType.CHATFUEL
    if 'manychat' in user_agent:
        return ClientType.MANYCHAT
    return ClientType.UNKNOWN

def validate_request(request_info):
    # required_fields = ['user_name', 'user_id', 'message']
    # return all(field in request_info['data'] for field in required_fields)
    return True

def normalize_data(request_info, client_type):
    # id, message, name, last name, gender, language, locale, timezone , profile_pic
    if client_type == ClientType.CHATFUEL:
        return {
            "user_name": request_info['data'].get('first name'),
            "user_id": request_info['data'].get('messenger user id'),
            "message": request_info['data'].get('last user freeform input'),
            "client_type": client_type
        }
    if client_type == ClientType.MANYCHAT:
        return {
            "user_name": request_info['data'].get('first_name'),
            "user_id": request_info['data'].get('id'),
            "message": request_info['data'].get('last_input_text'),
            "client_type": client_type
        }
    return {}

def delegate_to_model(normalized_data):
    bot_response = model.generate_response(normalized_data["message"], normalized_data["user_id"])
    return bot_response

def send_response_to_client(message_content, normalized_request_info):
    client_type = normalized_request_info.get("client_type")
    if client_type == ClientType.MANYCHAT:
        subscriber_id = normalized_request_info.get("user_id")
        url = config_controller.ManychatConfig.URL
        headers = {
            "Authorization": f"Bearer {config_controller.ManychatConfig.API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "subscriber_id": subscriber_id,
            "data": {
                "version": "v2",
                "content": {
                    "messages": [
                        {"type": "text", "text": message_content}
                    ]
                }
            }
        }
        response = requests.post(url, json=data, headers=headers)
        return response.json(), response.status_code
    elif client_type == ClientType.CHATFUEL:
        response = {
            "messages": [
                {"text": message_content}
            ]
        }
        return jsonify(response), 200
    else:
        return {"error": "Client type not supported"}, 400

def log_request(request_info):
    print(f"Logging request: {request_info}")

def handle_client_request(request_info):
    client_type = recognize_client(request_info)
    print(client_type)
    if not validate_request(request_info):
        return {"error": "Invalid request"}, 400
    normalized_request_info = normalize_data(request_info, client_type)
    bot_response = delegate_to_model(normalized_request_info)
    # log_request(request_info)
    print(normalized_request_info)
    return send_response_to_client(bot_response, normalized_request_info)

@app.route('/', methods=['POST'])
def handle_request():
    request_info = {
        "method": request.method,
        "url": request.url,
        "headers": dict(request.headers),
        "args": request.args,
        "data": request.get_json(silent=True)
    }
    response, status_code = handle_client_request(request_info)
    return response, status_code

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)