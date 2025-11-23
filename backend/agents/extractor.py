"""
UNIFIED & ROBUST ENTITY EXTRACTOR
Supports:
- temporal_comparison
- property_comparison
- multi_entity_query
- analytics_query (list / max / min / top / count)
- pl_calculation
- tenant_info
- fallback regex (improved)
"""

import json
import time
import re
from typing import Dict, Any, List
from backend.utils.prompts import PromptTemplates


GENERIC_PROPERTIES = {"PropCo", "Portfolio", "All Properties", "All Buildings"}


class EntityExtractor:
    """Extracts entities from user queries using LLM with JSON output."""
    
    def __init__(self, llm, available_properties: List[str]):
        self.llm = llm
        self.available_properties = available_properties
        self.prompt_templates = PromptTemplates()
    
    # -------------------------------------------------------------
    # MAIN EXTRACTION
    # -------------------------------------------------------------
    def extract_entities(self, user_query: str, intent: str, chat_history=None):
        start = time.time()
        
        try:
            base_prompt = self.prompt_templates.extractor_entities(
                user_query, intent, self.available_properties
            )
            
            prompt = (
                self.prompt_templates.add_chat_context(base_prompt, chat_history)
                if chat_history
                else base_prompt
            )

            llm_response = self.llm.invoke(prompt)
            entities = self._parse_json_response(llm_response)
            
            entities = self._normalize_entities(entities, intent, user_query)
            
            return {
                "success": True,
                "entities": entities,
                "duration_ms": int((time.time() - start) * 1000),
            }
            
        except Exception as e:
            # Improved fallback
            fb = self._fallback_regex_extraction(user_query, intent)
            return {
                "success": True,
                "entities": fb,
                "duration_ms": int((time.time() - start) * 1000),
                "fallback_used": True,
                "error": str(e),
            }
    
    # -------------------------------------------------------------
    # JSON PARSING
    # -------------------------------------------------------------
    def _parse_json_response(self, response):
        text = response.content if hasattr(response, "content") else str(response)
        text = text.strip()

        # strict
        try:
            return json.loads(text)
        except:
            pass

        # inside ```json
        if "```" in text:
            for block in text.split("```"):
                if "{" in block:
                    try:
                        return json.loads(block[block.find("{"):block.rfind("}")+1])
                    except:
                        pass

        # last chance
        if "{" in text and "}" in text:
            try:
                return json.loads(text[text.find("{"): text.rfind("}")+1])
            except:
                pass

        raise ValueError("Extractor: invalid JSON returned")

    # -------------------------------------------------------------
    # ENTITY NORMALISATION
    # -------------------------------------------------------------
    def _normalize_entities(self, ent: Dict[str, Any], intent: str, user_query: str):
        out = {}
        
        # --------- PROPERTIES ----------
        props = ent.get("properties")
        if props is None:
            out["properties"] = None
        elif isinstance(props, list):
            out["properties"] = [p for p in props if p]
        else:
            out["properties"] = [props]

        # handle generic "all"
        all_patterns = [
            "all buildings", "all properties", "for all properties", "all the buildings",
            "revenue for all properties", "expenses for all properties",
            "all my properties", "all my buildings", "for all my properties",
            "all of my properties", "all of my buildings"
        ]
        if any(x in user_query.lower() for x in all_patterns):
            out["properties"] = ["PropCo"]
            # Also set property (singular) for consistency
            if not out.get("property"):
                out["property"] = "PropCo"

        # special case analytics_query: always detect operation
        if intent == "analytics_query":
            out["operation"] = self._detect_analytics_operation(user_query)
            # For listing queries, properties can be None
            if out["operation"] == "list":
                out["properties"] = out.get("properties", None)
            # Still extract year/quarter for analytics if present (for filtering)
            year = ent.get("year")
            if isinstance(year, list):
                out["year"] = [str(y) for y in year]
            elif year:
                out["year"] = str(year)
            quarter = ent.get("quarter")
            if quarter:
                out["quarter"] = quarter
            return out

        # --------- YEAR ----------
        year = ent.get("year")
        if isinstance(year, list):
            out["year"] = [str(y) for y in year]
        elif year:
            out["year"] = str(year)

        # fallback for temporal: extract 2024/2025
        if intent == "temporal_comparison" and not out.get("year"):
            yrs = re.findall(r'20(24|25)', user_query)
            if len(yrs) >= 2:
                out["year"] = [f"20{x}" for x in yrs]

        # --------- QUARTER ----------
        quarter = ent.get("quarter")
        if isinstance(quarter, list):
            out["quarter"] = [q.upper() for q in quarter]
        elif quarter:
            out["quarter"] = str(quarter).upper()

        # --------- MONTH ----------
        month = ent.get("month")
        if month:
            out["month"] = self._normalize_month(month)
        
        # --------- TENANTS ----------
        tenants = ent.get("tenants")
        if tenants:
            out["tenants"] = tenants if isinstance(tenants, list) else [tenants]

        # --------- TEMPORAL_COMPARISON → periods ---------
        if intent == "temporal_comparison":
            periods = []
            if isinstance(out.get("quarter"), list):
                periods = out["quarter"]
            elif isinstance(out.get("year"), list):
                periods = out["year"]
            elif isinstance(out.get("month"), list):
                periods = out["month"]

            if periods:
                out["periods"] = periods

        # --------- MULTI ENTITY ---------
        if intent == "multi_entity_query":
            out["sub_queries"] = self._extract_multi_subqueries(user_query)

        return out

    # -------------------------------------------------------------
    # ANALYTICS OPERATION DETECTOR
    # -------------------------------------------------------------
    def _detect_analytics_operation(self, query: str):
        q = query.lower()

        # Priority order: most specific first
        if "highest" in q or "most" in q or ("max" in q and ("profit" in q or "expense" in q or "revenue" in q)):
            return "max"
        if "lowest" in q or "least" in q or ("min" in q and ("profit" in q or "expense" in q or "revenue" in q)):
            return "min"
        if "top" in q:
            return "top"
        if "bottom" in q:
            return "bottom"
        if "list" in q or ("all" in q and ("properties" in q or "tenants" in q or "buildings" in q)):
            return "list"
        if "sum" in q or "total" in q:
            return "sum"
        if "average" in q or "avg" in q or "mean" in q:
            return "avg"
        if "count" in q:
            return "count"

        return "list"

    # -------------------------------------------------------------
    # MULTI ENTITY SUB-QUERY PARSER
    # -------------------------------------------------------------
    def _extract_multi_subqueries(self, text: str):
        """
        Supports:
        - Building 17 in 2024 AND Building 180 in 2025
        - PropCo 2024 and Building 140 Q1
        - Building 17 Q2 and PropCo Q1 2025
        """
        entities = re.split(r"\band\b|\balso\b", text, flags=re.IGNORECASE)
        sub_queries = []

        for e in entities:
            prop = re.findall(r'(PropCo|Building\s+\d+)', e, re.IGNORECASE)
            year = re.findall(r'\b(2024|2025)\b', e)
            quarter = re.findall(r'\b(Q[1-4])\b', e, re.IGNORECASE)

            sub = {"raw": e.strip()}

            if prop:
                sub["properties"] = [prop[0].title()]  # fix casing
            if year:
                sub["year"] = year[0]
            if quarter:
                sub["quarter"] = quarter[0].upper()

            sub_queries.append(sub)

        return sub_queries

    # -------------------------------------------------------------
    # NORMALIZE MONTH NAMES
    # -------------------------------------------------------------
    def _normalize_month(self, m):
        m = str(m).lower().strip()
        table = {
            "jan": "M01", "january": "M01",
            "feb": "M02", "february": "M02",
            "mar": "M03", "march": "M03",
            "apr": "M04", "april": "M04",
            "may": "M05",
            "jun": "M06", "june": "M06",
            "jul": "M07", "july": "M07",
            "aug": "M08", "august": "M08",
            "sep": "M09", "september": "M09",
            "oct": "M10", "october": "M10",
            "nov": "M11", "november": "M11",
            "dec": "M12", "december": "M12",
        }
        return table.get(m, m.upper())

    # -------------------------------------------------------------
    # IMPROVED FALLBACK
    # -------------------------------------------------------------
    def _fallback_regex_extraction(self, text: str, intent: str):
        out = {}
        
        # buildings
        props = re.findall(r"(PropCo|Building\s+\d+)", text, re.IGNORECASE)
        if props:
            out["properties"] = [p.title() for p in props]
        
        # years
        years = re.findall(r"\b(2024|2025)\b", text)
        if years:
            out["year"] = years if intent == "temporal_comparison" else years[0]

        # quarter
        q = re.findall(r"\b(Q[1-4])\b", text, re.IGNORECASE)
        if q:
            out["quarter"] = [x.upper() for x in q] if intent == "temporal_comparison" else q[0].upper()
        
        # tenants
        t = re.findall(r"Tenant\s+\d+", text, re.IGNORECASE)
        if t:
            out["tenants"] = t

        # analytics fallback
        if intent == "analytics_query":
            out["operation"] = self._detect_analytics_operation(text)

        return out
