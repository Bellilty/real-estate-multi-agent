"""
Natural Date Parser for Real Estate Queries
Converts natural language dates to structured time periods
"""

from datetime import datetime
from typing import Dict, List, Optional
import re


class NaturalDateParser:
    """Parse natural language dates into structured time periods"""
    
    # Current date for relative calculations
    CURRENT_YEAR = "2025"
    CURRENT_QUARTER = "2025-Q1"
    CURRENT_MONTH = "2025-M03"
    
    # Seasons mapping (for Northern Hemisphere real estate context)
    SEASONS = {
        "winter": ["M12", "M01", "M02"],  # Dec, Jan, Feb
        "spring": ["M03", "M04", "M05"],  # Mar, Apr, May
        "summer": ["M06", "M07", "M08"],  # Jun, Jul, Aug
        "fall": ["M09", "M10", "M11"],    # Sep, Oct, Nov
        "autumn": ["M09", "M10", "M11"],
    }
    
    # Quarter mappings
    QUARTERS = {
        "q1": "Q1",
        "q2": "Q2",
        "q3": "Q3",
        "q4": "Q4",
        "first quarter": "Q1",
        "second quarter": "Q2",
        "third quarter": "Q3",
        "fourth quarter": "Q4",
    }
    
    # Month name mappings
    MONTHS = {
        "january": "M01", "jan": "M01",
        "february": "M02", "feb": "M02",
        "march": "M03", "mar": "M03",
        "april": "M04", "apr": "M04",
        "may": "M05",
        "june": "M06", "jun": "M06",
        "july": "M07", "jul": "M07",
        "august": "M08", "aug": "M08",
        "september": "M09", "sep": "M09", "sept": "M09",
        "october": "M10", "oct": "M10",
        "november": "M11", "nov": "M11",
        "december": "M12", "dec": "M12",
    }
    
    @classmethod
    def parse(cls, query: str) -> Dict[str, Optional[str]]:
        """
        Parse natural language date references from query
        
        Returns:
            Dict with 'year', 'quarter', 'month', and 'clarification_needed'
        """
        query_lower = query.lower()
        result = {
            "year": None,
            "quarter": None,
            "month": None,
            "clarification_needed": None
        }
        
        # Explicit years (2024, 2025)
        year_match = re.search(r'\b(2024|2025)\b', query)
        if year_match:
            result["year"] = year_match.group(1)
        
        # "this year", "current year"
        if re.search(r'\b(this year|current year)\b', query_lower):
            result["year"] = cls.CURRENT_YEAR
        
        # "last year"
        if re.search(r'\b(last year|previous year)\b', query_lower):
            result["year"] = "2024"
        
        # Quarters
        for quarter_str, quarter_code in cls.QUARTERS.items():
            if quarter_str in query_lower:
                if result["year"]:
                    # Year explicitly mentioned - use it
                    year = result["year"]
                    result["quarter"] = f"{year}-{quarter_code}"
                else:
                    # Year NOT mentioned - need clarification
                    result["clarification_needed"] = f"Which year did you mean for {quarter_code}? (2024 or 2025)"
                    # Default to most recent year with data (2024)
                    year = "2024"
                    result["year"] = year
                    result["quarter"] = f"{year}-{quarter_code}"
                break
        
        # "last quarter"
        if re.search(r'\blast quarter\b', query_lower):
            # Q1 2025 -> last quarter would be Q4 2024
            result["quarter"] = "2024-Q4"
            result["year"] = "2024"
        
        # Month names
        for month_str, month_code in cls.MONTHS.items():
            if month_str in query_lower:
                if result["year"]:
                    # Year explicitly mentioned - use it
                    year = result["year"]
                    result["month"] = f"{year}-{month_code}"
                else:
                    # Year NOT mentioned - need clarification
                    result["clarification_needed"] = f"Which year did you mean for {month_str.title()}? (2024 or 2025)"
                    # Default to most recent year with data (2024)
                    year = "2024"
                    result["year"] = year
                    result["month"] = f"{year}-{month_code}"
                break
        
        # Seasons
        for season, months in cls.SEASONS.items():
            if season in query_lower:
                # Determine which year's season
                year = result["year"]
                
                # "last winter" special case
                if "last" in query_lower and season == "winter":
                    # Last winter = Dec 2023, Jan-Feb 2024 (but we only have 2024-2025 data)
                    # So we interpret as "winter 2024" = Dec 2024, Jan-Feb 2025
                    result["clarification_needed"] = f"Did you mean winter 2024 (Dec 2024 to Feb 2025)?"
                    result["quarter"] = "2024-Q4"  # Approximate
                    result["year"] = "2024"
                elif year:
                    result["clarification_needed"] = f"Season '{season}' detected. This includes months: {', '.join(months)}. I'll use Q1 as approximation."
                    result["quarter"] = f"{year}-Q1"
                else:
                    result["clarification_needed"] = f"Season '{season}' detected, but which year? Please specify 2024 or 2025."
                break
        
        return result
    
    @classmethod
    def get_period_description(cls, year: Optional[str], quarter: Optional[str], month: Optional[str]) -> str:
        """Generate human-readable description of the period"""
        if month:
            return f"Month: {month}"
        elif quarter:
            return f"Quarter: {quarter}"
        elif year:
            return f"Year: {year}"
        else:
            return "All time"

