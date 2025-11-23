"""
Response Formatter – deterministic formatting for all intents
LLM used only for fallback formatting of multi-entity / complex queries.
"""

import time
import re
from typing import Dict, Any
from backend.utils.prompts import PromptTemplates


class ResponseFormatter:
    """Formats query results into natural language responses."""
    
    def __init__(self, llm):
        self.llm = llm
        self.prompt_templates = PromptTemplates()
    
    # ========================================================================
    # PUBLIC METHOD
    # ========================================================================
    def format_response(self, user_query: str, intent: str, query_result: Dict[str, Any]) -> Dict[str, Any]:
        start = time.time()
        
        try:
            if query_result.get("error"):
                response = self._format_error(query_result)
            else:
                response = self._format_success(user_query, intent, query_result)
            
            return {
                "response": response,
                "duration_ms": int((time.time() - start) * 1000)
            }
            
        except Exception as e:
            return {
                "response": "I encountered an error while formatting the response.",
                "duration_ms": int((time.time() - start) * 1000),
                "error": str(e)
            }
    
    # ========================================================================
    # ERROR HANDLING
    # ========================================================================
    def _format_error(self, result: Dict[str, Any]) -> str:
        err = result.get("error", "")

        # ---------------------------
        # CLARIFICATION NEEDED
        # ---------------------------
        if err == "clarification_needed":
            invalid = result.get("invalid_entities", {}) or {}
            suggestions = result.get("suggestions", {}) or {}
            clarification_msg = result.get("clarification_message", "")
            
            response_parts = []
            if clarification_msg:
                response_parts.append(clarification_msg)
        
            # Add invalid entities with suggestions
            if invalid and isinstance(invalid, dict):
                for entity_type, entities in invalid.items():
                    if entities and isinstance(entities, list):
                        entity_list = ", ".join(str(e) for e in entities[:3])
                        response_parts.append(f"I couldn't find the {entity_type} '{entity_list}' in the dataset.")
                        if entity_type in suggestions and suggestions[entity_type]:
                            available = suggestions[entity_type][:5]
                            response_parts.append(f"Available {entity_type}s are: {', '.join(str(a) for a in available)}.")
            
            if not response_parts:
                response_parts.append("I need more information to process your request.")
            
            response_parts.append("Please try again with the correct information.")
            return " ".join(response_parts)

        # ---------------------------
        # INVALID or MISSING ENTITIES
        # ---------------------------
        if "invalid_properties" in result:
            props = result["invalid_properties"]
            available = result.get("available_properties", [])
            msg = f"I couldn't find: {', '.join(props)}."
            if available:
                msg += "\nHere are valid properties: " + ", ".join(available[:5])
            return msg

        # ---------------------------
        # TEMPORAL ERROR
        # ---------------------------
        if err == "missing_period_data":
            req = result.get("periods_requested", [])
            found = result.get("periods_found", [])
            return (
                "I could not retrieve data for some of the requested periods.\n"
                f"Requested: {', '.join(req)}\n"
                f"Available: {', '.join(found)}"
            )

        # ---------------------------
        # NO FINANCIAL DATA
        # ---------------------------
        if err == "no_financial_data":
            p = result.get("property")
            y = result.get("year")
            q = result.get("quarter")
            m = result.get("month")
            period = q or m or y or ""
            return (
                f"No financial data is available for {p or 'the portfolio'}"
                + (f" in {period}" if period else "")
                + ". Try another time period."
            )

        # ---------------------------
        # NOT ENOUGH FOR COMPARISON
        # ---------------------------
        if "Need at least 2 properties" in err:
            available = result.get("available_properties", [])
            return (
                "You need at least two valid properties for comparison.\n"
                "Valid options include: " + ", ".join(available[:5])
            )

        # Fallback
        return err or "An unknown error occurred."
            
    # ========================================================================
    # SUCCESS FORMATTER ROUTER
    # ========================================================================
    def _format_success(self, user_query: str, intent: str, data: Dict[str, Any]) -> str:
        if intent == "pl_calculation":
            return self._format_pl(data)

        if intent == "property_comparison":
            return self._format_property_comparison(data)

        if intent == "temporal_comparison":
            return self._format_temporal_comparison(data)

        if intent == "property_details":
            return self._format_property_details(data)

        if intent == "tenant_info":
            return self._format_tenant_info(data)

        if intent == "multi_entity_query":
            return self._format_multi_entity(data)

        if intent == "analytics_query":
            return self._format_analytics(data)

        # fallback for general queries
        return self._fallback_llm(user_query, intent, data)

    # ========================================================================
    # FORMATTING HELPERS
    # ========================================================================
    def _format_currency(self, x):
        if x is None:
            return "N/A"
        try:
            return f"${float(x):,.2f}"
        except:
            return str(x)

    # ========================================================================
    # P&L
    # ========================================================================
    def _format_pl(self, data: Dict[str, Any]) -> str:
        entity = data.get("property")
        # Handle portfolio-level queries (PropCo, None, etc.)
        if not entity or entity in ["PropCo", "Portfolio", "All Properties", "All Buildings"]:
            entity = "all properties"
        else:
            entity = entity or "the portfolio"
        revenue = self._format_currency(data.get("total_revenue"))
        expenses = self._format_currency(abs(data.get("total_expenses", 0)))
        pnl = self._format_currency(data.get("net_profit"))

        # time reference
        period = (
            data.get("quarter")
            or data.get("month")
            or data.get("year")
            or ""
        )
        timeline = f" in {period}" if period else ""

        return (f"The total P&L for {entity}{timeline} is {pnl}. "
                f"Revenue was {revenue} and expenses were {expenses}.")

    # ========================================================================
    # PROPERTY COMPARISON
    # ========================================================================
    def _format_property_comparison(self, data: Dict[str, Any]) -> str:
        ranking = data.get("ranking", []) or []
        if not ranking:
            return "I compared the properties, but no financial differences were found."

        best = ranking[0] if ranking else {}
        worst = ranking[-1] if ranking else {}

        return (
            f"{best.get('property', 'Unknown')} has the highest net profit at "
            f"{self._format_currency(best.get('net_profit', 0))}, "
            f"while {worst.get('property', 'Unknown')} performs the lowest at "
            f"{self._format_currency(worst.get('net_profit', 0))}."
        )

    # ========================================================================
    # TEMPORAL COMPARISON (same property, different periods)
    # ========================================================================
    def _format_temporal_comparison(self, data: Dict[str, Any]) -> str:
        prop = data.get("property") or "the portfolio"
        ranking = data.get("ranking", []) or []

        if not ranking or len(ranking) < 2:
            return f"I couldn't compare periods for {prop} because insufficient data was found."

        best_period = ranking[0] if ranking else {}
        worst_period = ranking[-1] if ranking else {}

        return (
            f"For {prop}, the best-performing period is {best_period.get('period', 'Unknown')} "
            f"with {self._format_currency(best_period.get('net_profit', 0))}. "
            f"The lowest-performing period is {worst_period.get('period', 'Unknown')} "
            f"with {self._format_currency(worst_period.get('net_profit', 0))}."
        )

    # ========================================================================
    # PROPERTY DETAILS
    # ========================================================================
    def _format_property_details(self, data: Dict[str, Any]) -> str:
        prop = data.get("property") or data.get("property_name") or "the property"
        tenants = data.get("tenants", []) or []
        revenue = self._format_currency(data.get("total_revenue"))
        expenses = self._format_currency(abs(data.get("total_expenses", 0)))
        pnl = self._format_currency(data.get("net_profit"))

        tenant_count = len(tenants)
        tenant_text = "tenant" if tenant_count == 1 else "tenants"
        tenant_list = ", ".join(tenants) if tenants else "none"
        
        return (
            f"{prop} has {tenant_count} {tenant_text}. "
            f"{'Tenants: ' + tenant_list + '. ' if tenants else ''}"
            f"Its total revenue is {revenue}, expenses are {expenses}, "
            f"and net profit is {pnl}."
        )

    # ========================================================================
    # TENANT INFO
    # ========================================================================
    def _format_tenant_info(self, data: Dict[str, Any]) -> str:
        # Check if this is a property query (tenants of a building)
        if "property" in data:
            prop = data.get("property")
            tenants = data.get("tenants", []) or []
            revenue = self._format_currency(data.get("total_revenue", 0))
            expenses = self._format_currency(data.get("total_expenses", 0))
            pnl = self._format_currency(data.get("net_profit", 0))
            
            if tenants:
                tenants_str = ", ".join(tenants[:10])
                if len(tenants) > 10:
                    tenants_str += f", and {len(tenants) - 10} more"
                return (
                    f"{prop} has {len(tenants)} tenant(s): {tenants_str}. "
                    f"Total revenue: {revenue}, expenses: {expenses}, net profit: {pnl}."
                )
            else:
                return f"{prop} has no tenants recorded."
        
        # Original logic: tenant query (properties of a tenant)
        tenant = data.get("tenant") or "the tenant"
        props = data.get("properties", []) or []
        revenue = self._format_currency(data.get("total_revenue"))

        return (
            f"{tenant} operates in {len(props)} properties "
            f"and generated a total revenue of {revenue}."
        )

    # ========================================================================
    # MULTI-ENTITY
    # ========================================================================
    def _format_multi_entity(self, data: Dict[str, Any]) -> str:
        count = data.get("total_queries", 0)
        return f"I processed {count} separate requests and combined the results."

    # ========================================================================
    # ANALYTICS QUERY
    # ========================================================================
    def _format_analytics(self, data: Dict[str, Any]) -> str:
        """Format analytics query results (list, max, min, etc.)"""
        # Check for error first
        if "error" in data:
            return data.get("message", data["error"])
        
        operation = data.get("operation", "list")
        query_type = data.get("type", "list")
        # Get raw_query if available (for revenue vs profit detection)
        raw_query = data.get("raw_query", "").lower() if isinstance(data.get("raw_query"), str) else ""
        
        # Handle ranking queries (max/min/highest/lowest)
        if query_type == "ranking":
            if "property" in data:
                # Single property ranking (max/min profit or revenue)
                prop = data["property"]
                profit = self._format_currency(data.get("net_profit", 0))
                revenue = self._format_currency(data.get("total_revenue", 0))
                expenses = self._format_currency(data.get("total_expenses", 0))
                
                # Check if query was about revenue or profit
                is_revenue_query = "revenue" in raw_query and "profit" not in raw_query
                
                if is_revenue_query:
                    operation_desc = "highest revenue" if operation in ["max", "highest", "most"] else "lowest revenue"
                    return (
                        f"{prop} had the {operation_desc} with {revenue}. "
                        f"Net profit: {profit}, Expenses: {expenses}."
                    )
                else:
                    operation_desc = "most profit" if operation in ["max", "highest", "most"] else "least profit"
                    return (
                        f"{prop} made the {operation_desc} with a net profit of {profit}. "
                        f"Revenue: {revenue}, Expenses: {expenses}."
                    )
            elif "category" in data:
                # Category ranking (highest expense category)
                category = data["category"]
                amount = self._format_currency(data.get("total_amount", 0))
                operation_desc = "highest" if operation in ["max", "highest", "most"] else "lowest"
                return f"The {operation_desc} expense category is {category} with a total of {amount}."
            elif "rankings" in data:
                # Multiple rankings (top N)
                rankings = data.get("rankings", [])
                if not rankings:
                    return "No rankings found."
                
                result_parts = [f"Top {len(rankings)} properties by profit:"]
                for i, rank in enumerate(rankings, 1):
                    prop = rank.get("property", "Unknown")
                    profit = self._format_currency(rank.get("net_profit", 0))
                    result_parts.append(f"{i}. {prop}: {profit}")
                
                return " ".join(result_parts)
        
        # Handle list queries
        items = data.get("items", []) or []
        count = data.get("count", 0)
        
        if not items or count == 0:
            return "No items found."
        
        if operation == "list":
            if count <= 10:
                items_str = ", ".join(str(item) for item in items)
                return f"Found {count} items: {items_str}."
            else:
                items_str = ", ".join(str(item) for item in items[:10])
                return f"Found {count} items (showing first 10): {items_str}, ..."
        
        # For other operations, use fallback
        return f"Found {count} items matching your query."

    # ========================================================================
    # LLM FALLBACK
    # ========================================================================
    def _fallback_llm(self, user_query: str, intent: str, data: Dict[str, Any]) -> str:
        prompt = self.prompt_templates.formatter_response(user_query, intent, data)
        resp = self.llm.invoke(prompt)
        resp = resp.content if hasattr(resp, "content") else str(resp)
        return self._clean(resp)

    def _clean(self, x: str) -> str:
        x = re.sub(r"\*+", "", x)
        x = re.sub(r"\s+", " ", x)
        return x.strip()

    # ========================================================================
    # TRACKER SUPPORT
    # ========================================================================
    def format_for_tracker(self, result: Dict[str, Any]) -> Dict[str, Any]:
        resp = result.get("response", "")
        return {
            "step": "Formatter",
            "duration_ms": result.get("duration_ms", 0),
            "description": f"Generated {len(resp)} characters",
            "metadata": {
                "response_length": len(resp)
            }
        }
