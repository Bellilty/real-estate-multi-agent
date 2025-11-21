"""
Data loader for Real Estate Asset Management System
Handles loading and querying the cortex.parquet dataset
"""

import polars as pl
from pathlib import Path
from typing import Dict, List, Optional, Any


def _safe_string_value(value: str) -> str:
    """
    Sanitize string value for safe querying
    
    Implements SQL injection protection by escaping special characters
    Note: Polars is generally safe from SQL injection since it's not SQL,
    but we apply similar principles for consistency
    """
    if not isinstance(value, str):
        return str(value)
    
    # Escape single quotes (SQL injection protection)
    return value.replace("'", "''")


def _case_insensitive_match(column: pl.Expr, value: str) -> pl.Expr:
    """
    Create case-insensitive match expression
    
    Equivalent to SQL: WHERE LOWER(column) = LOWER('value')
    """
    safe_value = _safe_string_value(value)
    return column.cast(pl.Utf8).str.to_lowercase() == safe_value.lower()


class RealEstateDataLoader:
    """Loads and provides query interface for real estate data"""
    
    def __init__(self, data_path: str = "data/cortex.parquet"):
        """Initialize the data loader
        
        Args:
            data_path: Path to the parquet file
        """
        self.data_path = Path(data_path)
        self.df: Optional[pl.DataFrame] = None
        self.load_data()
    
    def load_data(self) -> None:
        """Load the parquet file into memory"""
        if not self.data_path.exists():
            raise FileNotFoundError(f"Data file not found: {self.data_path}")
        
        self.df = pl.read_parquet(self.data_path)
        print(f"✅ Loaded {len(self.df)} records from {self.data_path}")
    
    def get_properties(self) -> List[str]:
        """Get list of all properties"""
        if self.df is None:
            return []
        
        properties = (self.df
            .select("property_name")
            .unique()
            .drop_nulls()
            .to_series()
            .to_list()
        )
        return properties
    
    def get_tenants(self) -> List[str]:
        """Get list of all tenants"""
        if self.df is None:
            return []
        
        tenants = (self.df
            .select("tenant_name")
            .unique()
            .drop_nulls()
            .to_series()
            .to_list()
        )
        return tenants
    
    def get_property_details(self, property_name: str) -> Dict[str, Any]:
        """Get details for a specific property
        
        Args:
            property_name: Name of the property (case-insensitive)
            
        Returns:
            Dictionary with property details
        """
        if self.df is None:
            return {}
        
        # Use case-insensitive matching
        property_data = self.df.filter(
            _case_insensitive_match(pl.col("property_name"), property_name)
        )
        
        if len(property_data) == 0:
            return {"error": f"Property '{property_name}' not found"}
        
        # Calculate aggregated stats
        total_revenue = property_data.filter(
            pl.col("ledger_type") == "revenue"
        )["profit"].sum()
        
        total_expenses = abs(property_data.filter(
            pl.col("ledger_type") == "expenses"
        )["profit"].sum())
        
        net_profit = total_revenue - total_expenses
        
        tenants = (property_data
            .select("tenant_name")
            .unique()
            .drop_nulls()
            .to_series()
            .to_list()
        )
        
        return {
            "property_name": property_name,
            "total_revenue": round(total_revenue, 2),
            "total_expenses": round(total_expenses, 2),
            "net_profit": round(net_profit, 2),
            "tenants": tenants,
            "record_count": len(property_data)
        }
    
    def calculate_pl(self, 
                    year: Optional[str] = None,
                    quarter: Optional[str] = None,
                    month: Optional[str] = None,
                    property_name: Optional[str] = None) -> Dict[str, Any]:
        """Calculate Profit & Loss for given timeframe and/or property
        
        Args:
            year: Filter by year (e.g., "2024")
            quarter: Filter by quarter (e.g., "2024-Q1")
            month: Filter by month (e.g., "2024-M01")
            property_name: Filter by property name
            
        Returns:
            Dictionary with P&L details
        """
        if self.df is None:
            return {}
        
        filtered_df = self.df
        
        # Apply filters
        if year:
            filtered_df = filtered_df.filter(pl.col("year") == year)
        if quarter:
            filtered_df = filtered_df.filter(pl.col("quarter") == quarter)
        if month:
            filtered_df = filtered_df.filter(pl.col("month") == month)
        if property_name:
            # Use case-insensitive matching for property names
            filtered_df = filtered_df.filter(
                _case_insensitive_match(pl.col("property_name"), property_name)
            )
        
        if len(filtered_df) == 0:
            return {"error": "No data found for the specified filters"}
        
        # Calculate P&L
        revenue_df = filtered_df.filter(pl.col("ledger_type") == "revenue")
        expenses_df = filtered_df.filter(pl.col("ledger_type") == "expenses")
        
        total_revenue = revenue_df["profit"].sum()
        total_expenses = abs(expenses_df["profit"].sum())
        net_profit = total_revenue - total_expenses
        
        # Breakdown by category
        revenue_by_category = (revenue_df
            .group_by("ledger_category")
            .agg(pl.col("profit").sum().alias("amount"))
            .sort("amount", descending=True)
            .head(5)
        )
        
        expenses_by_category = (expenses_df
            .group_by("ledger_category")
            .agg(pl.col("profit").abs().sum().alias("amount"))
            .sort("amount", descending=True)
            .head(5)
        )
        
        return {
            "total_revenue": round(total_revenue, 2),
            "total_expenses": round(total_expenses, 2),
            "net_profit": round(net_profit, 2),
            "revenue_breakdown": revenue_by_category.to_dicts(),
            "expenses_breakdown": expenses_by_category.to_dicts(),
            "filters": {
                "year": year,
                "quarter": quarter,
                "month": month,
                "property": property_name
            }
        }
    
    def compare_properties(self, property1: str, property2: str) -> Dict[str, Any]:
        """Compare two properties
        
        Args:
            property1: First property name
            property2: Second property name
            
        Returns:
            Dictionary with comparison data
        """
        details1 = self.get_property_details(property1)
        details2 = self.get_property_details(property2)
        
        if "error" in details1 or "error" in details2:
            return {
                "error": f"One or both properties not found: {property1}, {property2}"
            }
        
        return {
            "property1": details1,
            "property2": details2,
            "comparison": {
                "revenue_diff": round(details1["total_revenue"] - details2["total_revenue"], 2),
                "profit_diff": round(details1["net_profit"] - details2["net_profit"], 2),
                "better_performer": property1 if details1["net_profit"] > details2["net_profit"] else property2
            }
        }
    
    def get_dataset_stats(self) -> Dict[str, Any]:
        """Get dataset statistics for UI display"""
        if self.df is None:
            return {}
        
        # Get unique months (periods)
        periods = (self.df
            .select("month")
            .unique()
            .sort("month")
            .drop_nulls()
            .to_series()
            .to_list()
        )
        
        return {
            "total_records": len(self.df),
            "properties": self.get_properties(),
            "tenants": self.get_tenants(),
            "years": self.df["year"].unique().sort().to_list(),
            "period_range": [periods[0], periods[-1]] if periods else ["", ""]
        }
    
    def get_data_summary(self) -> Dict[str, Any]:
        """Get overall data summary"""
        if self.df is None:
            return {}
        
        return {
            "total_records": len(self.df),
            "properties_count": self.df["property_name"].n_unique(),
            "tenants_count": self.df["tenant_name"].n_unique(),
            "date_range": {
                "years": self.df["year"].unique().sort().to_list(),
                "earliest_month": self.df["month"].min(),
                "latest_month": self.df["month"].max()
            },
            "total_revenue": round(self.df.filter(pl.col("ledger_type") == "revenue")["profit"].sum(), 2),
            "total_expenses": round(abs(self.df.filter(pl.col("ledger_type") == "expenses")["profit"].sum()), 2)
        }
    
    def validate_entities(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate all entities against the dataset
        
        Returns a dict with:
        - valid: bool (True if all entities are valid)
        - invalid_entities: dict of {entity_type: [invalid_values]}
        - suggestions: dict of {entity_type: [available_values]}
        """
        if self.df is None:
            return {"valid": False, "error": "Dataset not loaded"}
        
        invalid_entities = {}
        suggestions = {}
        
        # Validate property_name (support both "property" and "properties")
        property_to_check = None
        if "property" in entities and entities["property"]:
            property_to_check = entities["property"]
        elif "properties" in entities and entities["properties"]:
            # Handle list of properties
            if isinstance(entities["properties"], list):
                property_to_check = entities["properties"]
            else:
                property_to_check = [entities["properties"]]
        
        if property_to_check:
            available_properties = self.get_properties()
            invalid_props = []
            
            # Check if it's a list or single property
            props_list = property_to_check if isinstance(property_to_check, list) else [property_to_check]
            
            for prop in props_list:
                # Skip "all", "PropCo" (portfolio-level aliases)
                if prop and prop.lower() not in ["all", "propco"] and prop not in available_properties:
                    invalid_props.append(prop)
            
            if invalid_props:
                invalid_entities["property"] = invalid_props
                suggestions["property"] = available_properties
        
        # Validate tenant_name (support both "tenant" and "tenants")
        tenant_to_check = None
        if "tenant" in entities and entities["tenant"]:
            tenant_to_check = entities["tenant"]
        elif "tenants" in entities and entities["tenants"]:
            # Handle list of tenants
            if isinstance(entities["tenants"], list):
                tenant_to_check = entities["tenants"]
            else:
                tenant_to_check = [entities["tenants"]]
        
        if tenant_to_check:
            available_tenants = self.get_tenants()
            invalid_tenants = []
            
            # Check if it's a list or single tenant
            tenants_list = tenant_to_check if isinstance(tenant_to_check, list) else [tenant_to_check]
            
            for tenant in tenants_list:
                if tenant and tenant not in available_tenants:
                    invalid_tenants.append(tenant)
            
            if invalid_tenants:
                invalid_entities["tenant"] = invalid_tenants
                suggestions["tenant"] = available_tenants
        
        # Validate year
        if "year" in entities and entities["year"]:
            available_years = self.df["year"].unique().drop_nulls().to_list()
            if entities["year"] not in available_years:
                invalid_entities["year"] = [entities["year"]]
                suggestions["year"] = available_years
        
        # Validate quarter
        if "quarter" in entities and entities["quarter"]:
            quarter = entities["quarter"]
            year = entities.get("year")
            
            # If quarter is just "Q1" but we have year, build full quarter
            if quarter and year and quarter.upper() in ["Q1", "Q2", "Q3", "Q4"]:
                quarter = f"{year}-{quarter.upper()}"
            
            available_quarters = self.df["quarter"].unique().drop_nulls().to_list()
            if quarter not in available_quarters:
                invalid_entities["quarter"] = [quarter]
                suggestions["quarter"] = sorted(available_quarters)
        
        # Validate month
        if "month" in entities and entities["month"]:
            available_months = self.df["month"].unique().drop_nulls().to_list()
            if entities["month"] not in available_months:
                invalid_entities["month"] = [entities["month"]]
                suggestions["month"] = sorted(available_months)
        
        # Validate ledger_type
        if "ledger_type" in entities and entities["ledger_type"]:
            available_types = self.df["ledger_type"].unique().drop_nulls().to_list()
            if entities["ledger_type"] not in available_types:
                invalid_entities["ledger_type"] = [entities["ledger_type"]]
                suggestions["ledger_type"] = available_types
        
        # Validate ledger_group
        if "ledger_group" in entities and entities["ledger_group"]:
            available_groups = self.df["ledger_group"].unique().drop_nulls().to_list()
            if entities["ledger_group"] not in available_groups:
                invalid_entities["ledger_group"] = [entities["ledger_group"]]
                suggestions["ledger_group"] = available_groups
        
        # Validate ledger_category
        if "ledger_category" in entities and entities["ledger_category"]:
            available_categories = self.df["ledger_category"].unique().drop_nulls().to_list()
            if entities["ledger_category"] not in available_categories:
                invalid_entities["ledger_category"] = [entities["ledger_category"]]
                suggestions["ledger_category"] = available_categories
        
        return {
            "valid": len(invalid_entities) == 0,
            "invalid_entities": invalid_entities,
            "suggestions": suggestions
        }


if __name__ == "__main__":
    # Test the data loader
    loader = RealEstateDataLoader()
    print("\n📊 Data Summary:")
    print(loader.get_data_summary())
    
    print("\n🏢 Properties:")
    print(loader.get_properties())
    
    print("\n📈 P&L for 2024:")
    print(loader.calculate_pl(year="2024"))

