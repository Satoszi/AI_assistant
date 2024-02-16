from common import ClientType
import configs.log_config as log_config

class Controller:
    def __init__(self, model):
        self.model = model
        self.logger = log_config.setup_logging()

    def normalize_raw_request(self, request):
        return {
            "method": request.method,
            "url": request.url,
            "headers": dict(request.headers),
            "args": request.args.to_dict(),
            "data": request.get_json(silent=True) or {}
        }

    def recognize_client(self, request_data):
        user_agent = request_data['headers'].get('User-Agent', '').lower()
        if 'chatfuel' in user_agent:
            return ClientType.CHATFUEL
        if 'manychat' in user_agent:
            return ClientType.MANYCHAT
        return ClientType.UNKNOWN

    def validate_request(self, request_data):
        # required_fields = ['user_name', 'user_id', 'message']
        # return all(field in request_data['data'] for field in required_fields)
        return True

    def normalize_data(self, request_data, client_type):
        # id, message, name, last name, gender, language, locale, timezone , profile_pic
        if client_type == ClientType.CHATFUEL:
            return {
                "user_name": request_data['data'].get('first name'),
                "user_id": request_data['data'].get('messenger user id'),
                "message": request_data['data'].get('last user freeform input'),
                "client_type": client_type
            }
        if client_type == ClientType.MANYCHAT:
            return {
                "user_name": request_data['data'].get('first_name'),
                "user_id": request_data['data'].get('id'),
                "message": request_data['data'].get('last_input_text'),
                "client_type": client_type
            }
        return {}

    def process(self, request):
        request_data = self.normalize_raw_request(request)
        client_type = self.recognize_client(request_data)

        if not self.validate_request(request_data):
            return {"error": "Invalid request"}, 400

        normalized_request = self.normalize_data(request_data, client_type)
        
        # Call the model for processing and generating a response
        status = self.model.handle_message(normalized_request)
        return status