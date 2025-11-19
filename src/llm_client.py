"""
LLM Client for HuggingFace Integration
Uses Llama 3.2-3B-Instruct for text generation
"""

import os
from typing import Optional
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEndpoint
from langchain_core.language_models.llms import LLM

# Load environment variables
load_dotenv(".env.local")
load_dotenv()


class LLMClient:
    """Client for interacting with HuggingFace LLM"""
    
    MODEL_NAME = "meta-llama/Llama-3.2-3B-Instruct"
    
    def __init__(self, api_token: Optional[str] = None):
        """Initialize the LLM client
        
        Args:
            api_token: HuggingFace API token (if not provided, reads from env)
        """
        self.api_token = api_token or os.getenv("HUGGINGFACE_API_TOKEN")
        
        if not self.api_token:
            raise ValueError(
                "HuggingFace API token not found. "
                "Set HUGGINGFACE_API_TOKEN in .env.local file"
            )
        
        self.llm = self._initialize_llm()
    
    def _initialize_llm(self) -> LLM:
        """Initialize the HuggingFace LLM"""
        llm = HuggingFaceEndpoint(
            repo_id=self.MODEL_NAME,
            huggingfacehub_api_token=self.api_token,
            temperature=0.3,  # Lower temperature for more deterministic outputs
            max_new_tokens=512,
            top_p=0.95,
            repetition_penalty=1.1,
        )
        
        print(f"✅ Initialized LLM: {self.MODEL_NAME}")
        return llm
    
    def get_llm(self) -> LLM:
        """Get the initialized LLM instance"""
        return self.llm
    
    def invoke(self, prompt: str) -> str:
        """Invoke the LLM with a prompt
        
        Args:
            prompt: The input prompt
            
        Returns:
            The LLM's response
        """
        try:
            response = self.llm.invoke(prompt)
            return response.strip()
        except Exception as e:
            return f"Error invoking LLM: {str(e)}"


def create_prompt(
    system_message: str,
    user_message: str,
    examples: Optional[list] = None
) -> str:
    """Create a formatted prompt for Llama 3
    
    Args:
        system_message: System instructions
        user_message: User's input
        examples: Optional list of example interactions
        
    Returns:
        Formatted prompt string
    """
    prompt = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{system_message}<|eot_id|>"
    
    if examples:
        for example in examples:
            prompt += f"<|start_header_id|>user<|end_header_id|>\n\n{example['user']}<|eot_id|>"
            prompt += f"<|start_header_id|>assistant<|end_header_id|>\n\n{example['assistant']}<|eot_id|>"
    
    prompt += f"<|start_header_id|>user<|end_header_id|>\n\n{user_message}<|eot_id|>"
    prompt += "<|start_header_id|>assistant<|end_header_id|>\n\n"
    
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

