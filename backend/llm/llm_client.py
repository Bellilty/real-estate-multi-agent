"""
LLM Client - Now using OpenAI GPT-4o-mini
Switched from Llama 3.2-3B for better performance and reliability
"""

import os
from typing import Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.language_models.llms import BaseLLM

# Load environment variables
load_dotenv(".env.local")
load_dotenv()


class LLMClient:
    """Client for interacting with OpenAI GPT-4o-mini"""
    
    MODEL_NAME = "gpt-4o-mini"
    
    def __init__(self, api_token: Optional[str] = None):
        """Initialize the LLM client
        
        Args:
            api_token: OpenAI API token (if not provided, reads from env)
        """
        # Support both OPENAI_API_KEY and HUGGINGFACE_API_TOKEN for backward compatibility
        self.api_token = (
            api_token or 
            os.getenv("OPENAI_API_KEY") or 
            os.getenv("HUGGINGFACE_API_TOKEN")
        )
        
        if not self.api_token:
            raise ValueError(
                "OpenAI API token not found. "
                "Set OPENAI_API_KEY in .env.local file\n"
                "Or rename your existing HuggingFace token to OPENAI_API_KEY"
            )
        
        self.llm = self._initialize_llm()
    
    def _initialize_llm(self) -> BaseLLM:
        """Initialize the OpenAI LLM"""
        llm = ChatOpenAI(
            model=self.MODEL_NAME,
            temperature=0,  # Deterministic for consistent entity extraction
            api_key=self.api_token,
            max_tokens=1024  # Increased for complex responses
        )
        
        print(f"✅ Initialized LLM: {self.MODEL_NAME}")
        return llm
    
    def get_llm(self) -> BaseLLM:
        """Get the initialized LLM instance"""
        return self.llm
    
    def invoke(self, prompt: str) -> str:
        """Invoke the LLM with a prompt
        
        Args:
            prompt: The input prompt
            
        Returns:
            The LLM's response as a string
        """
        try:
            # ChatOpenAI returns AIMessage, we need the content
            response = self.llm.invoke(prompt)
            return self._extract_content(response)
        except Exception as e:
            return f"Error invoking LLM: {str(e)}"
    
    def _extract_content(self, response) -> str:
        """Extract text content from LLM response
        
        Handles both AIMessage objects and plain strings
        
        Args:
            response: LLM response (AIMessage or str)
            
        Returns:
            Cleaned string content
        """
        if hasattr(response, 'content'):
            # AIMessage from ChatOpenAI
            return response.content.strip()
        return str(response).strip()


def create_prompt(
    system_message: str,
    user_message: str,
    examples: Optional[list] = None
) -> str:
    """Create a formatted prompt for GPT-4o-mini
    
    Args:
        system_message: System instructions
        user_message: User's input
        examples: Optional list of example interactions
        
    Returns:
        Formatted prompt string
    """
    # For GPT-4o-mini, we can use a simpler format
    prompt = f"{system_message}\n\n"
    
    if examples:
        prompt += "Examples:\n"
        for example in examples:
            prompt += f"User: {example['user']}\n"
            prompt += f"Assistant: {example['assistant']}\n\n"
    
    prompt += f"User: {user_message}\n"
    prompt += "Assistant:"
    
    return prompt


if __name__ == "__main__":
    # Test the LLM client
    try:
        client = LLMClient()
        
        test_prompt = create_prompt(
            system_message="You are a helpful real estate assistant.",
            user_message="What is a P&L statement?"
        )
        
        print("\n🤖 Testing LLM...")
        response = client.invoke(test_prompt)
        print(f"Response: {response}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
