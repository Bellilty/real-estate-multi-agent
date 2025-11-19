"""
Extractor Agent - Extracts entities and parameters from user queries
"""

from typing import Dict, Any, List
from langchain_core.language_models.llms import LLM
from src.llm_client import create_prompt


class ExtractorAgent:
    """Extracts entities like property names, dates, tenants from user queries"""
    
    def __init__(self, llm: LLM, available_properties: List[str]):
        """Initialize the extractor agent
        
        Args:
            llm: Language model instance
            available_properties: List of available property names in the dataset
        """
        self.llm = llm
        self.available_properties = available_properties
    
    def extract_entities(self, user_query: str, intent: str) -> Dict[str, Any]:
        """Extract relevant entities based on intent
        
        Args:
            user_query: The user's query
            intent: The classified intent
            
        Returns:
            Dictionary with extracted entities
        """
        if intent == "property_comparison":
            return self._extract_comparison_entities(user_query)
        elif intent == "pl_calculation":
            return self._extract_pl_entities(user_query)
        elif intent == "property_details":
            return self._extract_property_entities(user_query)
        elif intent == "tenant_info":
            return self._extract_tenant_entities(user_query)
        else:
            return {}
    
    def _extract_comparison_entities(self, user_query: str) -> Dict[str, Any]:
        """Extract properties for comparison"""
        system_message = f"""Extract property names from the user query.

Available properties in the system: {', '.join(self.available_properties)}

Return property names in this exact format:
PROPERTY1: <name>
PROPERTY2: <name>

Use the exact property names from the available list. If unsure, return UNKNOWN."""

        prompt = create_prompt(system_message, user_query)
        
        try:
            response = self.llm.invoke(prompt).strip()
            
            properties = []
            for line in response.split("\n"):
                if "PROPERTY" in line and ":" in line:
                    prop = line.split(":", 1)[1].strip()
                    if prop and prop != "UNKNOWN":
                        properties.append(prop)
            
            return {
                "properties": properties[:2],  # Max 2 properties for comparison
                "count": len(properties[:2])
            }
            
        except Exception as e:
            return {"properties": [], "count": 0, "error": str(e)}
    
    def _extract_pl_entities(self, user_query: str) -> Dict[str, Any]:
        """Extract timeframe and property for P&L calculation"""
        system_message = f"""Extract time period and property information for P&L calculation.

Available properties: {', '.join(self.available_properties)}

Extract these fields:
- YEAR: e.g., 2024, 2025
- QUARTER: e.g., 2024-Q1, 2024-Q2
- MONTH: e.g., 2024-M01, 2024-M12
- PROPERTY: property name

Format:
YEAR: <year or ALL>
QUARTER: <quarter or ALL>
MONTH: <month or ALL>
PROPERTY: <property name or ALL>

Use "ALL" if not specified."""

        prompt = create_prompt(system_message, user_query)
        
        try:
            response = self.llm.invoke(prompt).strip()
            
            entities = {
                "year": None,
                "quarter": None,
                "month": None,
                "property": None
            }
            
            for line in response.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    if value and value.upper() != "ALL":
                        if key == "year":
                            entities["year"] = value
                        elif key == "quarter":
                            entities["quarter"] = value
                        elif key == "month":
                            entities["month"] = value
                        elif key == "property":
                            entities["property"] = value
            
            return entities
            
        except Exception as e:
            return {"year": None, "quarter": None, "month": None, "property": None, "error": str(e)}
    
    def _extract_property_entities(self, user_query: str) -> Dict[str, Any]:
        """Extract property name for details query"""
        system_message = f"""Extract the property name from the user query.

Available properties: {', '.join(self.available_properties)}

Return in this format:
PROPERTY: <exact property name from the list>

If the property is not in the list or unclear, return: PROPERTY: UNKNOWN"""

        prompt = create_prompt(system_message, user_query)
        
        try:
            response = self.llm.invoke(prompt).strip()
            
            property_name = None
            if "PROPERTY:" in response:
                property_name = response.split("PROPERTY:")[1].strip()
                if property_name == "UNKNOWN":
                    property_name = None
            
            return {"property": property_name}
            
        except Exception as e:
            return {"property": None, "error": str(e)}
    
    def _extract_tenant_entities(self, user_query: str) -> Dict[str, Any]:
        """Extract tenant information"""
        system_message = """Extract tenant name or tenant-related information from the query.

Return in format:
TENANT: <tenant name or description>"""

        prompt = create_prompt(system_message, user_query)
        
        try:
            response = self.llm.invoke(prompt).strip()
            
            tenant = None
            if "TENANT:" in response:
                tenant = response.split("TENANT:")[1].strip()
            
            return {"tenant": tenant}
            
        except Exception as e:
            return {"tenant": None, "error": str(e)}

