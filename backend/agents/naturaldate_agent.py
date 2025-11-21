"""
NaturalDate Agent - Parses and Normalizes Date Entities
Wraps NaturalDateParser as a graph node
"""

import time
from typing import Dict, Any, List
from backend.utils.date_parser import NaturalDateParser


class NaturalDateAgent:
    """
    Intelligent date parsing agent
    
    Responsibilities:
    1. Parse natural language dates ("last month", "Q1 2024")
    2. Normalize to standard formats (YYYY-MM-DD, YYYY-QX, YYYY-MXX)
    3. Detect ambiguous dates and flag for clarification
    4. Handle relative dates ("last quarter", "this year")
    """
    
    def __init__(self):
        self.date_parser = NaturalDateParser()
    
    def process(self, entities: Dict[str, Any], user_query: str = "") -> Dict[str, Any]:
        """
        Parse and normalize date entities
        
        Args:
            entities: Extracted entities (may contain year, quarter, month)
            user_query: Original user query for context
        
        Returns:
        {
            "status": "ok" | "ambiguous" | "error",
            "entities": dict,  # normalized entities
            "date_metadata": dict,
            "ambiguous_dates": list,
            "needs_clarification": bool,
            "notes": str,
            "duration_ms": int
        }
        """
        start_time = time.time()
        
        normalized = entities.copy()
        date_metadata = {}
        ambiguous_dates = []
        needs_clarification = False
        reasoning_parts = []
        
        # If user_query provided, use NaturalDateParser to extract dates
        if user_query:
            parsed_dates = self.date_parser.parse(user_query)
            date_metadata["parsed_from_query"] = parsed_dates
            
            # Merge parsed dates with entities (entities take precedence)
            if parsed_dates.get("year") and not normalized.get("year"):
                normalized["year"] = parsed_dates["year"]
                reasoning_parts.append(f"Extracted year from query: {parsed_dates['year']}")
            
            if parsed_dates.get("quarter") and not normalized.get("quarter"):
                normalized["quarter"] = parsed_dates["quarter"]
                reasoning_parts.append(f"Extracted quarter from query: {parsed_dates['quarter']}")
            
            if parsed_dates.get("month") and not normalized.get("month"):
                normalized["month"] = parsed_dates["month"]
                reasoning_parts.append(f"Extracted month from query: {parsed_dates['month']}")
        
        # Normalize quarter format (Q1 → 2024-Q1)
        if "quarter" in normalized and normalized["quarter"]:
            quarter_val = normalized["quarter"]
            year_val = normalized.get("year", "2024")
            
            # Handle list (temporal comparison)
            if isinstance(quarter_val, list):
                normalized_quarters = []
                for q in quarter_val:
                    q_str = str(q).upper()
                    # Validate quarter
                    if q_str in ["Q1", "Q2", "Q3", "Q4"]:
                        # Add year prefix if not present
                        if "-" not in q_str:
                            q_normalized = f"{year_val}-{q_str}"
                        else:
                            q_normalized = q_str
                        normalized_quarters.append(q_normalized)
                        reasoning_parts.append(f"Normalized {q} → {q_normalized}")
                    else:
                        ambiguous_dates.append(f"quarter: {q}")
                
                normalized["quarter"] = normalized_quarters
            else:
                # Single quarter
                q_str = str(quarter_val).upper()
                if q_str in ["Q1", "Q2", "Q3", "Q4"]:
                    if "-" not in q_str:
                        normalized["quarter"] = f"{year_val}-{q_str}"
                        reasoning_parts.append(f"Normalized {quarter_val} → {normalized['quarter']}")
                else:
                    ambiguous_dates.append(f"quarter: {quarter_val}")
        
        # Normalize month format
        if "month" in normalized and normalized["month"]:
            month_val = normalized["month"]
            year_val = normalized.get("year", "2024")
            
            # Handle list
            if isinstance(month_val, list):
                normalized_months = []
                for m in month_val:
                    m_normalized = self._normalize_month(str(m), str(year_val))
                    if m_normalized:
                        normalized_months.append(m_normalized)
                        reasoning_parts.append(f"Normalized {m} → {m_normalized}")
                    else:
                        ambiguous_dates.append(f"month: {m}")
                
                normalized["month"] = normalized_months
            else:
                # Single month
                m_normalized = self._normalize_month(str(month_val), str(year_val))
                if m_normalized:
                    normalized["month"] = m_normalized
                    reasoning_parts.append(f"Normalized {month_val} → {m_normalized}")
                else:
                    ambiguous_dates.append(f"month: {month_val}")
        
        # Check for relative dates in query
        if user_query:
            relative_dates = self._detect_relative_dates(user_query)
            if relative_dates:
                date_metadata["relative_dates"] = relative_dates
                reasoning_parts.append(f"Detected relative dates: {relative_dates}")
        
        # Flag if clarification needed
        if ambiguous_dates:
            needs_clarification = True
            reasoning_parts.append(f"Ambiguous dates: {', '.join(ambiguous_dates)}")
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        reasoning = "; ".join(reasoning_parts) if reasoning_parts else "No date normalization needed"
        
        status = "ambiguous" if needs_clarification else "ok"
        
        return {
            "status": status,
            "entities": normalized,
            "date_metadata": date_metadata,
            "ambiguous_dates": ambiguous_dates,
            "needs_clarification": needs_clarification,
            "notes": reasoning,
            "duration_ms": duration_ms
        }
    
    def _normalize_month(self, month_str: str, year: str = "2024") -> str:
        """
        Normalize month to YYYY-MXX format
        
        Args:
            month_str: Month string (e.g., "December", "12", "M12")
            year: Year context
        
        Returns:
            Normalized month (e.g., "2024-M12") or empty string if invalid
        """
        month_str = str(month_str).lower().strip()
        
        # Already in YYYY-MXX format
        if "-M" in month_str.upper():
            return month_str.upper()
        
        # Already in MXX format
        if month_str.upper().startswith('M') and len(month_str) == 3:
            return f"{year}-{month_str.upper()}"
        
        # Numeric month (1-12)
        if month_str.isdigit():
            month_num = int(month_str)
            if 1 <= month_num <= 12:
                return f"{year}-M{month_num:02d}"
            return ""
        
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
        
        month_code = month_map.get(month_str)
        if month_code:
            return f"{year}-{month_code}"
        
        return ""
    
    def _detect_relative_dates(self, query: str) -> List[str]:
        """Detect relative date expressions"""
        relative_indicators = [
            "last month", "last quarter", "last year",
            "this month", "this quarter", "this year",
            "next month", "next quarter", "next year",
            "previous", "current", "latest"
        ]
        
        query_lower = query.lower()
        detected = []
        
        for indicator in relative_indicators:
            if indicator in query_lower:
                detected.append(indicator)
        
        return detected

