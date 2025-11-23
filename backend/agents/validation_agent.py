"""
ValidationAgent – Clean 3-way routing:
- MISSING: Required entities missing or invalid
- AMBIGUOUS: Multiple possible matches (fuzzy)
- OK: Entities valid and unambiguous
"""

import time
from typing import Dict, Any, List, Literal


class ValidationAgent:
    """
    Validates extracted entities and decides routing:
    - missing      → Clarification Agent
    - ambiguous    → Disambiguation Agent
    - ok           → QueryAgent
    """

    def __init__(self, data_loader):
        self.data_loader = data_loader

    # =====================================================================
    # MAIN ENTRY
    # =====================================================================
    def validate(self, intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        start = time.time()

        notes = []
        missing = []
        ambiguous = {}
        invalid = {}
        suggestions = {}

        props_valid = self.data_loader.get_properties()
        tenants_valid = self.data_loader.get_tenants()

        # ================================================================
        # SPECIAL CASE – TEMPORAL COMPARISON
        # ================================================================
        if intent == "temporal_comparison":
            return self._validate_temporal_comparison(entities, start)

        # ================================================================
        # 1. VALIDATE PROPERTIES (skip for analytics_query)
        # ================================================================
        if intent != "analytics_query":  # analytics_query doesn't require properties
            props = entities.get("properties", [])
            # Handle None case
            if props is None:
                props = []
            elif isinstance(props, str):
                props = [props]

            # Valid portfolio-level properties
            portfolio_properties = {"PropCo", "Portfolio", "All Properties", "All Buildings"}
            
            for p in props:
                # Accept portfolio-level properties
                if p in portfolio_properties:
                    notes.append(f"Portfolio-level query: {p}")
                    continue
                
                if p not in props_valid:
                    # Fuzzy match
                    cands = self._fuzzy_candidates(p, props_valid)
                    if len(cands) == 1:
                        # Auto-correct
                        notes.append(f"Auto-matched '{p}' → '{cands[0]}'")
                        entities["properties"] = [
                            cands[0] if x == p else x for x in entities["properties"]
                        ]
                    elif len(cands) > 1:
                        ambiguous.setdefault("properties", []).append({
                            "input": p,
                            "candidates": cands
                        })
                    else:
                        invalid.setdefault("properties", []).append(p)

        # ================================================================
        # 2. VALIDATE TENANTS IF NEEDED (only if tenant specified, not property)
        # ================================================================
        if intent == "tenant_info":
            # Special case: "Show me the tenants for Building X" - has property, not tenant
            has_property = entities.get("property") or entities.get("properties")
            if not has_property:
                # Original logic: validate tenant
                t = entities.get("tenants", [])
                if isinstance(t, str):
                    t = [t]

                for tenant in t:
                    if tenant not in tenants_valid:
                        cands = self._fuzzy_candidates(tenant, tenants_valid)
                        if len(cands) > 1:
                            ambiguous.setdefault("tenants", []).append({
                                "input": tenant,
                                "candidates": cands
                            })
                        else:
                            invalid.setdefault("tenants", []).append(tenant)

        # ================================================================
        # 3. CHECK REQUIRED FIELDS (skip for analytics_query)
        # ================================================================
        if intent != "analytics_query":  # analytics_query doesn't require entities
            missing_required = self._get_missing_required(intent, entities)
            if missing_required:
                missing.extend(missing_required)

        # ================================================================
        # FINAL ROUTING DECISION
        # ================================================================
        # Special case: analytics_query doesn't require validation
        if intent == "analytics_query":
            status = "ok"
            notes.append("Analytics query - no entity validation required")
        elif ambiguous:
            status = "ambiguous"
            notes.append("Some entities are ambiguous")

        elif invalid or missing:
            status = "missing"
            notes.append("Some entities are missing or invalid")

        else:
            status = "ok"
            notes.append("All entities validated")

        return {
            "status": status,
            "validation_status": status,
            "entities": entities if status == "ok" else {},
            "invalid_entities": invalid,
            "missing_fields": missing,
            "ambiguous_entities": ambiguous,
            "suggestions": suggestions,
            "needs_clarification": status in ["missing", "ambiguous"],
            "notes": "; ".join(notes),
            "duration_ms": int((time.time() - start) * 1000),
        }

    # =====================================================================
    # SPECIAL VALIDATION FOR TEMPORAL COMPARISON
    # =====================================================================
    def _validate_temporal_comparison(self, entities: Dict[str, Any], start: float):
        props = entities.get("properties", [])
        periods = entities.get("periods", [])

        valid_props = self.data_loader.get_properties()

        # 1 property required
        if not props or props[0] not in valid_props:
            return {
                "status": "missing",
                "validation_status": "missing",
                "entities": {},
                "invalid_entities": {"properties": props},
                "missing_fields": ["properties"],
                "ambiguous_entities": {},
                "suggestions": {},
                "needs_clarification": True,
                "notes": "Temporal comparison requires one valid property",
                "duration_ms": int((time.time() - start) * 1000),
            }

        # Two time periods required
        if not periods or len(periods) < 2:
            return {
                "status": "missing",
                "validation_status": "missing",
                "entities": {},
                "invalid_entities": {},
                "missing_fields": ["periods (need ≥ 2)"],
                "ambiguous_entities": {},
                "suggestions": {},
                "needs_clarification": True,
                "notes": "Temporal comparison requires at least 2 periods",
                "duration_ms": int((time.time() - start) * 1000),
            }

        # Valid
        return {
            "status": "ok",
            "validation_status": "ok",
            "entities": entities,
            "invalid_entities": {},
            "missing_fields": [],
            "ambiguous_entities": {},
            "suggestions": {},
            "needs_clarification": False,
            "notes": "Temporal comparison validated",
            "duration_ms": int((time.time() - start) * 1000),
        }

    # =====================================================================
    # HELPERS
    # =====================================================================
    def _fuzzy_candidates(self, query: str, candidates: List[str], threshold=0.6):
        """Return possible fuzzy matches."""
        from difflib import SequenceMatcher
        q = query.lower()
        out = []
        for c in candidates:
            score = SequenceMatcher(None, q, c.lower()).ratio()
            if score >= threshold:
                out.append(c)
        return out[:5]

    def _get_missing_required(self, intent: str, ent: Dict[str, Any]):
        req = {
            "property_comparison": ["properties"],   # 2+ will be handled by QueryAgent
            "pl_calculation": ["properties"],        # year optional
            "property_details": ["properties"],
            "tenant_info": ["tenants", "properties"],  # Either tenants OR properties
            "multi_entity_query": ["sub_queries"]
        }
        missing = []
        need = req.get(intent, [])
        
        # Special case for tenant_info: need either tenants OR properties
        if intent == "tenant_info":
            has_tenants = ent.get("tenants") and len(ent.get("tenants", [])) > 0
            has_properties = ent.get("property") or (ent.get("properties") and len(ent.get("properties", [])) > 0)
            if not has_tenants and not has_properties:
                missing.append("tenants or properties")
        else:
            for f in need:
                if f not in ent or not ent[f]:
                    missing.append(f)
        return missing
