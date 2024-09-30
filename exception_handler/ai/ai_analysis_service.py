import json
from abc import ABC, abstractmethod
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

class AIAnalysisService:
    def __init__(self, config):
        self.config = config

    @abstractmethod
    def analyze_exception(self, exception_data, trace_files):
        pass

def get_ai_service(config):
    from exception_handler.ai.gemini_analysis_service import GeminiAnalysisService
    from exception_handler.ai.openai_analysis_service import OpenAIAnalysisService

    llm_model = config.get('llm_model', 'gemini').lower()
    if llm_model == 'gemini':
        return GeminiAnalysisService(config)
    elif llm_model == 'openai':
        return OpenAIAnalysisService(config)
    else:
        raise ValueError(f"Unsupported LLM model: {llm_model}")

def analyze_exception(config, exception_data, trace_files):
    ai_service = get_ai_service(config)
    return ai_service.analyze_exception(exception_data, trace_files)
