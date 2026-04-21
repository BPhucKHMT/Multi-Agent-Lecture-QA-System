"""Module generation — cấu hình LLM cho generation và supervisor."""
import os
from dotenv import load_dotenv

load_dotenv()


def get_llm():
    """LLM cho generation (Tutor, Coding, Math, Quiz)."""
    from langchain_openai import ChatOpenAI
    max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "8192"))
    kwargs = {
        "api_key": os.getenv("myAPIKey", "placeholder"),
        "model": os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        "temperature": 0.1,
        "streaming": True,
        "max_tokens": max_tokens,
    }
    return ChatOpenAI(**kwargs)


def get_supervisor_llm():
    """LLM cho Supervisor routing."""
    from langchain_openai import ChatOpenAI
    max_tokens = int(os.getenv("OPENAI_SUPERVISOR_MAX_TOKENS", "256"))
    kwargs = {
        "api_key": os.getenv("myAPIKey", "placeholder"),
        "model": os.getenv(
            "OPENAI_SUPERVISOR_MODEL",
            os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        ),
        "temperature": 0.0,
        "streaming": False,
        "max_tokens": max_tokens,
    }
    return ChatOpenAI(**kwargs)
