"""
NaturalDateAgent – Simplified, deterministic, no hallucinations.

Its ONLY mission:
- Normalize dates already extracted by the Extractor
- Optionally resolve simple relative dates (this year / last year)
- Produce clean periods: ["2024-Q1", "2024-M03", ...]

This agent NEVER tries to guess missing dates.
"""

import time
from typing import Dict, Any


class NaturalDateAgent:
    """Deterministic date normalizer for the real-estate assistant."""
    
    VALID_QUARTERS = {"Q1", "Q2", "Q3", "Q4"}
    
    MONTH_MAP = {
        "m01": "M01", "m02": "M02", "m03": "M03", "m04": "M04",
        "m05": "M05", "m06": "M06", "m07": "M07", "m08": "M08",
        "m09": "M09", "m10": "M10", "m11": "M11", "m12": "M12"
    }

    def __init__(self):
        pass

    # ----------------------------------------------------------------------
    # MAIN FUNCTION
    # ----------------------------------------------------------------------
    def process(self, entities: Dict[str, Any], user_query: str = "") -> Dict[str, Any]:
        start = time.time()

        # CLONE so we never mutate upstream entity dict
        normalized = entities.copy()
        notes = []
        ambiguous = []

        # --------------------------------------------------
        # 1. NORMALIZE YEAR
        # --------------------------------------------------
        year = normalized.get("year")

        # single year
        if isinstance(year, str) and year.isdigit():
            normalized["year"] = year

        # list of years
        if isinstance(year, list):
            normalized["year"] = [str(y) for y in year]

        # resolve relative "this year", "last year"
        if year in ["this year", "current year"]:
            normalized["year"] = "2024"
            notes.append("Normalized 'this year' → 2024")

        if year == "last year":
            normalized["year"] = "2023"   # simple deterministic rule
            notes.append("Normalized 'last year' → 2023")

        # --------------------------------------------------
        # 2. NORMALIZE QUARTER
        # --------------------------------------------------
        q = normalized.get("quarter")
        year_val = normalized.get("year", "2024")
        # Handle year as list for temporal_comparison
        if isinstance(year_val, list):
            year_val = year_val[0] if year_val else "2024"
        year_val = str(year_val)

        if isinstance(q, str):   # e.g. "Q1"
            if q.upper() in self.VALID_QUARTERS:
                normalized["quarter"] = f"{year_val}-{q.upper()}"
                notes.append(f"Normalized quarter {q} → {normalized['quarter']}")
            else:
                ambiguous.append(q)

        if isinstance(q, list):
            out = []
            for x in q:
                x_str = str(x).upper()
                # Remove year prefix if already present (e.g., "2024-Q1" → "Q1")
                if "-" in x_str:
                    x_str = x_str.split("-")[-1]
                if x_str in self.VALID_QUARTERS:
                    out.append(f"{year_val}-{x_str}")
                else:
                    ambiguous.append(x)
            normalized["quarter"] = out
            notes.append(f"Normalized quarter list → {out}")

        # --------------------------------------------------
        # 3. NORMALIZE MONTH
        # --------------------------------------------------
        m = normalized.get("month")
        year_val = normalized.get("year", "2024")
        if isinstance(year_val, list):
            year_val = year_val[0] if year_val else "2024"
        year_val = str(year_val)

        if isinstance(m, str):
            key = m.lower()
            if key in self.MONTH_MAP:
                normalized["month"] = f"{year_val}-{self.MONTH_MAP[key]}"
                notes.append(f"Normalized month {m} → {normalized['month']}")
            else:
                ambiguous.append(m)

        if isinstance(m, list):
            out = []
            for x in m:
                key = str(x).lower()
                if key in self.MONTH_MAP:
                    out.append(f"{year_val}-{self.MONTH_MAP[key]}")
                else:
                    ambiguous.append(x)
            normalized["month"] = out
            notes.append("Normalized month list")

        # --------------------------------------------------
        # 4. CONSTRUCT periods (for temporal_comparison)
        # --------------------------------------------------
        periods = []

        if "quarter" in normalized:
            if isinstance(normalized["quarter"], list):
                periods.extend(normalized["quarter"])
            else:
                periods.append(normalized["quarter"])

        if "month" in normalized:
            if isinstance(normalized["month"], list):
                periods.extend(normalized["month"])
            else:
                periods.append(normalized["month"])

        if isinstance(normalized.get("year"), list):
            periods.extend(normalized["year"])

        if periods:
            normalized["periods"] = periods

        # --------------------------------------------------
        # RESULT
        # --------------------------------------------------
        return {
            "status": "ok" if not ambiguous else "ambiguous",
            "entities": normalized,
            "ambiguous_dates": ambiguous,
            "needs_clarification": len(ambiguous) > 0,
            "notes": "; ".join(notes) if notes else "No normalization needed",
            "duration_ms": int((time.time() - start) * 1000)
        }
