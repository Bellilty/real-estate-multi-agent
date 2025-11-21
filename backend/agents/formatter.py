"""
Formatter Agent v3 - Simplified
Uses LLM to format responses in natural language
"""

import time
import re
from typing import Dict, Any
from backend.utils.prompts import PromptTemplates


class ResponseFormatter:
    """Formats query results into natural language responses"""
    
    def __init__(self, llm):
        self.llm = llm
        self.prompt_templates = PromptTemplates()
    
    def format_response(
        self,
        user_query: str,
        intent: str,
        query_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Format query result into natural language
        
        Args:
            user_query: Original user question
            intent: Classified intent
            query_result: Data from Query agent
            
        Returns:
            {
                "response": str,
                "duration_ms": int
            }
        """
        start_time = time.time()
        
        try:
            # Check for errors
            if query_result.get("error"):
                response = self._format_error_response(query_result)
            else:
                # Use LLM to format response
                prompt = self.prompt_templates.formatter_response(
                    user_query, intent, query_result
                )
                response = self.llm.invoke(prompt)
                
                # Handle AIMessage
                if hasattr(response, 'content'):
                    response = response.content
                else:
                    response = str(response)
                
                # Clean up response
                response = self._clean_response(response)
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            return {
                "response": response,
                "duration_ms": duration_ms
            }
            
        except Exception as e:
            return {
                "response": "I encountered an error while formatting the response. Please try again.",
                "duration_ms": int((time.time() - start_time) * 1000),
                "error": str(e)
            }
    
    def _format_error_response(self, query_result: Dict[str, Any]) -> str:
        """Format error messages with helpful suggestions"""
        error = query_result.get("error", "Unknown error")
        
        # Invalid entities
        if "Invalid entities" in error:
            invalid = query_result.get("invalid_entities", {})
            suggestions = query_result.get("suggestions", {})
            
            response = "❌ I couldn't find the following:\n\n"
            
            # Invalid properties
            if invalid.get("property"):
                response += f"**Properties:** {', '.join(invalid['property'])}\n\n"
                if suggestions.get("property"):
                    response += "Available properties:\n"
                    for prop in suggestions["property"][:5]:
                        response += f"  - {prop}\n"
            
            # Invalid tenants
            if invalid.get("tenant"):
                response += f"\n**Tenants:** {', '.join(invalid['tenant'])}\n\n"
                if suggestions.get("tenant"):
                    response += "Available tenants:\n"
                    for tenant in suggestions["tenant"][:5]:
                        response += f"  - {tenant}\n"
            
            response += "\nPlease try again with one of the available options."
            return response
        
        # Need at least 2 properties for comparison
        if "Need at least 2 properties" in error:
            invalid_props = query_result.get("invalid_properties", [])
            if invalid_props:
                available = query_result.get("available_properties", [])
                response = f"❌ I couldn't find: {', '.join(invalid_props)}\n\n"
                response += "Available properties:\n"
                for prop in available[:5]:
                    response += f"  - {prop}\n"
                response += "\nPlease specify two valid properties to compare."
                return response
            else:
                return "❌ Need at least 2 properties for comparison\n\nTip: Make sure to specify two different properties or two different time periods.\nFor example: \"Compare Building 140 to Building 180\" or \"Compare Building 17 in 2024 vs 2025\".\n\nPlease try again with the correct information."
        
        # No data found
        if "No data found" in error:
            return "❌ No data found for the specified filters\n\nPlease try a different property, time period, or query."
        
        # Generic error
        return f"❌ {error}\n\nPlease try again with the correct information."
    
    def _clean_response(self, response: str) -> str:
        """Clean up LLM response"""
        # Remove markdown formatting
        response = re.sub(r'\*\*([^*]+)\*\*', r'\1', response)
        response = re.sub(r'\*([^*]+)\*', r'\1', response)
        
        # Remove extra whitespace
        response = re.sub(r'\n{3,}', '\n\n', response)
        response = response.strip()
        
        return response
    
    def format_for_tracker(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format result for chain-of-thought tracker"""
        response_len = len(result.get("response", ""))
        
        return {
            "step": "Formatter",
            "duration_ms": result.get("duration_ms", 0),
            "description": f"Generated {response_len} character response",
            "metadata": {
                "response_length": response_len,
                "has_error": "error" in result
            }
        }

