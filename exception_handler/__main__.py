from flask import Flask, request, jsonify
from exception_handler.notifiers.notifier_factory import get_notifier
from exception_handler.handler import ExceptionHandler
import json
from dotenv import load_dotenv
import os
import sys

load_dotenv()

app = Flask(__name__)

# Remove config file loading
config = {
    "llm_model": os.getenv('LLM_MODEL', 'gemini'),
    "vcs_type": os.getenv('VCS_TYPE', 'github'),
    "repo": os.getenv('REPO_NAME'),
    "local_repo_path": os.getenv('LOCAL_REPO_PATH'),
    "notifier": os.getenv('NOTIFIER_TYPE', 'sentry')
}

exception_handler = ExceptionHandler(config)

def process_event(event):
    notifier_type = config['notifier']
    try:
        notifier = get_notifier(config, notifier_type)
        processed_data = notifier.process_exception(event)
    except ValueError as e:
        return {"error": str(e)}, 400
    except Exception as e:
        return {"error": f"An unexpected error occurred: {str(e)}"}, 500
    
    try:
        result = exception_handler.handle_exception(processed_data)
    except Exception as e:
        return {"error": f"Error handling exception: {str(e)}"}, 500
    
    return result, 200

def extract_event(payload):
    event = payload.get('data', {}).get('event', {})
    return event

@app.route('/', methods=['POST'])
def webhook():
    payload = request.json
    event = extract_event(payload)
    result, status_code = process_event(event)
    return jsonify(result), status_code

def main():
    if len(sys.argv) > 1:
        # Command-line execution
        json_file_path = sys.argv[1]
        try:
            with open(json_file_path, 'r') as json_file:
                payload = json.load(json_file)
            result, status_code = process_event(payload)
            print(json.dumps(result, indent=2))
            sys.exit(0 if status_code == 200 else 1)
        except FileNotFoundError:
            print(f"Error: File not found - {json_file_path}")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in file - {json_file_path}")
            sys.exit(1)
    else:
        # Start Flask server
        port = int(os.getenv('EXCEPTION_HANDLER_PORT', 5001))
        app.run(debug=True, host='0.0.0.0', port=port)

if __name__ == '__main__':
    main()