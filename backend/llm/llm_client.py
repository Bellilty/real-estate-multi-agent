"""
LLM Client – Clean, LangChain-compatible, AIMessage-safe
Compatible with the orchestrator and all agents.
"""

import os
from typing import Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage


# Load ENV
load_dotenv(".env.local")
load_dotenv()


class LLMClient:
    """Wrapper around ChatOpenAI with correct message formatting."""

    MODEL_NAME = "gpt-4o-mini"

    def __init__(self, api_token: Optional[str] = None):
        self.api_token = (
            api_token
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("HUGGINGFACE_API_TOKEN")
        )

        if not self.api_token:
            raise ValueError(
                "❌ Missing API key.\n"
                "Please set OPENAI_API_KEY in your .env.local"
            )

        # Create LLM instance
        self.llm = ChatOpenAI(
            model=self.MODEL_NAME,
            api_key=self.api_token,
            temperature=0,
            max_tokens=1500,
        )

        print(f"✅ Initialized OpenAI model: {self.MODEL_NAME}")

    # ------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------

    def get_llm(self) -> ChatOpenAI:
        """Return the raw ChatOpenAI instance."""
        return self.llm

    def invoke(self, prompt: str):
        """
        Invoke the model with a simple string prompt.

        Returns:
            AIMessage (standard LangChain object)
        """
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])

            # Safety: ensure AIMessage
            if isinstance(response, AIMessage):
                return response
            if hasattr(response, "content"):
                return AIMessage(content=response.content)

            return AIMessage(content=str(response))

        except Exception as e:
            return AIMessage(content=f"LLM invocation error: {str(e)}")


# ------------------------------------------------------------
# HELPER FOR PROMPTS
# ------------------------------------------------------------

def create_prompt(system_message: str, user_message: str, examples=None) -> str:
    """
    Create a simple prompt (string). LLMClient will wrap it as HumanMessage.
    """
    prompt = f"{system_message}\n\n"

    if examples:
        prompt += "Examples:\n"
        for ex in examples:
            prompt += f"User: {ex['user']}\nAssistant: {ex['assistant']}\n\n"

    prompt += f"User: {user_message}\nAssistant:"
    return prompt


# ------------------------------------------------------------
# MANUAL TEST
# ------------------------------------------------------------
if __name__ == "__main__":
    llm_client = LLMClient()

    prompt = create_prompt(
        "You are a helpful AI.",
        "Explain profit vs revenue."
    )

    print("\n🤖 Testing LLM...")
    res = llm_client.invoke(prompt)
    print("Response:", res.content)
