"""
QueryAgent – Clean and fully patched execution layer
• No validation (handled earlier)
• No intent classification
• Executes the 6 query types in a safe, consistent format
• Compatible with Formatter, ValidationAgent & NaturalDateAgent
"""

import time
import polars as pl
from typing import Dict, Any, List


class QueryAgent:
    """Executes dataset queries based on validated entities."""

    def __init__(self, data_loader):
        self.data_loader = data_loader

    # ============================================================
    # MAIN ENTRY
    # ============================================================
    def run(self, intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        start = time.time()

        try:
            if intent == "property_comparison":
                result = self._property_comparison(entities)

            elif intent == "temporal_comparison":
                result = self._temporal_comparison(entities)

            elif intent == "multi_entity_query":
                result = self._multi_entity(entities)

            elif intent == "pl_calculation":
                result = self._pnl(entities)

            elif intent == "property_details":
                result = self._property_details(entities)

            elif intent == "tenant_info":
                result = self._tenant_info(entities)

            elif intent == "analytics_query":
                result = self._analytics_query(entities)

            else:
                result = {"error": f"Unsupported intent '{intent}'"}

        except Exception as e:
            result = {"error": f"QueryAgent failure: {str(e)}"}

        result["duration_ms"] = int((time.time() - start) * 1000)
        return result

    # ============================================================
    # PROPERTY COMPARISON
    # ============================================================
    def _property_comparison(self, ent: Dict[str, Any]) -> Dict[str, Any]:
        props = ent.get("properties", [])

        if len(props) < 2:
            return {
                "error": "Property comparison requires at least 2 properties",
                "properties": props,
                "available_properties": self.data_loader.get_properties()
            }

        details = []
        for p in props:
            d = self.data_loader.get_property_details(p)
            details.append({
                "property": p,
                "net_profit": d.get("net_profit", 0),
                "total_revenue": d.get("total_revenue", 0),
                "total_expenses": d.get("total_expenses", 0),
                "tenants": d.get("tenants", [])
            })

        ranking = sorted(details, key=lambda x: x["net_profit"], reverse=True)

        return {
            "type": "property_comparison",
            "properties": props,
            "ranking": ranking,
            "best_performer": ranking[0]["property"],
            "worst_performer": ranking[-1]["property"],
        }

    # ============================================================
    # TEMPORAL COMPARISON (PATCHED & CLEAN)
    # ============================================================
    def _temporal_comparison(self, ent: Dict[str, Any]) -> Dict[str, Any]:
        # Property from "property" OR "properties"
        prop = ent.get("property")
        if not prop and ent.get("properties"):
            prop = ent["properties"][0]

        periods = ent.get("periods", [])

        if not prop:
            return {"error": "Missing property for temporal comparison"}

        if len(periods) < 2:
            return {"error": "Temporal comparison needs ≥ 2 periods"}

        results = {}

        for period in periods:
            if len(period) == 4:  # YEAR
                d = self.data_loader.calculate_pl(year=period, property_name=prop)

            elif "-Q" in period:  # QUARTER
                d = self.data_loader.calculate_pl(quarter=period, property_name=prop)

            elif "-M" in period:  # MONTH
                d = self.data_loader.calculate_pl(month=period, property_name=prop)

            else:
                continue

            if "error" not in d:
                results[period] = d

        if len(results) < 2:
            return {
                "error": "missing_period_data",
                "periods_requested": periods,
                "periods_found": list(results.keys())
            }

        # -------- PATCHED FORMAT (Formatter compatible) -------- #
        ranking_list = sorted(
            [{"period": p, "net_profit": d.get("net_profit", 0)} for p, d in results.items()],
            key=lambda x: x["net_profit"],
            reverse=True
        )

        return {
            "type": "temporal_comparison",
            "property": prop,
            "periods": list(results.keys()),
            "ranking": ranking_list,
            "best_period": ranking_list[0]["period"],
            "worst_period": ranking_list[-1]["period"],
            "details": results
        }

    # ============================================================
    # MULTI QUERY (PATCHED – supports ALL query types)
    # ============================================================
    def _multi_entity(self, ent: Dict[str, Any]) -> Dict[str, Any]:
        subs = ent.get("sub_queries", []) or []
        if not subs:
            return {"error": "No sub-queries provided"}

        output = []
        for i, sq in enumerate(subs):
            if not sq or not isinstance(sq, dict):
                continue
            e = sq["entities"]
            raw = sq["raw_query"]

            # ROUTING LOGIC (patched)
            if "properties" in e and len(e["properties"]) >= 2:
                r = self._property_comparison(e)

            elif "year" in e or "quarter" in e or "month" in e:
                r = self._pnl(e)

            elif "property" in e or "properties" in e:
                r = self._property_details(e)

            elif "tenant" in e or "tenants" in e:
                r = self._tenant_info(e)

            else:
                r = {"error": "Unsupported sub-query"}

            output.append({
                "index": i + 1,
                "raw_query": raw,
                "entities": e,
                "result": r
            })

        return {
            "type": "multi_entity",
            "total_queries": len(output),
            "results": output
        }

    # ============================================================
    # P&L CALCULATION (PATCHED)
    # ============================================================
    def _pnl(self, ent: Dict[str, Any]) -> Dict[str, Any]:
        # Property: support property / properties / portfolio-level
        prop = ent.get("property")
        if not prop and ent.get("properties"):
            # Handle None or empty list
            props = ent.get("properties")
            if props and isinstance(props, list) and len(props) > 0:
                prop = props[0]

        if prop and prop.lower() in ["propco", "all"]:
            prop = None  # portfolio-level

        metric = ent.get("metric", "pnl")
        year = ent.get("year")
        quarter = ent.get("quarter")
        month = ent.get("month")

        # Normalize quarter: handle both string and list
        if quarter:
            # If quarter is a list, take the first one (for pl_calculation, we only need one quarter)
            if isinstance(quarter, list):
                quarter = quarter[0] if quarter else None
            
            # Normalize quarter Q1 → 2024-Q1 (only if not already formatted)
            if quarter and year:
                if isinstance(quarter, str):
                    # Check if already formatted (e.g., "2024-Q1")
                    if "-" not in quarter and quarter.upper() in ["Q1", "Q2", "Q3", "Q4"]:
                        quarter = f"{year}-{quarter.upper()}"
                    elif "-" in quarter:
                        # Already formatted, use as is
                        pass

        # Safety check: if no property and no filters, return error
        if not prop and not year and not quarter and not month:
            return {"error": "no_financial_data", "message": "No property or timeframe specified"}

        df = self.data_loader.df
        df = df.filter(df["property_name"] == prop) if prop else df
        df = df.filter(df["year"] == str(year)) if year else df
        df = df.filter(df["quarter"] == quarter) if quarter else df
        df = df.filter(df["month"] == month) if month else df

        if df.is_empty():
            return {"error": "no_financial_data"}

        base = self.data_loader.calculate_pl(
            year=year,
            quarter=quarter,
            month=month,
            property_name=prop
        )

        if "error" in base:
            return base

        # --- Metric filtering (Expenses / Revenue / Rent / Parking) ---
        if metric == "expenses":
            return {
                "metric": "expenses",
                "total_expenses": base["total_expenses"],
                "net_profit": -base["total_expenses"],
                "property": prop,
                "year": year,
                "quarter": quarter,
                "month": month
            }

        if metric in ["revenue", "rent_income", "parking_income"]:
            rev = 0
            revenue_breakdown = base.get("revenue_breakdown", []) or []
            for row in revenue_breakdown:
                if not isinstance(row, dict):
                    continue
                cat = row.get("ledger_category", "").lower()
                group = row.get("ledger_group", "").lower()
                amt = row.get("amount", 0)

                if metric == "rent_income" and ("rental" in group or "rent" in cat):
                    rev += amt

                elif metric == "parking_income" and "parking" in cat:
                    rev += amt

                elif metric == "revenue":
                    rev += amt

            if rev == 0:
                rev = base.get("total_revenue", 0)

            return {
                "metric": metric,
                "total_revenue": rev,
                "net_profit": rev,
                "property": prop,
                "year": year,
                "quarter": quarter,
                "month": month
            }

        # Default P&L
        base["property"] = prop
        base["year"] = year
        base["quarter"] = quarter
        base["month"] = month
        return base

    # ============================================================
    # PROPERTY DETAILS
    # ============================================================
    def _property_details(self, ent: Dict[str, Any]) -> Dict[str, Any]:
        prop = ent.get("property")
        if not prop and ent.get("properties"):
            prop = ent["properties"][0]

        if not prop:
            return {"error": "No property specified"}

        info = self.data_loader.get_property_details(prop)

        years = sorted(self.data_loader.df.filter(
            self.data_loader.df["property_name"] == prop
        )["year"].unique().to_list())

        info["available_years"] = years
        return info

    # ============================================================
    # TENANT DETAILS
    # ============================================================
    def _tenant_info(self, ent: Dict[str, Any]) -> Dict[str, Any]:
        # Special case: "Show me the tenants for Building X" - query by property
        property_name = ent.get("property") or (ent.get("properties", [None])[0] if ent.get("properties") else None)
        
        if property_name:
            # Get tenants for a property
            info = self.data_loader.get_property_details(property_name)
            if "error" in info:
                return info
            return {
                "property": property_name,
                "tenants": info.get("tenants", []),
                "total_revenue": info.get("total_revenue", 0),
                "total_expenses": info.get("total_expenses", 0),
                "net_profit": info.get("net_profit", 0)
            }
        
        # Original logic: query by tenant
        tenant = ent.get("tenant")
        if not tenant and ent.get("tenants"):
            tenant = ent["tenants"][0]

        if not tenant:
            return {"error": "No tenant or property specified"}

        df = self.data_loader.df.filter(
            self.data_loader.df["tenant_name"] == tenant
        )

        if df.is_empty():
            return {"error": f"No data for tenant '{tenant}'"}

        revenue = df.filter(df["ledger_type"] == "revenue")["profit"].sum()
        props = df["property_name"].unique().to_list()

        return {
            "tenant": tenant,
            "properties": props,
            "total_revenue": float(revenue),
            "record_count": len(df)
        }

    # ============================================================
    # ANALYTICS QUERY
    # ============================================================
    def _analytics_query(self, ent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle analytics queries: list, max, min, top, etc."""
        operation = ent.get("operation", "list")
        user_query = ent.get("raw_query", "").lower() if isinstance(ent.get("raw_query"), str) else ""
        
        try:
            # For max/min/top queries - IMPLEMENT RANKING
            if operation in ["max", "min", "top", "highest", "lowest", "most"]:
                # Check if query is about categories FIRST (more specific - "expense category")
                if "categor" in user_query or ("expense" in user_query and ("category" in user_query or "lowest" in user_query or "highest" in user_query)):
                    return self._rank_expense_categories(ent, operation)
                # Check if query is about properties (which property made the most profit/highest revenue)
                elif "propert" in user_query or "building" in user_query:
                    return self._rank_properties_by_profit(ent, operation)
                # Generic error for unsupported ranking
                return {
                    "error": f"Ranking queries ({operation}) for this entity type are not yet fully supported.",
                    "operation": operation
                }
            
            # Determine what to list/analyze based on query content (only for "list" operation)
            # List all properties
            if "propert" in user_query or ("building" in user_query and "tenant" not in user_query):
                props = self.data_loader.get_properties()
                return {
                    "type": "list",
                    "items": props if props else [],
                    "count": len(props) if props else 0,
                    "operation": operation
                }
            
            # List all tenants
            if "tenant" in user_query:
                tenants = self.data_loader.get_tenants()
                return {
                    "type": "list",
                    "items": tenants if tenants else [],
                    "count": len(tenants) if tenants else 0,
                    "operation": operation
                }
            
            # Default: return available properties
            props = self.data_loader.get_properties()
            return {
                "type": "list",
                "items": props if props else [],
                "count": len(props) if props else 0,
                "operation": operation,
                "note": "Defaulting to properties list"
            }
        except Exception as e:
            return {
                "error": f"Error in analytics query: {str(e)}",
                "operation": operation
            }

    # ============================================================
    # RANKING HELPERS
    # ============================================================
    def _rank_properties_by_profit(self, ent: Dict[str, Any], operation: str) -> Dict[str, Any]:
        """Rank properties by profit or revenue (max/min/highest/lowest)."""
        year = ent.get("year")
        quarter = ent.get("quarter")
        month = ent.get("month")
        user_query = ent.get("raw_query", "").lower() if isinstance(ent.get("raw_query"), str) else ""
        
        # Determine sort metric: revenue or profit
        sort_by_revenue = "revenue" in user_query and "profit" not in user_query
        
        # Normalize year if it's a list
        if isinstance(year, list):
            year = year[0] if year else None
        elif year:
            year = str(year)
        
        # Normalize quarter format
        if quarter and year:
            if isinstance(quarter, list):
                quarter = quarter[0] if quarter else None
            if isinstance(quarter, str):
                if "-" not in quarter and quarter.upper() in ["Q1", "Q2", "Q3", "Q4"]:
                    quarter = f"{year}-{quarter.upper()}"
        
        # Get all properties
        all_properties = self.data_loader.get_properties()
        
        if not all_properties:
            return {
                "error": "No properties found in dataset",
                "operation": operation
            }
        
        # Calculate P&L for each property
        rankings = []
        for prop in all_properties:
            pl_result = self.data_loader.calculate_pl(
                year=year,
                quarter=quarter,
                month=month,
                property_name=prop
            )
            
            if "error" not in pl_result:
                rankings.append({
                    "property": prop,
                    "net_profit": pl_result.get("net_profit", 0),
                    "total_revenue": pl_result.get("total_revenue", 0),
                    "total_expenses": pl_result.get("total_expenses", 0)
                })
        
        if not rankings:
            return {
                "error": "no_financial_data",
                "message": f"No financial data found for the specified period",
                "operation": operation
            }
        
        # Sort by revenue or profit (descending for max/highest/most, ascending for min/lowest)
        reverse = operation in ["max", "highest", "most", "top"]
        sort_key = "total_revenue" if sort_by_revenue else "net_profit"
        rankings.sort(key=lambda x: x[sort_key], reverse=reverse)
        
        # Return top result for max/min, or top N for "top"
        if operation == "top":
            # Default to top 3, or extract number from query if possible
            top_n = 3
            return {
                "type": "ranking",
                "operation": operation,
                "rankings": rankings[:top_n],
                "count": len(rankings[:top_n]),
                "total_properties": len(rankings)
            }
        else:
            # Return the top/bottom property
            top_result = rankings[0]
            return {
                "type": "ranking",
                "operation": operation,
                "property": top_result["property"],
                "net_profit": top_result["net_profit"],
                "total_revenue": top_result["total_revenue"],
                "total_expenses": top_result["total_expenses"],
                "rankings": rankings[:5] if len(rankings) > 1 else [top_result]  # Include top 5 for context
            }

    def _rank_expense_categories(self, ent: Dict[str, Any], operation: str) -> Dict[str, Any]:
        """Rank expense categories by amount (highest/lowest)."""
        year = ent.get("year")
        quarter = ent.get("quarter")
        month = ent.get("month")
        property_name = ent.get("property") or (ent.get("properties", [None])[0] if ent.get("properties") else None)
        
        # Handle PropCo/portfolio-level (treat as None)
        if property_name and property_name.lower() in ["propco", "portfolio", "all properties", "all buildings"]:
            property_name = None
        
        # Normalize year if it's a list
        if isinstance(year, list):
            year = year[0] if year else None
        elif year:
            year = str(year)
        
        # Normalize quarter format
        if quarter and year:
            if isinstance(quarter, list):
                quarter = quarter[0] if quarter else None
            if isinstance(quarter, str):
                if "-" not in quarter and quarter.upper() in ["Q1", "Q2", "Q3", "Q4"]:
                    quarter = f"{year}-{quarter.upper()}"
        
        # Filter data
        df = self.data_loader.df
        if property_name:
            df = df.filter(pl.col("property_name") == property_name)
        if year:
            df = df.filter(pl.col("year") == str(year))
        if quarter:
            df = df.filter(pl.col("quarter") == quarter)
        if month:
            df = df.filter(pl.col("month") == month)
        
        # Filter expenses only
        exp_df = df.filter(pl.col("ledger_type") == "expenses")
        
        if exp_df.is_empty():
            return {
                "error": "no_financial_data",
                "message": "No expense data found for the specified period",
                "operation": operation
            }
        
        # Group by category and sum
        category_totals = (
            exp_df
            .group_by("ledger_category")
            .agg(pl.col("profit").abs().sum().alias("total_amount"))
            .sort("total_amount", descending=(operation in ["max", "highest", "most"]))
            .to_dicts()
        )
        
        if not category_totals:
            return {
                "error": "no_financial_data",
                "operation": operation
            }
        
        top_category = category_totals[0]
        return {
            "type": "ranking",
            "operation": operation,
            "category": top_category["ledger_category"],
            "total_amount": float(top_category["total_amount"]),
            "top_categories": category_totals[:5]  # Include top 5 for context
        }
