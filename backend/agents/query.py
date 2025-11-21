"""
Enhanced Query Agent with performance tracking
Executes queries against the real estate dataset
"""

import time
import sys
import os
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.data_loader import RealEstateDataLoader


class EnhancedQueryAgent:
    """Executes queries with timing and error handling"""
    
    def __init__(self, data_loader: RealEstateDataLoader):
        self.data_loader = data_loader
    
    def execute_query(
        self,
        intent: str,
        entities: Dict[str, Any]
    ) -> tuple[Dict[str, Any], float]:
        """
        Execute query based on intent and entities
        
        Returns:
            (query_result, duration_ms)
        """
        start_time = time.time()
        print("\n[QUERY] ---- Query agent called ----")        
        try:
            # STEP 1: Validate all entities against the dataset
            # SKIP validation for temporal_comparison (it has different entity structure)
            if intent != "temporal_comparison":
                validation = self.data_loader.validate_entities(entities)
                
                if not validation["valid"]:
                    # Build a comprehensive error message
                    invalid = validation["invalid_entities"]
                    suggestions = validation["suggestions"]
                    
                    error_parts = []
                    for entity_type, invalid_values in invalid.items():
                        error_parts.append(f"{entity_type}: {', '.join(map(str, invalid_values))}")
                    
                    result = {
                        "error": f"Invalid entities found: {'; '.join(error_parts)}",
                        "invalid_entities": invalid,
                        "suggestions": suggestions
                    }
                    
                    # Add legacy keys for backward compatibility
                    if "property" in invalid:
                        result["invalid_properties"] = invalid["property"]
                        result["available_properties"] = suggestions.get("property", [])
                    if "tenant" in invalid:
                        result["invalid_tenants"] = invalid["tenant"]
                        result["available_tenants"] = suggestions.get("tenant", [])
                    
                    duration_ms = (time.time() - start_time) * 1000
                    return result, duration_ms
            
            # STEP 2: Execute the query
            if intent == "property_comparison":
                result = self._query_comparison(entities)
            elif intent == "temporal_comparison":
                result = self._query_temporal_comparison(entities)
            elif intent == "multi_entity_query":
                result = self._query_multi_entity(entities)
            elif intent == "pl_calculation":
                result = self._query_pl(entities)
            elif intent == "property_details":
                result = self._query_property_details(entities)
            elif intent == "tenant_info":
                result = self._query_tenant_info(entities)
            elif intent == "general_query":
                result = self._query_general_info()
            else:
                result = {"error": "Unsupported query intent"}
            
            duration_ms = (time.time() - start_time) * 1000
            
            return result, duration_ms
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result = {"error": f"Query execution failed: {str(e)}"}
            return result, duration_ms
    
    def _query_comparison(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Execute property comparison"""
        properties = entities.get("properties", [])
        invalid_properties = entities.get("invalid_properties", [])
        requested_properties = entities.get("requested_properties", properties)
        
        if len(properties) < 2:
            # Not enough valid properties to perform a comparison
            # If there are invalid ones, surface them explicitly
            if invalid_properties:
                return {
                    "error": "Need at least 2 valid properties for comparison",
                    "invalid_properties": invalid_properties,
                    "available_properties": self.data_loader.get_properties(),
                    "requested_properties": requested_properties,
                    "provided": properties,
                }
            return {
                "error": "Need at least 2 properties for comparison",
                "available_properties": self.data_loader.get_properties(),
                "provided": properties
            }
        
        # Handle N properties (2 or more)
        # Get details for each property
        property_details = []
        for prop in properties:
            details = self.data_loader.get_property_details(prop)
            if "error" in details:
                return {
                    "error": f"Property '{prop}' not found in dataset",
                    "available_properties": self.data_loader.get_properties()
                }
            property_details.append(details)
        
        # Build comparison result
        result = {
            "type": "multi_property_comparison",
            "properties": properties,
            "count": len(properties)
        }
        
        # Add each property's data
        for i, (prop, details) in enumerate(zip(properties, property_details), start=1):
            result[f"property{i}"] = {
                "property_name": prop,
                "total_revenue": details.get("total_revenue", 0),
                "total_expenses": details.get("total_expenses", 0),
                "net_profit": details.get("net_profit", 0),
                "tenants": details.get("tenants", []),
                "record_count": details.get("record_count", 0)
            }
        
        # Add comparison summary (best performer, rankings)
        profits = [(prop, details.get("net_profit", 0)) for prop, details in zip(properties, property_details)]
        profits_sorted = sorted(profits, key=lambda x: x[1], reverse=True)
        
        result["ranking"] = [{"property": prop, "net_profit": profit} for prop, profit in profits_sorted]
        result["best_performer"] = profits_sorted[0][0]
        result["worst_performer"] = profits_sorted[-1][0]
        
        return result
    
    def _query_multi_entity(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute multiple queries and combine results
        entities = { "sub_queries": [query1_entities, query2_entities, ...] }
        """
        if "sub_queries" not in entities:
            raise ValueError("sub_queries not found in entities")
        
        sub_queries = entities["sub_queries"]
        results = []
        
        for i, sub_query in enumerate(sub_queries):
            query_entities = sub_query["entities"]
            raw_query = sub_query["raw_query"]
            
            # Determine query type and execute
            if query_entities.get("property") == "all":
                # PropCo query - calculate P&L for all properties
                result = self._query_pl(query_entities)
            elif "year" in query_entities or "quarter" in query_entities or "month" in query_entities:
                # P&L query
                result = self._query_pl(query_entities)
            else:
                # Property details query
                result = self._query_property_details(query_entities)
            
            results.append({
                "query_index": i + 1,
                "raw_query": raw_query,
                "entities": query_entities,
                "result": result
            })
        
        return {
            "type": "multi_entity",
            "total_queries": len(results),
            "results": results
        }
    
    def _query_temporal_comparison(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Execute temporal comparison (same property, different periods)"""
        # Handle both singular and plural keys
        property_name = entities.get("property")
        if not property_name and "properties" in entities:
            props_list = entities.get("properties")
            if isinstance(props_list, list) and len(props_list) > 0:
                property_name = props_list[0]  # Take first property
            elif isinstance(props_list, str):
                property_name = props_list
        
        periods = entities.get("periods", [])
        years = entities.get("years", [])
        is_portfolio = entities.get("is_portfolio", False) or property_name is None or property_name.lower() in ["all", "propco"]
        
        if len(periods) < 2:
            return {
                "error": "Need at least 2 time periods for comparison",
                "hint": "Please specify two years, quarters, or months (e.g., '2024 vs 2025')"
            }
        
        # Validate property if we are NOT at portfolio level
        if not is_portfolio and property_name:
            available = self.data_loader.get_properties()
            if property_name not in available:
                return {
                    "error": f"Property '{property_name}' not found in dataset",
                    "available_properties": available
                }
        
        # Calculate P&L for each period (NO LIMIT - handle N periods)
        period_results = {}
        for period in periods:
            # Determine if it's year, quarter, or month
            if len(period) == 4:  # Year (e.g., "2024")
                pl_data = self.data_loader.calculate_pl(
                    year=period,
                    property_name=None if is_portfolio else property_name
                )
            elif "-Q" in period:  # Quarter
                pl_data = self.data_loader.calculate_pl(
                    quarter=period,
                    property_name=None if is_portfolio else property_name
                )
            elif "-M" in period:  # Month
                pl_data = self.data_loader.calculate_pl(
                    month=period,
                    property_name=None if is_portfolio else property_name
                )
            else:
                continue
            
            if "error" not in pl_data:
                period_results[period] = pl_data
        
        if len(period_results) < 2:
            return {
                "error": "Could not retrieve data for at least 2 periods",
                "periods_requested": periods,
                "periods_found": list(period_results.keys())
            }
        
        # Format comparison result for N periods
        result = {
            "type": "temporal_comparison",
            "property": property_name,
            "periods": list(period_results.keys()),
            "count": len(period_results)
        }
        
        # Add each period's data
        for i, (period, data) in enumerate(period_results.items(), start=1):
            result[f"period{i}"] = period
            result[f"period{i}_data"] = {
                "total_revenue": data.get("total_revenue", 0),
                "total_expenses": data.get("total_expenses", 0),
                "net_profit": data.get("net_profit", 0)
            }
        
        # Add ranking by net profit
        profits = [(period, data.get("net_profit", 0)) for period, data in period_results.items()]
        profits_sorted = sorted(profits, key=lambda x: x[1], reverse=True)
        
        result["ranking"] = [{"period": period, "net_profit": profit} for period, profit in profits_sorted]
        result["best_period"] = profits_sorted[0][0]
        result["worst_period"] = profits_sorted[-1][0]
        
        return result
    
    def _query_pl(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Execute P&L calculation"""
        year = entities.get("year")
        quarter = entities.get("quarter")
        month = entities.get("month")
        
        # Normalize quarter: if just "Q1" and we have year, make it "2024-Q1"
        if quarter and year and quarter.upper() in ["Q1", "Q2", "Q3", "Q4"]:
            quarter = f"{year}-{quarter.upper()}"
        
        # Support both "property" and "properties" (from extractor)
        property_name = entities.get("property")
        if not property_name and "properties" in entities:
            props_list = entities.get("properties")
            if isinstance(props_list, list) and len(props_list) > 0:
                property_name = props_list[0]  # Take first property
            elif isinstance(props_list, str):
                property_name = props_list
        
        metric = entities.get("metric", "pnl")
        ledger_type = entities.get("ledger_type")
        ledger_group = entities.get("ledger_group")
        invalid_properties = entities.get("invalid_properties", [])
        
        # Check for invalid properties first
        if invalid_properties:
            return {
                "error": f"Property not found: {', '.join(invalid_properties)}",
                "invalid_properties": invalid_properties,
                "available_properties": self.data_loader.get_properties()
            }
        
        # Handle "all" properties (PropCo is portfolio-level)
        if property_name and property_name.lower() in ["all", "propco"]:
            property_name = None  # None means all properties
        
        # Detect conflicting time ranges (e.g., quarter vs month that don't match)
        if quarter and month:
            # month is in format YYYY-MMM, e.g. 2025-M02
            try:
                month_code = month.split("-")[1]  # M01, M02, ...
                month_num = int(month_code.replace("M", ""))
                if 1 <= month_num <= 3:
                    inferred_quarter = "Q1"
                elif 4 <= month_num <= 6:
                    inferred_quarter = "Q2"
                elif 7 <= month_num <= 9:
                    inferred_quarter = "Q3"
                else:
                    inferred_quarter = "Q4"
                inferred_quarter_full = f"{year}-{inferred_quarter}" if year else None
                if inferred_quarter_full and inferred_quarter_full != quarter:
                    return {
                        "error": "Conflicting time ranges: quarter and month do not match. "
                                 "Please specify a single period, for example '2024-Q3' or '2025-M02'."
                    }
            except Exception:
                # If parsing fails, fall back to normal behaviour
                pass
        
        # Validate property if specified
        if property_name:
            available = self.data_loader.get_properties()
            if property_name not in available:
                return {
                    "error": f"Property '{property_name}' not found in dataset",
                    "available_properties": available
                }
        
        # Delegate base P&L calculation to the data loader
        base_result = self.data_loader.calculate_pl(
            year=year,
            quarter=quarter,
            month=month,
            property_name=property_name
        )

        # If there was an error or we don't need metric-level filtering, return as-is
        if "error" in base_result:
            return base_result

        # By default, calculate_pl already returns aggregated revenue, expenses and net_profit.
        # We adjust this based on the inferred "metric"/ledger filters to align with
        # the user's requested type of information.
        result: Dict[str, Any] = {
            **base_result,
            "metric": metric,
        }

        # If the user asked specifically for expenses only
        if metric == "expenses":
            # Keep total_expenses and zero out revenue/net profit to make intent explicit
            result["total_revenue"] = 0.0
            result["net_profit"] = -base_result.get("total_expenses", 0.0)
            return result

        # If the user asked for revenue-only style metrics (revenue, rent income, parking income)
        if metric in ["revenue", "rent_income", "parking_income"]:
            # We recompute revenue from the detailed breakdown based on ledger filters,
            # and do not focus on expenses in the numeric summary.
            revenue_breakdown = base_result.get("revenue_breakdown", [])
            filtered_revenue = 0.0

            for row in revenue_breakdown:
                category = str(row.get("ledger_category", "")).lower()
                group = str(row.get("ledger_group", "")).lower() if "ledger_group" in row else ""
                amount = float(row.get("amount", 0.0))

                if metric == "rent_income":
                    # Focus on rental income categories (main rent flows)
                    if "rental_income" in group or "revenue_rent_taxed" in category or "rent" in category:
                        filtered_revenue += amount
                elif metric == "parking_income":
                    # Focus on parking-related revenue.
                    # Here we interpret "parking income" as the main taxed parking proceeds.
                    if "proceeds_parking_taxed" in category:
                        filtered_revenue += amount
                else:
                    # Generic revenue metric: sum all revenue categories
                    filtered_revenue += amount

            # If we couldn't filter specifically (e.g. missing breakdown info), fall back to total_revenue
            if filtered_revenue == 0.0:
                filtered_revenue = base_result.get("total_revenue", 0.0)

            result["total_revenue"] = round(filtered_revenue, 2)
            # For revenue-type questions, set net_profit equal to revenue when expenses aren't the focus
            result["net_profit"] = result["total_revenue"]
            return result

        # Default: full P&L metric (pnl or unknown)
        return result
    
    def _query_property_details(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Execute property details query"""
        # Support both "property" and "properties" (from extractor)
        property_name = entities.get("property")
        if not property_name and "properties" in entities:
            props_list = entities.get("properties")
            if isinstance(props_list, list) and len(props_list) > 0:
                property_name = props_list[0]  # Take first property
            elif isinstance(props_list, str):
                property_name = props_list
        
        invalid_properties = entities.get("invalid_properties", [])
        
        if not property_name:
            # Check if there was an invalid property request
            if invalid_properties:
                return {
                    "error": f"Property not found: {', '.join(invalid_properties)}",
                    "invalid_properties": invalid_properties,
                    "available_properties": self.data_loader.get_properties()
                }
            return {
                "error": "No property specified",
                "available_properties": self.data_loader.get_properties()
            }
        
        # Validate property
        available = self.data_loader.get_properties()
        if property_name not in available:
            return {
                "error": f"Property '{property_name}' not found in dataset",
                "available_properties": available
            }
        
        result = self.data_loader.get_property_details(property_name)
        return result
    
    def _query_tenant_info(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tenant information query"""
        # Support both "tenant" and "tenants" (from extractor)
        tenant = entities.get("tenant")
        if not tenant and "tenants" in entities:
            tenants_list = entities.get("tenants")
            if isinstance(tenants_list, list) and len(tenants_list) > 0:
                tenant = tenants_list[0]  # Take first tenant
            elif isinstance(tenants_list, str):
                tenant = tenants_list
        
        invalid_tenants = entities.get("invalid_tenants", [])
        
        if not tenant:
            # Check if there was an invalid tenant request
            if invalid_tenants:
                return {
                    "error": f"Tenant not found: {', '.join(invalid_tenants)}",
                    "invalid_tenants": invalid_tenants,
                    "available_tenants": self.data_loader.get_tenants()
                }
            return {
                "info": "Available tenants",
                "tenants": self.data_loader.get_tenants()
            }
        
        # Filter for tenant
        tenant_data = self.data_loader.df.filter(
            self.data_loader.df["tenant_name"] == tenant
        )
        
        if len(tenant_data) == 0:
            return {
                "error": f"No data found for {tenant}",
                "available_tenants": self.data_loader.get_tenants()
            }
        
        # Calculate stats
        total_revenue = tenant_data.filter(
            tenant_data["ledger_type"] == "revenue"
        )["profit"].sum()
        
        properties = tenant_data["property_name"].unique().drop_nulls().to_list()
        
        return {
            "tenant": tenant,
            "properties": properties,
            "total_revenue": round(total_revenue, 2),
            "record_count": len(tenant_data)
        }
    
    def _query_general_info(self) -> Dict[str, Any]:
        """Return general dataset information"""
        return self.data_loader.get_data_summary()

