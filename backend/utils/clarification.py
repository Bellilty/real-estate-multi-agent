"""
Clarification System - Makes agents smarter by asking intelligent questions
"""

from typing import Dict, Any, Optional, List


class ClarificationAgent:
    """Intelligent agent that can ask clarifying questions"""
    
    @staticmethod
    def needs_clarification(intent: str, entities: Dict[str, Any], query: str) -> Optional[str]:
        """
        Determine if the query needs clarification
        Returns clarification message if needed, None otherwise
        """
        query_lower = query.lower()
        
        # Temporal comparison without property
        if intent == "temporal_comparison":
            if not entities.get("property"):
                # Check if "all" or "properties" is mentioned
                if any(word in query_lower for word in ["all", "properties", "portfolio", "everything"]):
                    return None  # User means all properties
                
                # Ask for clarification
                return {
                    "type": "missing_property",
                    "message": "I notice you're comparing time periods. Which property would you like to compare? Or did you mean all properties?",
                    "suggestions": [
                        "Compare expenses for **all properties** between January and February 2025",
                        "Compare expenses for **Building 180** between January and February 2025"
                    ]
                }
        
        # P&L calculation with vague timeframe
        if intent == "pl_calculation":
            if not entities.get("property") and not entities.get("year"):
                # Very vague query
                return {
                    "type": "vague_query",
                    "message": "I can help with that! Could you be more specific?",
                    "suggestions": [
                        "P&L for **all properties** in 2024",
                        "P&L for **Building 180** in Q1 2025",
                        "Total P&L for **all properties**"
                    ]
                }
        
        # General query that might be a follow-up
        if intent == "general_query":
            # Check if it's a clarification from user
            clarification_words = ["all", "everything", "all properties", "for all", "total"]
            if any(word in query_lower for word in clarification_words):
                # User is clarifying - infer they want all properties
                return {
                    "type": "infer_all_properties",
                    "inferred_intent": "pl_calculation",
                    "inferred_entities": {
                        "property": None,  # None means all
                        "year": None,
                        "quarter": None,
                        "month": None
                    }
                }
        
        return None
    
    @staticmethod
    def format_clarification_response(clarification: Dict[str, Any]) -> str:
        """Format a clarification message for the user"""
        if clarification["type"] == "missing_property":
            response = f"💡 {clarification['message']}\n\n**Examples:**\n"
            for suggestion in clarification["suggestions"]:
                response += f"- {suggestion}\n"
            return response
        
        elif clarification["type"] == "vague_query":
            response = f"💡 {clarification['message']}\n\n**Try:**\n"
            for suggestion in clarification["suggestions"]:
                response += f"- {suggestion}\n"
            return response
        
        return clarification.get("message", "Could you please clarify?")
    
    @staticmethod
    def infer_from_context(
        query: str, 
        last_intent: Optional[str], 
        last_entities: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Infer user intent from context of previous query
        Example: After asking about Building 180, "for all properties" means compare all
        """
        query_lower = query.lower()
        
        # User says "for all properties" or "all properties"
        if any(phrase in query_lower for phrase in ["all propert", "for all", "everything", "total"]):
            if last_intent in ["temporal_comparison", "pl_calculation"]:
                # Infer they want the same query but for all properties
                return {
                    "inferred_intent": last_intent,
                    "inferred_entities": {
                        **last_entities,
                        "property": None  # None = all properties
                    }
                }
        
        return None


