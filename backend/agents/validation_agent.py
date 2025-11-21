"""
Enhanced Validation Agent - Routes to 3 Branches
MISSING → Clarifier
AMBIGUOUS → Disambiguation
VALID → Retriever
"""

import time
from typing import Dict, Any, Literal


class ValidationAgent:
    """
    Enhanced validation with 3-way routing
    
    Routes:
    1. MISSING → entities are incomplete, need clarification
    2. AMBIGUOUS → entities have multiple matches, need disambiguation
    3. VALID → entities are verified, proceed to retrieval
    """
    
    def __init__(self, data_loader):
        self.data_loader = data_loader
    
    def validate(self, intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate entities and determine routing
        
        Returns:
        {
            "status": "ok" | "missing" | "ambiguous",
            "entities": dict,  # valid entities
            "invalid_entities": dict,
            "missing_fields": list,
            "ambiguous_entities": dict,
            "suggestions": dict,
            "needs_clarification": bool,
            "notes": str,
            "duration_ms": int
        }
        """
        start_time = time.time()        
        # Skip validation for temporal_comparison (special structure)
        if intent == "temporal_comparison":
            return self._validate_temporal_comparison(entities, start_time)
        
        # Run standard validation
        validation_result = self.data_loader.validate_entities(entities)
        
        # Analyze validation result
        is_valid = validation_result["valid"]
        invalid_entities = validation_result.get("invalid_entities", {})
        suggestions = validation_result.get("suggestions", {})
        
        # Determine status
        validation_status: Literal["MISSING", "AMBIGUOUS", "VALID"] = "VALID"
        missing_fields = []
        ambiguous_entities = {}
        reasoning_parts = []
        
        if not is_valid:
            # Check if entities are missing or invalid
            if "property" in invalid_entities or "properties" in invalid_entities:
                invalid_props = invalid_entities.get("property", invalid_entities.get("properties", []))
                
                # Check if it's a partial match (ambiguous)
                for prop in invalid_props:
                    candidates = self._find_fuzzy_matches(prop, self.data_loader.get_properties())
                    if len(candidates) > 1:
                        validation_status = "AMBIGUOUS"
                        ambiguous_entities.setdefault("properties", []).append({
                            "input": prop,
                            "candidates": candidates
                        })
                        reasoning_parts.append(f"Property '{prop}' is ambiguous ({len(candidates)} matches)")
                    elif len(candidates) == 0:
                        validation_status = "MISSING"
                        missing_fields.append(f"property: {prop}")
                        reasoning_parts.append(f"Property '{prop}' not found")
            
            if "tenant" in invalid_entities or "tenants" in invalid_entities:
                invalid_tenants = invalid_entities.get("tenant", invalid_entities.get("tenants", []))
                
                for tenant in invalid_tenants:
                    candidates = self._find_fuzzy_matches(tenant, self.data_loader.get_tenants())
                    if len(candidates) > 1:
                        validation_status = "AMBIGUOUS"
                        ambiguous_entities.setdefault("tenants", []).append({
                            "input": tenant,
                            "candidates": candidates
                        })
                        reasoning_parts.append(f"Tenant '{tenant}' is ambiguous ({len(candidates)} matches)")
                    elif len(candidates) == 0:
                        validation_status = "MISSING"
                        missing_fields.append(f"tenant: {tenant}")
                        reasoning_parts.append(f"Tenant '{tenant}' not found")
        else:
            reasoning_parts.append("All entities validated successfully")
        
        # Check for missing required fields based on intent
        required_fields = self._get_required_fields(intent)
        for field in required_fields:
            if field not in entities or not entities[field]:
                validation_status = "MISSING"
                missing_fields.append(field)
                reasoning_parts.append(f"Required field '{field}' is missing")
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        reasoning = "; ".join(reasoning_parts) if reasoning_parts else "Validation passed"        
        # Map to unified status
        status_map = {"VALID": "ok", "MISSING": "missing", "AMBIGUOUS": "ambiguous"}
        unified_status = status_map.get(validation_status, "ok")
        
        return {
            "status": unified_status,
            "validation_status": validation_status,  # Keep for routing
            "entities": entities if is_valid else {},
            "invalid_entities": invalid_entities,
            "missing_fields": missing_fields,
            "ambiguous_entities": ambiguous_entities,
            "suggestions": suggestions,
            "needs_clarification": validation_status in ["MISSING", "AMBIGUOUS"],
            "notes": reasoning,
            "duration_ms": duration_ms
        }
    
    def _validate_temporal_comparison(self, entities: Dict[str, Any], start_time: float) -> Dict[str, Any]:
        """Special validation for temporal comparison"""
        # Check if we have periods or components to build periods
        has_periods = "periods" in entities and len(entities.get("periods", [])) >= 2
        
        # Check if we can build periods from year/quarter/month
        can_build_periods = False
        if "year" in entities and isinstance(entities["year"], list) and len(entities["year"]) >= 2:
            can_build_periods = True
        elif "quarter" in entities and isinstance(entities["quarter"], list) and len(entities["quarter"]) >= 2:
            can_build_periods = True
        elif "month" in entities and isinstance(entities["month"], list) and len(entities["month"]) >= 2:
            can_build_periods = True
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        if has_periods or can_build_periods:
            return {
                "status": "ok",
                "validation_status": "VALID",
                "entities": entities,
                "invalid_entities": {},
                "missing_fields": [],
                "ambiguous_entities": {},
                "suggestions": {},
                "needs_clarification": False,
                "notes": "Temporal comparison entities validated",
                "duration_ms": duration_ms
            }
        else:
            return {
                "status": "missing",
                "validation_status": "MISSING",
                "entities": {},
                "invalid_entities": {},
                "missing_fields": ["periods (need at least 2 time periods)"],
                "ambiguous_entities": {},
                "suggestions": {},
                "needs_clarification": True,
                "notes": "Temporal comparison requires at least 2 time periods",
                "duration_ms": duration_ms
            }
    
    def _find_fuzzy_matches(self, query: str, candidates: list, threshold: float = 0.6) -> list:
        """Find fuzzy matches for a query string"""
        from difflib import SequenceMatcher
        
        matches = []
        query_lower = query.lower()
        
        for candidate in candidates:
            candidate_lower = candidate.lower()
            
            # Exact match
            if query_lower == candidate_lower:
                return [candidate]  # Single exact match
            
            # Substring match or similarity
            if query_lower in candidate_lower or candidate_lower in query_lower:
                similarity = SequenceMatcher(None, query_lower, candidate_lower).ratio()
                if similarity >= threshold:
                    matches.append((candidate, similarity))
        
        # Sort by similarity
        matches.sort(key=lambda x: x[1], reverse=True)
        
        return [m[0] for m in matches[:5]]  # Top 5 matches
    
    def _get_required_fields(self, intent: str) -> list:
        """Get required fields for an intent"""
        required_map = {
            "property_comparison": ["properties"],  # Need at least 2
            "temporal_comparison": ["periods"],  # Need at least 2
            "pl_calculation": [],  # Flexible
            "property_details": ["properties"],
            "tenant_info": ["tenants"],
            "multi_entity_query": ["sub_queries"],
        }
        
        return required_map.get(intent, [])

