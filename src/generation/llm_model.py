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
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "temperature": float(os.getenv("OPENAI_TEMPERATURE", "0.1")),
        "streaming": True,
        "max_tokens": max_tokens,
    }
    return ChatOpenAI(**kwargs)


def get_internal_llm():
    """LLM không streaming dùng cho Query Expansion hoặc các tác vụ ngầm."""
    from langchain_openai import ChatOpenAI
    max_tokens = int(os.getenv("OPENAI_INTERNAL_MAX_TOKENS", "1024"))
    kwargs = {
        "api_key": os.getenv("myAPIKey", "placeholder"),
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "temperature": 0.0,
        "streaming": False,
        "max_tokens": max_tokens,
    }
    return ChatOpenAI(**kwargs)


def get_supervisor_llm():
    """LLM cho Supervisor routing."""
    from langchain_openai import ChatOpenAI
    max_tokens = int(os.getenv("OPENAI_SUPERVISOR_MAX_TOKENS", "1024"))
    kwargs = {
        "api_key": os.getenv("myAPIKey", "placeholder"),
        "model": os.getenv(
            "OPENAI_SUPERVISOR_MODEL",
            os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        ),
        "temperature": float(os.getenv("OPENAI_SUPERVISOR_TEMPERATURE", "0.0")),
        "streaming": False,
        "max_tokens": max_tokens,
    }
    # Bypass proxy for OpenAI
    old_http = os.environ.pop("HTTP_PROXY", None)
    old_https = os.environ.pop("HTTPS_PROXY", None)
    try:
        return ChatOpenAI(**kwargs)
    finally:
        if old_http: os.environ["HTTP_PROXY"] = old_http
        if old_https: os.environ["HTTPS_PROXY"] = old_https
