import os
from langchain_openai import ChatOpenAI
from exception_handler.ai.base_llm_service import BaseLLMService

class OpenAIAnalysisService(BaseLLMService):
    def _initialize_llm(self):
        self.llm = ChatOpenAI(
            model_name="gpt-4",
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            temperature=0
        )

    def _generate_fix(self, prompt):
        response = self.llm.invoke(prompt.to_string())
        return self.parser.parse(response.content)