"""
Response Agent - Formats query results into natural language responses
"""

from typing import Dict, Any
from langchain_core.language_models.llms import LLM
from src.llm_client import create_prompt


class ResponseAgent:
    """Formats data query results into natural language responses"""
    
    def __init__(self, llm: LLM):
        """Initialize the response agent
        
        Args:
            llm: Language model instance
        """
        self.llm = llm
    
    def format_response(self, 
                       intent: str, 
                       query_result: Dict[str, Any], 
                       user_query: str) -> str:
        """Format query results into a natural language response
        
        Args:
            intent: The classified intent
            query_result: Results from the query agent
            user_query: Original user query
            
        Returns:
            Formatted natural language response
        """
        # Handle errors
        if "error" in query_result:
            return self._format_error_response(query_result, intent)
        
        # Format based on intent
        if intent == "property_comparison":
            return self._format_comparison_response(query_result)
        elif intent == "pl_calculation":
            return self._format_pl_response(query_result)
        elif intent == "property_details":
            return self._format_property_details_response(query_result)
        elif intent == "tenant_info":
            return self._format_tenant_response(query_result)
        elif intent == "general_query":
            return self._format_general_response(query_result, user_query)
        else:
            return "I'm sorry, I couldn't process your request."
    
    def _format_comparison_response(self, result: Dict[str, Any]) -> str:
        """Format property comparison response"""
        prop1 = result["property1"]
        prop2 = result["property2"]
        comp = result["comparison"]
        
        response = f"""📊 Property Comparison:

**{prop1['property_name']}:**
- Total Revenue: €{prop1['total_revenue']:,.2f}
- Total Expenses: €{prop1['total_expenses']:,.2f}
- Net Profit: €{prop1['net_profit']:,.2f}
- Tenants: {', '.join(prop1['tenants']) if prop1['tenants'] else 'None'}

**{prop2['property_name']}:**
- Total Revenue: €{prop2['total_revenue']:,.2f}
- Total Expenses: €{prop2['total_expenses']:,.2f}
- Net Profit: €{prop2['net_profit']:,.2f}
- Tenants: {', '.join(prop2['tenants']) if prop2['tenants'] else 'None'}

**Comparison:**
- Revenue Difference: €{comp['revenue_diff']:,.2f}
- Profit Difference: €{comp['profit_diff']:,.2f}
- Better Performer: {comp['better_performer']}"""
        
        return response
    
    def _format_pl_response(self, result: Dict[str, Any]) -> str:
        """Format P&L response"""
        filters = result.get("filters", {})
        filter_desc = []
        
        if filters.get("property"):
            filter_desc.append(f"Property: {filters['property']}")
        if filters.get("year"):
            filter_desc.append(f"Year: {filters['year']}")
        if filters.get("quarter"):
            filter_desc.append(f"Quarter: {filters['quarter']}")
        if filters.get("month"):
            filter_desc.append(f"Month: {filters['month']}")
        
        filter_str = " | ".join(filter_desc) if filter_desc else "All Properties & All Time"
        
        response = f"""💰 Profit & Loss Statement

**Period:** {filter_str}

**Summary:**
- Total Revenue: €{result['total_revenue']:,.2f}
- Total Expenses: €{result['total_expenses']:,.2f}
- Net Profit: €{result['net_profit']:,.2f}

**Top Revenue Categories:**"""
        
        for item in result.get("revenue_breakdown", [])[:3]:
            response += f"\n- {item['ledger_category']}: €{item['amount']:,.2f}"
        
        response += "\n\n**Top Expense Categories:**"
        for item in result.get("expenses_breakdown", [])[:3]:
            response += f"\n- {item['ledger_category']}: €{item['amount']:,.2f}"
        
        return response
    
    def _format_property_details_response(self, result: Dict[str, Any]) -> str:
        """Format property details response"""
        response = f"""🏢 Property Details: {result['property_name']}

**Financial Performance:**
- Total Revenue: €{result['total_revenue']:,.2f}
- Total Expenses: €{result['total_expenses']:,.2f}
- Net Profit: €{result['net_profit']:,.2f}

**Tenants:** {', '.join(result['tenants']) if result['tenants'] else 'None'}

**Data Coverage:** {result['record_count']} transactions"""
        
        return response
    
    def _format_tenant_response(self, result: Dict[str, Any]) -> str:
        """Format tenant information response"""
        if "tenants" in result:
            return f"""👥 Available Tenants ({len(result['tenants'])}):\n\n""" + "\n".join(f"- {t}" for t in result['tenants'][:20])
        
        response = f"""👤 Tenant Information: {result['tenant']}

**Properties:**
{chr(10).join(f'- {p}' for p in result['properties'])}

**Total Revenue:** €{result['total_revenue']:,.2f}
**Transaction Count:** {result['record_count']}"""
        
        return response
    
    def _format_general_response(self, result: Dict[str, Any], user_query: str) -> str:
        """Format general information response using LLM"""
        system_message = f"""You are a helpful real estate assistant. Answer the user's question using this data:

{result}

Provide a clear, concise answer. Use specific numbers when available."""
        
        prompt = create_prompt(system_message, user_query)
        
        try:
            response = self.llm.invoke(prompt)
            return response.strip()
        except Exception as e:
            # Fallback to structured response
            return f"""📊 Dataset Overview:

- Total Records: {result.get('total_records', 'N/A')}
- Properties: {result.get('properties_count', 'N/A')}
- Tenants: {result.get('tenants_count', 'N/A')}
- Years Covered: {', '.join(str(y) for y in result.get('date_range', {}).get('years', []))}
- Total Revenue: €{result.get('total_revenue', 0):,.2f}
- Total Expenses: €{result.get('total_expenses', 0):,.2f}"""
    
    def _format_error_response(self, result: Dict[str, Any], intent: str) -> str:
        """Format error responses"""
        error_msg = result.get("error", "Unknown error occurred")
        
        response = f"❌ {error_msg}"
        
        # Add helpful suggestions
        if "available_properties" in result:
            response += f"\n\n**Available Properties:**\n" + "\n".join(f"- {p}" for p in result["available_properties"][:10])
        
        if "available_tenants" in result:
            response += f"\n\n**Available Tenants:**\n" + "\n".join(f"- {t}" for t in result["available_tenants"][:10])
        
        return response

