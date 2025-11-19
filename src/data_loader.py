"""
Data loader for Real Estate Asset Management System
Handles loading and querying the cortex.parquet dataset
"""

import polars as pl
from pathlib import Path
from typing import Dict, List, Optional, Any


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
            property_name: Name of the property
            
        Returns:
            Dictionary with property details
        """
        if self.df is None:
            return {}
        
        property_data = self.df.filter(
            pl.col("property_name") == property_name
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
            filtered_df = filtered_df.filter(pl.col("property_name") == property_name)
        
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


if __name__ == "__main__":
    # Test the data loader
    loader = RealEstateDataLoader()
    print("\n📊 Data Summary:")
    print(loader.get_data_summary())
    
    print("\n🏢 Properties:")
    print(loader.get_properties())
    
    print("\n📈 P&L for 2024:")
    print(loader.calculate_pl(year="2024"))

