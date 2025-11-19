"""
Router Agent - Classifies user intent
Determines what type of request the user is making
"""

from typing import Dict, Any
from langchain_core.language_models.llms import BaseLLM
from src.llm_client import create_prompt


class RouterAgent:
    """Classifies user intent and routes to appropriate handler"""
    
    INTENT_TYPES = {
        "property_comparison": "Compare two or more properties",
        "pl_calculation": "Calculate profit and loss (P&L) for properties/periods",
        "property_details": "Get details about a specific property",
        "tenant_info": "Get information about tenants",
        "general_query": "General questions about real estate or the data",
        "unsupported": "Request cannot be handled"
    }
    
    def __init__(self, llm: BaseLLM):
        """Initialize the router agent
        
        Args:
            llm: Language model instance
        """
        self.llm = llm
    
    def classify_intent(self, user_query: str) -> Dict[str, Any]:
        """Classify the user's intent
        
        Args:
            user_query: The user's natural language query
            
        Returns:
            Dictionary with intent classification
        """
        system_message = """You are an intent classifier for a real estate asset management system.

Classify the user's query into ONE of these intents:
- property_comparison: User wants to compare two or more properties
- pl_calculation: User wants to calculate P&L (profit and loss) for a period or property
- property_details: User wants details about a specific property
- tenant_info: User wants information about tenants
- general_query: General questions about real estate or the dataset
- unsupported: The request cannot be handled

Respond with ONLY the intent name and a brief confidence explanation in this format:
INTENT: <intent_name>
CONFIDENCE: <high/medium/low>
REASON: <brief reason>"""

        examples = [
            {
                "user": "What is the P&L for Building 17?",
                "assistant": "INTENT: pl_calculation\nCONFIDENCE: high\nREASON: User explicitly asks for P&L calculation for a specific building"
            },
            {
                "user": "Compare Building 140 to Building 180",
                "assistant": "INTENT: property_comparison\nCONFIDENCE: high\nREASON: User wants to compare two specific buildings"
            },
            {
                "user": "Tell me about Building 17",
                "assistant": "INTENT: property_details\nCONFIDENCE: high\nREASON: User wants general details about a specific property"
            }
        ]
        
        prompt = create_prompt(system_message, user_query, examples)
        
        try:
            response = self.llm.invoke(prompt).strip()
            
            # Parse the response
            intent = "unsupported"
            confidence = "low"
            reason = ""
            
            for line in response.split("\n"):
                if line.startswith("INTENT:"):
                    intent = line.split("INTENT:")[1].strip().lower()
                elif line.startswith("CONFIDENCE:"):
                    confidence = line.split("CONFIDENCE:")[1].strip().lower()
                elif line.startswith("REASON:"):
                    reason = line.split("REASON:")[1].strip()
            
            # Validate intent
            if intent not in self.INTENT_TYPES:
                intent = "unsupported"
            
            return {
                "intent": intent,
                "confidence": confidence,
                "reason": reason,
                "raw_response": response
            }
            
        except Exception as e:
            return {
                "intent": "unsupported",
                "confidence": "low",
                "reason": f"Error during classification: {str(e)}",
                "raw_response": ""
            }
    
    def get_intent_description(self, intent: str) -> str:
        """Get description for an intent type"""
        return self.INTENT_TYPES.get(intent, "Unknown intent")

