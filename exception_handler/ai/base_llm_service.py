import json
from abc import abstractmethod
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field


class AnalysisResult(BaseModel):
    diff: str = Field(..., description="Git diff of the changes, starting with 'diff --git' for each file")
    analysis: str = Field(..., description="Explanation of the issue and the updated fix")

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

    def process_comment(self, comment, pr_details, file_contents, stacktraces, original_analysis):
        prompt = self._prepare_comment_prompt(comment, pr_details, file_contents, stacktraces, original_analysis)
        updated_fix = self._generate_fix(prompt)

        return {
            "analysis": updated_fix.model_dump(),
            "pr_details": pr_details
        }

    def _prepare_comment_prompt(self, comment, pr_details, file_contents, stacktraces, original_analysis):
        template = """You are an AI assistant helping to update a pull request based on a user's comment. Here's the context:

        Original PR Title: {pr_title}
        Original PR Description: {pr_description}
        Files changed: {files_changed}

        Original Analysis and Proposed Fix:
        {original_analysis}

        User's comment: {comment}

        Content of the affected files and their stacktraces:

        {file_contents_and_stacktraces}

        Based on the user's comment, the original analysis, and the provided file contents and stacktraces, suggest updates to the pull request. 
        Consider the following:
        1. The original fix might have missed some aspects or introduced new issues.
        2. The user's comment might point out problems or suggest improvements.
        3. You may need to modify multiple files to address the comment comprehensively.
        4. Use the stacktrace information to understand the flow of execution and potential problem areas.

        Provide a detailed explanation of the changes, including:
        1. Why the changes are necessary
        2. How they address the user's comment
        3. How the changes relate to the stacktrace information
        4. Any potential side effects or considerations

        Then, provide an updated diff that incorporates these changes.

        {format_instructions}
        """

        prompt = ChatPromptTemplate.from_messages([
            ("system", template),
            ("human", "{query}")
        ])

        file_contents_and_stacktraces = "\n\n".join([
            f"File: {file_path}\n"
            f"Stacktrace:\n```\n{json.dumps(stacktraces.get(file_path, {}), indent=2)}\n```\n"
            f"Content:\n```python\n{content}\n```"
            for file_path, content in file_contents.items()
        ])

        return prompt.format_prompt(
            pr_title=pr_details['title'],
            pr_description=pr_details['body'],
            files_changed=", ".join(pr_details['files_changed']),
            original_analysis=original_analysis,
            comment=comment,
            file_contents_and_stacktraces=file_contents_and_stacktraces,
            format_instructions=self.parser.get_format_instructions(),
            query="Process the comment and suggest updates to the pull request."
        )
