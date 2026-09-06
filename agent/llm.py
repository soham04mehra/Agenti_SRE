import os
from langchain_openai import ChatOpenAI

# Shared LLM instance for SRE reasoning
# Uses OPENAI_API_KEY from environment / .env file
api_key = os.getenv("OPENAI_API_KEY") or "mock-key"

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.1,
    api_key=api_key
)
