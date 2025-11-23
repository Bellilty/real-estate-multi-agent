"""
Disambiguation Agent – resolves ambiguous entities reported by ValidationAgent
NE REDETECTS NOTHING.
It ONLY resolves what ValidationAgent flagged as ambiguous.
"""

import time
from typing import Dict, Any, List


class DisambiguationAgent:
    """
    Resolves ambiguous entities based on suggestions from ValidationAgent.

    ValidationAgent provides:
        ambiguous_entities = {
            "properties": [
                {"input": "Building 18", "candidates": ["Building 18", "Building 180"]}
            ],
            "tenants": [
                {"input": "Tenant A", "candidates": ["Tenant A1", "Tenant AB"]}
            ]
        }
    """

    def __init__(self, data_loader):
        self.data_loader = data_loader

    # =====================================================================
    def process(self, entities: Dict[str, Any], ambiguous_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Disambiguate entities using ambiguous_info from ValidationAgent.

        Returns:
        {
            "status": "ok" | "ambiguous",
            "entities": dict,
            "needs_clarification": bool,
            "clarification_message": str,
            "suggestions": dict,
            "notes": str,
            "duration_ms": int
        }
        """
        start = time.time()

        clarified = entities.copy()
        suggestions = {}
        needs_clarification = False
        clarification_lines = []
        reasoning_parts = []

        ambiguous_properties = ambiguous_info.get("properties", [])
        ambiguous_tenants = ambiguous_info.get("tenants", [])

        # ============================================================
        # PROPERTIES
        # ============================================================
        if ambiguous_properties:
            new_props = []
            for ap in ambiguous_properties:
                input_name = ap["input"]
                candidates = ap["candidates"]

                if len(candidates) == 1:
                    # Auto-resolve
                    resolved = candidates[0]
                    new_props.append(resolved)
                    reasoning_parts.append(f"Auto-resolved '{input_name}' → '{resolved}'")
                else:
                    # Need user clarification
                    needs_clarification = True
                    suggestions.setdefault("properties", []).append({
                        "input": input_name,
                        "candidates": candidates
                    })
                    clarification_lines.append(
                        f"Which property did you mean for '{input_name}'? Options: {', '.join(candidates)}"
                    )

            clarified["properties"] = new_props if new_props else clarified.get("properties", [])

        # ============================================================
        # TENANTS
        # ============================================================
        if ambiguous_tenants:
            new_tenants = []
            for at in ambiguous_tenants:
                input_name = at["input"]
                candidates = at["candidates"]

                if len(candidates) == 1:
                    resolved = candidates[0]
                    new_tenants.append(resolved)
                    reasoning_parts.append(f"Auto-resolved '{input_name}' → '{resolved}'")
                else:
                    needs_clarification = True
                    suggestions.setdefault("tenants", []).append({
                        "input": input_name,
                        "candidates": candidates
                    })
                    clarification_lines.append(
                        f"Which tenant did you mean for '{input_name}'? Options: {', '.join(candidates)}"
                    )

            clarified["tenants"] = new_tenants if new_tenants else clarified.get("tenants", [])

        # ============================================================
        # OUTPUT
        # ============================================================
        duration_ms = int((time.time() - start) * 1000)

        return {
            "status": "ambiguous" if needs_clarification else "ok",
            "entities": clarified,
            "needs_clarification": needs_clarification,
            "clarification_message": "\n".join(clarification_lines),
            "suggestions": suggestions,
            "notes": "; ".join(reasoning_parts) if reasoning_parts else "No disambiguation performed",
            "duration_ms": duration_ms
        }
