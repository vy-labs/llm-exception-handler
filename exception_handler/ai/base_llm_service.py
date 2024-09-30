import json
from abc import abstractmethod
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field


class AnalysisResult(BaseModel):
    diff: str = Field(..., description="Git diff of the changes, starting with 'diff --git' for each file")
    analysis: str = Field(..., description="Explanation of the issue and the fix")

class BaseLLMService:
    def __init__(self, config):
        self.config = config
        self.parser = PydanticOutputParser(pydantic_object=AnalysisResult)
        self._initialize_llm()

    @abstractmethod
    def _initialize_llm(self):
        raise NotImplementedError("Subclasses must implement _initialize_llm method")

    def _generate_fix(self, prompt):
        raise NotImplementedError("Subclasses must implement _generate_fix method")

    def analyze_exception(self, exception_data, trace_files):
        prompt = self._prepare_prompt(exception_data, trace_files)
        proposed_fix = self._generate_fix(prompt)

        return {
            "analysis": proposed_fix.model_dump(),
            "original_exception": exception_data,
            "affected_files": list(trace_files.keys())
        }

    def _prepare_prompt(self, exception_data, trace_files):
        template = """You are an AI assistant which is a developer working on fixing a bug in a codebase. Analyze this exception and suggest a fix. Here's the context:

        Exception Data type: {exception_type}, value: {exception_value}, module: {exception_module}
        Request context: {request_context}
        Stacktrace:
        {stacktrace}

        Content of the files involved in the exception trace:

        {file_contents}

        Provide a detailed explanation of the issue, including how it propagates through the different files. 
        Then, suggest a comprehensive fix that addresses the root cause of the problem. 
        Make sure your fix is consistent with the existing code style and structure across all affected files. 
        If multiple files need to be modified, please provide separate code snippets for each file, code snippets should be complete, do not add incomplete code like # ... existing code ... or # ... rest of the method ...

        IMPORTANT: When providing the diff, please follow these guidelines:
        1. Start the diff with 'diff --git a/path/to/file b/path/to/file'
        2. Include the file path in the diff header
        3. Use '---' and '+++' lines to indicate the old and new versions of the file
        4. Use '-' for removed lines and '+' for added lines
        5. Provide context lines (unchanged lines) around the changes
        6. If multiple files are changed, separate each file's diff with a newline
        7. Maintain consistent indentation with the surrounding code.
        8. Do not introduce empty lines with extra whitespace.
        9. When modifying existing lines, show the entire line being removed and the entire new line being added, rather than just showing whitespace changes.

        Here's an example of a correctly formatted diff:

        diff --git a/path/to/file1.py b/path/to/file1.py
        --- a/path/to/file1.py
        +++ b/path/to/file1.py
        @@ -10,7 +10,7 @@
         def some_function():
             # This is a context line
        -    old_code = "to be removed"
        +    new_code = "added instead"
             # This is another context line

        diff --git a/path/to/file2.py b/path/to/file2.py
        --- a/path/to/file2.py
        +++ b/path/to/file2.py
        @@ -15,6 +15,8 @@
         class SomeClass:
             def __init__(self):
                 self.value = 10
        +        # New line added
        +        self.new_value = 20

        Please ensure your diff follows this format exactly.

        {format_instructions}
        """

        prompt = ChatPromptTemplate.from_messages([
            ("system", template),
            ("human", "{query}")
        ])

        file_contents = "\n\n".join([f"File: {file_path}\n```python\n{content}\n```" for file_path, content in trace_files.items()])

        return prompt.format_prompt(
            exception_type=exception_data['exception']['type'],
            exception_value=exception_data['exception']['value'],
            exception_module=exception_data['exception']['module'],
            request_context=exception_data['context']['request'],
            stacktrace=json.dumps(exception_data['stacktrace'], indent=2),
            file_contents=file_contents,
            format_instructions=self.parser.get_format_instructions(),
            query="Analyze the exception and provide a fix."
        )