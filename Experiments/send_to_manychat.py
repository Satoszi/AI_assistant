def send_message_to_subscriber(api_key, subscriber_id, message_content):
    url = "https://api.manychat.com/fb/sending/sendContent"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "subscriber_id": subscriber_id,
        "data": {
            "version": "v2",
            "content": {
                "messages": [
                    {"type": "text", "text": message_content},
                    # {"type": "image", "url": "https://cdn.pixabay.com/photo/2015/04/19/08/32/marguerite-729510_1280.jpg"}
                ]
            }
        }
    }

    response = requests.post(url, json=data, headers=headers)
    return response.json()