import os
from langchain_google_genai import ChatGoogleGenerativeAI
from exception_handler.ai.base_llm_service import BaseLLMService

class GeminiAnalysisService(BaseLLMService):
    def _initialize_llm(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-pro-exp-0827",
            google_api_key=os.getenv('GEMINI_API_KEY'),
            temperature=0
        )

    def _generate_fix(self, prompt):
        response = self.llm.invoke(prompt.to_string())
        return self.parser.parse(response.content)