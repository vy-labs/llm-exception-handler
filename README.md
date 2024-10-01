# Exception Handler

This project is an automated exception handler that integrates with various exception notifiers (e.g., Sentry) and version control systems (e.g., GitHub) to analyze and propose fixes for exceptions using AI.

## Features

- Listens for exception notifications (currently supports Sentry)
- Analyzes exceptions using AI (supports Gemini and OpenAI)
- Creates pull requests with proposed fixes (currently supports GitHub)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/vy-labs/exception-handler.git
   cd exception-handler
   ```

2. Install Poetry if you haven't already:
   ```
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. Install dependencies using Poetry:
   ```
   poetry install
   ```

4. Copy `.env.example` to `.env` and fill in your API keys and configuration:
   ```
   cp .env.example .env
   ```

## Configuration

Update the `.env` file with your project settings. Here's an example:

```
{
  "projects": [
    {
      "unique_identifier": "sentry_project_id",
      "environments": ["production", "staging"],
      "repo": "your-org/your-repo",
      "local_repo_path": "/path/to/your/local/repo",
      "notifier": "sentry"
    }
  ],
  "llm_model": "gemini",
  "vcs_type": "github"
}
```
## Usage

1. Activate the Poetry virtual environment:
   ```
   poetry shell
   ```

2. Run the exception handler in one of two ways:

   a. As a Flask server (no arguments):
   ```
   python -m exception_handler
   ```

   By default, the server will start on port 5001. If you need to use a different port, you can set the `EXCEPTION_HANDLER_PORT` environment variable:

   ```
   EXCEPTION_HANDLER_PORT=5002 python -m exception_handler
   ```

   The exception handler will start a Flask server that listens for webhook notifications from your configured exception notifier.

   b. Directly from the command line with a JSON file:
   ```
   python -m exception_handler path/to/your/json_file.json
   ```

   This allows you to process a single exception by providing a JSON file containing the exception data. The result will be printed to the console.

### Changing the LLM Model

To use a different LLM model, update the `llm_model` field in `config/config.json`. Currently supported models are:

- `gemini` (default)
- `openai`

To add a new LLM model:

1. Create a new service class in `exception_handler/ai/` that inherits from `BaseLLMService`.
2. Implement the `_initialize_llm` and `_generate_fix` methods.
3. Update the `get_ai_service` function in `exception_handler/ai/ai_analysis_service.py`.

Example for a new LLM service:

```python
from exception_handler.ai.base_llm_service import BaseLLMService

class NewLLMService(BaseLLMService):
    def _initialize_llm(self):
        # Initialize your LLM here
        pass

    def _generate_fix(self, prompt):
        # Generate fix using your LLM
        pass

# Update get_ai_service in ai_analysis_service.py
def get_ai_service(config):
    # ...
    elif llm_model == 'new_llm':
        return NewLLMService(config)
    # ...
```

### Adding a New VCS

To add support for a new version control system:

1. Create a new service class in `exception_handler/vcs/` that inherits from `BaseVCSService`.
2. Implement the required methods: `get_repo`, `get_file_content`, `create_pull_request`, and `pull_request_exists`.
3. Update the `get_vcs_service` function in `exception_handler/vcs/vcs_factory.py`.

Example for a new VCS service:

```python
from exception_handler.vcs.base_vcs_service import BaseVCSService

class NewVCSService(BaseVCSService):
    def get_repo(self, repo_name):
        # Implement repo retrieval
        pass

    def get_file_content(self, repo, file_path):
        # Implement file content retrieval
        pass

    def create_pull_request(self, data, repo_name):
        # Implement pull request creation
        pass

    def pull_request_exists(self, repo_name, issue_id):
        # Implement pull request existence check
        pass

# Update get_vcs_service in vcs_factory.py
def get_vcs_service(config):
    vcs_type = config.get('vcs_type', 'github').lower()
    if vcs_type == 'new_vcs':
        return NewVCSService(config)
    # ...
```

### Adding a New Exception Notifier

To add support for a new exception notifier:

1. Create a new notifier class in `exception_handler/notifiers/` that inherits from `BaseNotifier`.
2. Implement the `process_exception` method.
3. Update the `get_notifier` function in `exception_handler/notifiers/notifier_factory.py`.

Example for a new notifier:

```python
from exception_handler.notifiers.base_notifier import BaseNotifier

class NewNotifier(BaseNotifier):
    def process_exception(self, payload):
        # Process the exception payload and return structured data
        pass

# Update get_notifier in notifier_factory.py
def get_notifier(config, notifier_type):
    if notifier_type.lower() == 'new_notifier':
        return NewNotifier(config)
    # ...
```



## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.
