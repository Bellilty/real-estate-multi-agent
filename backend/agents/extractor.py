"""
Extractor Agent v3 - Simplified JSON-based
Uses LLM to extract entities with JSON responses
NO MORE REGEX FALLBACKS!
"""

import json
import time
import re
from typing import Dict, Any, List
from backend.utils.prompts import PromptTemplates


class EntityExtractor:
    """Extracts entities from user queries using LLM with JSON output"""
    
    def __init__(self, llm, available_properties: List[str]):
        self.llm = llm
        self.available_properties = available_properties
        self.prompt_templates = PromptTemplates()
    
    def extract_entities(
        self,
        user_query: str,
        intent: str,
        chat_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Extract entities using LLM
        
        Args:
            user_query: The user's question
            intent: The classified intent
            chat_history: Previous conversation for context
            
        Returns:
            {
                "success": bool,
                "entities": dict,
                "duration_ms": int
            }
        """
        start_time = time.time()
        
        try:
            # Build prompt
            base_prompt = self.prompt_templates.extractor_entities(
                user_query, intent, self.available_properties
            )
            
            # Add chat history if available
            if chat_history:
                prompt = self.prompt_templates.add_chat_context(base_prompt, chat_history)
            else:
                prompt = base_prompt
            
            # Call LLM
            response = self.llm.invoke(prompt)
            
            # Parse JSON response
            entities = self._parse_json_response(response)
            
            # Post-process entities
            entities = self._normalize_entities(entities, intent, user_query)
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            return {
                "success": True,
                "entities": entities,
                "duration_ms": duration_ms
            }
            
        except Exception as e:
            # Fallback: try simple regex extraction
            fallback_entities = self._simple_fallback_extraction(user_query, intent)
            
            return {
                "success": True,
                "entities": fallback_entities,
                "duration_ms": int((time.time() - start_time) * 1000),
                "fallback_used": True,
                "error": str(e)
            }
    
    def _parse_json_response(self, response) -> Dict[str, Any]:
        """Parse LLM JSON response with fallbacks"""
        # Handle both string and AIMessage
        if hasattr(response, 'content'):
            text = response.content
        else:
            text = str(response)
        
        try:
            # Try direct JSON parse
            return json.loads(text.strip())
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            elif "```" in text:
                json_str = text.split("```")[1].split("```")[0].strip()
                return json.loads(json_str)
            
            # Try to find JSON object in text
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                json_str = text[start:end]
                return json.loads(json_str)
            
            raise ValueError(f"Could not parse JSON from response: {text[:200]}")
    
    def _normalize_entities(self, entities: Dict[str, Any], intent: str, user_query: str = "") -> Dict[str, Any]:
        """Normalize and validate extracted entities"""
        normalized = {}
        
        # Properties
        properties = entities.get("properties")
        if properties and isinstance(properties, list):
            normalized["properties"] = [p for p in properties if p]
            if intent == "property_comparison":
                normalized["count"] = len(normalized["properties"])
                normalized["requested_properties"] = normalized["properties"].copy()
        elif properties:
            normalized["properties"] = [properties]
        
        # Year - handle list for temporal_comparison
        year = entities.get("year")
        if year:
            if isinstance(year, list):
                # List of years for temporal_comparison
                normalized["year"] = [str(y) for y in year if str(y) in ["2024", "2025"]]
            elif str(year) in ["2024", "2025"]:
                normalized["year"] = str(year)
        
        # FALLBACK for temporal_comparison: Extract years from query if missing
        if intent == "temporal_comparison" and not normalized.get("year"):
            years_in_query = re.findall(r'20(24|25)', user_query)
            if len(years_in_query) >= 2:
                normalized["year"] = [f"20{y}" for y in years_in_query][:2]
        
        # Quarter
        quarter = entities.get("quarter")
        if quarter:
            quarter = str(quarter).upper()
            if quarter in ["Q1", "Q2", "Q3", "Q4"]:
                normalized["quarter"] = quarter
                # Also set year if not present
                if not normalized.get("year"):
                    normalized["year"] = "2024"  # Default
        
        # Month
        month = entities.get("month")
        if month:
            normalized["month"] = self._normalize_month(month)
        
        # Tenants
        tenants = entities.get("tenants")
        if tenants:
            if isinstance(tenants, list):
                normalized["tenants"] = tenants
            else:
                normalized["tenants"] = [tenants]
        
        # SPECIAL: For temporal_comparison, create "periods" list from year/quarter/month
        if intent == "temporal_comparison":
            periods = []
            
            # Check if year is a list (multiple years)
            if isinstance(normalized.get("year"), list):
                periods = normalized["year"]
            # Check if quarter is a list
            elif isinstance(normalized.get("quarter"), list):
                year_context = normalized.get("year", "2024")
                periods = [f"{year_context}-{q}" for q in normalized["quarter"]]
            # Check if month is a list
            elif isinstance(normalized.get("month"), list):
                year_context = normalized.get("year", "2024")
                periods = [f"{year_context}-{m}" for m in normalized["month"]]
            
            if periods:
                normalized["periods"] = periods
        
        return normalized
    
    def _normalize_month(self, month_str: str) -> str:
        """Normalize month to M01-M12 format"""
        month_str = str(month_str).lower().strip()
        
        # Already in M01 format
        if re.match(r'^m?\d{2}$', month_str):
            if month_str.startswith('m'):
                return month_str.upper()
            return f"M{month_str}"
        
        # Month names
        month_map = {
            "january": "M01", "jan": "M01",
            "february": "M02", "feb": "M02",
            "march": "M03", "mar": "M03",
            "april": "M04", "apr": "M04",
            "may": "M05",
            "june": "M06", "jun": "M06",
            "july": "M07", "jul": "M07",
            "august": "M08", "aug": "M08",
            "september": "M09", "sep": "M09",
            "october": "M10", "oct": "M10",
            "november": "M11", "nov": "M11",
            "december": "M12", "dec": "M12"
        }
        
        return month_map.get(month_str, month_str.upper())
    
    def _simple_fallback_extraction(self, user_query: str, intent: str) -> Dict[str, Any]:
        """Simple regex-based fallback if LLM fails"""
        entities = {}
        
        # Extract buildings
        buildings = re.findall(r'Building\s+\d+', user_query, re.IGNORECASE)
        if buildings:
            entities["properties"] = buildings
        
        # Extract years
        years = re.findall(r'\b(2024|2025)\b', user_query)
        if years:
            entities["year"] = years[0]
        
        # Extract quarters
        quarters = re.findall(r'\b(Q[1-4])\b', user_query, re.IGNORECASE)
        if quarters:
            entities["quarter"] = quarters[0].upper()
        
        # Extract tenants
        tenants = re.findall(r'Tenant\s+\d+', user_query, re.IGNORECASE)
        if tenants:
            entities["tenants"] = tenants
        
        return entities
    
    def format_for_tracker(self, result: Dict[str, Any], intent: str) -> Dict[str, Any]:
        """Format result for chain-of-thought tracker"""
        entities = result.get("entities", {})
        
        # Build description based on intent
        if intent == "property_comparison":
            props = entities.get("properties", [])
            desc = f"Extracted {len(props)} properties for comparison: {', '.join(props)}"
        elif intent == "pl_calculation":
            prop = entities.get("properties", ["None"])[0] if entities.get("properties") else "None"
            year = entities.get("year", "None")
            desc = f"Extracted P&L parameters: Property={prop}, Year={year}"
        elif intent == "tenant_info":
            tenant = entities.get("tenants", ["None"])[0] if entities.get("tenants") else "None"
            desc = f"Extracted tenant: {tenant}"
        else:
            desc = f"Extracted entities: {entities}"
        
        return {
            "step": "Extractor",
            "duration_ms": result.get("duration_ms", 0),
            "description": desc,
            "metadata": {
                "entities": entities,
                "fallback_used": result.get("fallback_used", False)
            }
        }

