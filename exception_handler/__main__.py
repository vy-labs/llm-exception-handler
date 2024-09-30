from flask import Flask, request, jsonify
from exception_handler.notifiers.notifier_factory import get_notifier
from exception_handler.handler import ExceptionHandler
import json
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

with open('config/config.json') as config_file:
    config = json.load(config_file)

exception_handler = ExceptionHandler(config)

@app.route('/', methods=['POST'])
def webhook():
    payload = request.json
    notifier_type = 'sentry'  # Use 'sentry' as the default notifier
    
    try:
        notifier = get_notifier(config, notifier_type)
        processed_data = notifier.process_exception(payload)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    
    result = exception_handler.handle_exception(processed_data)
    
    return jsonify(result), 200

def main():
    app.run(debug=True, host='0.0.0.0', port=int(os.getenv('PORT', 5001)))

if __name__ == '__main__':
    main()