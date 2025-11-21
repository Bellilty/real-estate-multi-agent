"""
Disambiguation Agent - Resolves Ambiguous Entities
Handles cases like "Building 18" vs "Building 180"
"""

import time
from typing import Dict, Any, List
from difflib import SequenceMatcher


class DisambiguationAgent:
    """
    Resolves ambiguous entity references
    
    Examples:
    - "Building 18" → could be "Building 18" or "Building 180"
    - "Tenant" → multiple tenants exist
    - Partial matches from SearchTool
    """
    
    def __init__(self, data_loader):
        self.data_loader = data_loader
    
    def process(self, entities: Dict[str, Any], ambiguous_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Disambiguate entities
        
        Args:
            entities: Extracted entities
            ambiguous_info: Information about ambiguities from validation
        
        Returns:
        {
            "status": "ok" | "ambiguous" | "error",
            "entities": dict,  # clarified entities
            "suggestions": dict,
            "needs_clarification": bool,
            "clarification_message": str,
            "notes": str,
            "duration_ms": int
        }
        """
        start_time = time.time()        
        clarified = entities.copy()
        suggestions = {}
        needs_clarification = False
        clarification_message = ""
        reasoning_parts = []
        
        # Disambiguate properties
        if "properties" in entities:
            properties = entities["properties"]
            if isinstance(properties, list):
                resolved_props = []
                for prop in properties:
                    result = self._disambiguate_property(prop)
                    
                    if result["resolved"]:
                        resolved_props.append(result["resolved_to"])
                        reasoning_parts.append(f"'{prop}' → '{result['resolved_to']}'")
                    elif result["candidates"]:
                        # Multiple candidates
                        suggestions["properties"] = result["candidates"]
                        needs_clarification = True
                        clarification_message = f"Did you mean: {', '.join(result['candidates'][:5])}?"
                    else:
                        # No match
                        resolved_props.append(prop)  # Keep original
                
                clarified["properties"] = resolved_props
        
        # Disambiguate tenants
        if "tenants" in entities:
            tenants = entities["tenants"]
            if isinstance(tenants, list):
                resolved_tenants = []
                for tenant in tenants:
                    result = self._disambiguate_tenant(tenant)
                    
                    if result["resolved"]:
                        resolved_tenants.append(result["resolved_to"])
                        reasoning_parts.append(f"'{tenant}' → '{result['resolved_to']}'")
                    elif result["candidates"]:
                        suggestions["tenants"] = result["candidates"]
                        needs_clarification = True
                        if clarification_message:
                            clarification_message += f" Or tenant: {', '.join(result['candidates'][:5])}?"
                        else:
                            clarification_message = f"Did you mean tenant: {', '.join(result['candidates'][:5])}?"
                    else:
                        resolved_tenants.append(tenant)
                
                clarified["tenants"] = resolved_tenants
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        reasoning = "; ".join(reasoning_parts) if reasoning_parts else "No disambiguation needed"        
        status = "ambiguous" if needs_clarification else "ok"
        
        return {
            "status": status,
            "entities": clarified,
            "suggestions": suggestions,
            "needs_clarification": needs_clarification,
            "clarification_message": clarification_message,
            "notes": reasoning,
            "duration_ms": duration_ms
        }
    
    def _disambiguate_property(self, prop_name: str) -> Dict[str, Any]:
        """
        Disambiguate a single property name
        
        Returns:
        {
            "resolved": bool,
            "resolved_to": str or None,
            "candidates": list
        }
        """
        all_properties = self.data_loader.get_properties()
        
        # Exact match (case-insensitive)
        for p in all_properties:
            if p.lower() == prop_name.lower():
                return {
                    "resolved": True,
                    "resolved_to": p,
                    "candidates": []
                }
        
        # Fuzzy match - find candidates
        candidates = []
        prop_lower = prop_name.lower()
        
        for p in all_properties:
            p_lower = p.lower()
            
            # Substring match
            if prop_lower in p_lower or p_lower in prop_lower:
                similarity = SequenceMatcher(None, prop_lower, p_lower).ratio()
                candidates.append((p, similarity))
        
        # Sort by similarity
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        # If only one strong candidate (>0.8 similarity), auto-resolve
        if len(candidates) == 1 and candidates[0][1] > 0.8:
            return {
                "resolved": True,
                "resolved_to": candidates[0][0],
                "candidates": []
            }
        
        # Multiple candidates
        if len(candidates) > 1:
            return {
                "resolved": False,
                "resolved_to": None,
                "candidates": [c[0] for c in candidates[:5]]
            }
        
        # No candidates
        return {
            "resolved": False,
            "resolved_to": None,
            "candidates": []
        }
    
    def _disambiguate_tenant(self, tenant_name: str) -> Dict[str, Any]:
        """
        Disambiguate a single tenant name
        
        Returns:
        {
            "resolved": bool,
            "resolved_to": str or None,
            "candidates": list
        }
        """
        all_tenants = self.data_loader.get_tenants()
        
        # Exact match (case-insensitive)
        for t in all_tenants:
            if t.lower() == tenant_name.lower():
                return {
                    "resolved": True,
                    "resolved_to": t,
                    "candidates": []
                }
        
        # Fuzzy match
        candidates = []
        tenant_lower = tenant_name.lower()
        
        for t in all_tenants:
            t_lower = t.lower()
            
            if tenant_lower in t_lower or t_lower in tenant_lower:
                similarity = SequenceMatcher(None, tenant_lower, t_lower).ratio()
                candidates.append((t, similarity))
        
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Auto-resolve if single strong match
        if len(candidates) == 1 and candidates[0][1] > 0.8:
            return {
                "resolved": True,
                "resolved_to": candidates[0][0],
                "candidates": []
            }
        
        if len(candidates) > 1:
            return {
                "resolved": False,
                "resolved_to": None,
                "candidates": [c[0] for c in candidates[:5]]
            }
        
        return {
            "resolved": False,
            "resolved_to": None,
            "candidates": []
        }

