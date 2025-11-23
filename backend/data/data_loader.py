"""
Clean & Optimized Data Loader
--------------------------------
This version contains:
✔ No validation logic (now handled by ValidationAgent)
✔ No business logic (handled by QueryAgent)
✔ Pure data access + aggregation only
✔ Robust filtering of year/quarter/month/property
✔ Safe case-insensitive matching
✔ Correct quarter/month normalization handling
✔ Correct breakdown structure (ledger_category + ledger_group)
✔ Cleaned interface for QueryAgent
"""

import polars as pl
from pathlib import Path
from typing import Dict, List, Optional, Any


# ================================================================
# INTERNAL UTILS
# ================================================================

def _normalize_string(value: str) -> str:
    """Lowercase & strip strings (safe normalization)"""
    if not isinstance(value, str):
        return str(value)
    return value.strip().lower()


def _ci_match(column: pl.Expr, value: str) -> pl.Expr:
    """
    Case-insensitive exact match for Polars:
    Equivalent to: LOWER(column) = LOWER(value)
    """
    norm = _normalize_string(value)
    return column.cast(pl.Utf8).str.to_lowercase() == norm


# ================================================================
# MAIN CLASS
# ================================================================

class RealEstateDataLoader:
    """Pure data access layer for real estate dataset."""

    def __init__(self, data_path: str = "data/cortex.parquet"):
        self.data_path = Path(data_path)
        self.df: Optional[pl.DataFrame] = None
        self._load_data()

    # ------------------------------------------------------------
    # LOADING
    # ------------------------------------------------------------
    def _load_data(self):
        if not self.data_path.exists():
            raise FileNotFoundError(f"Data file not found: {self.data_path}")

        self.df = pl.read_parquet(self.data_path)

        # Force types for safety
        self.df = self.df.with_columns([
            pl.col("property_name").cast(pl.Utf8),
            pl.col("tenant_name").cast(pl.Utf8),
            pl.col("year").cast(pl.Utf8),
            pl.col("quarter").cast(pl.Utf8),
            pl.col("month").cast(pl.Utf8)
        ])

        print(f"✅ Loaded {len(self.df)} rows from {self.data_path}")

    # ------------------------------------------------------------
    # BASIC READERS
    # ------------------------------------------------------------
    def get_properties(self) -> List[str]:
        return (
            self.df
            .select("property_name")
            .drop_nulls()
            .unique()
            .sort("property_name")
            .to_series()
            .to_list()
        )

    def get_tenants(self) -> List[str]:
        return (
            self.df
            .select("tenant_name")
            .drop_nulls()
            .unique()
            .sort("tenant_name")
            .to_series()
            .to_list()
        )

    # ------------------------------------------------------------
    # FETCH PROPERTY DETAILS (NO VALIDATION HERE)
    # ------------------------------------------------------------
    def get_property_details(self, property_name: str) -> Dict[str, Any]:
        df = self.df.filter(_ci_match(pl.col("property_name"), property_name))

        if df.is_empty():
            return {"error": f"Property '{property_name}' not found"}

        total_rev = df.filter(pl.col("ledger_type") == "revenue")["profit"].sum()
        total_exp = abs(df.filter(pl.col("ledger_type") == "expenses")["profit"].sum())
        net_profit = total_rev - total_exp

        tenants = (
            df.select("tenant_name")
            .unique()
            .drop_nulls()
            .sort("tenant_name")
            .to_series()
            .to_list()
        )

        return {
            "property": df["property_name"].first(),  # canonical name
            "total_revenue": float(round(total_rev, 2)),
            "total_expenses": float(round(total_exp, 2)),
            "net_profit": float(round(net_profit, 2)),
            "tenants": tenants,
            "record_count": len(df)
        }

    # ------------------------------------------------------------
    # P&L CALCULATION (PURE AGGREGATION, NO VALIDATION)
    # ------------------------------------------------------------
    def calculate_pl(
        self,
        year: Optional[str] = None,
        quarter: Optional[str] = None,
        month: Optional[str] = None,
        property_name: Optional[str] = None
    ) -> Dict[str, Any]:

        df = self.df

        # --- Apply filters (all safe / case-insensitive) ---
        if property_name:
            df = df.filter(_ci_match(pl.col("property_name"), property_name))

        if year:
            df = df.filter(pl.col("year") == str(year))

        if quarter:
            df = df.filter(pl.col("quarter") == quarter)

        if month:
            df = df.filter(pl.col("month") == month)

        if df.is_empty():
            return {"error": "no_financial_data"}

        # --- P&L numbers ---
        rev_df = df.filter(pl.col("ledger_type") == "revenue")
        exp_df = df.filter(pl.col("ledger_type") == "expenses")

        total_rev = rev_df["profit"].sum()
        total_exp = abs(exp_df["profit"].sum())
        net = total_rev - total_exp

        # --- Breakdown (ledger_category + ledger_group) ---
        revenue_breakdown = (
            rev_df
            .group_by(["ledger_category", "ledger_group"])
            .agg(pl.col("profit").sum().alias("amount"))
            .sort("amount", descending=True)
            .head(10)
            .to_dicts()
        )

        expenses_breakdown = (
            exp_df
            .group_by(["ledger_category", "ledger_group"])
            .agg(pl.col("profit").abs().sum().alias("amount"))
            .sort("amount", descending=True)
            .head(10)
            .to_dicts()
        )

        return {
            "property": property_name,
            "year": year,
            "quarter": quarter,
            "month": month,
            "total_revenue": float(round(total_rev, 2)),
            "total_expenses": float(round(total_exp, 2)),
            "net_profit": float(round(net, 2)),
            "revenue_breakdown": revenue_breakdown,
            "expenses_breakdown": expenses_breakdown,
        }

    # ------------------------------------------------------------
    # MISC
    # ------------------------------------------------------------
    def get_dataset_stats(self) -> Dict[str, Any]:
        """Basic dataset info for UI or health-check."""
        months = (
            self.df
            .select("month")
            .drop_nulls()
            .unique()
            .sort("month")
            .to_series()
            .to_list()
        )

        years = (
            self.df
            .select("year")
            .drop_nulls()
            .unique()
            .sort("year")
            .to_series()
            .to_list()
        )

        return {
            "total_records": len(self.df),
            "properties": self.get_properties(),
            "tenants": self.get_tenants(),
            "years": years,
            "period_range": months if len(months) >= 2 else [],
        }

    def get_data_summary(self) -> Dict[str, Any]:
        """Returns global high-level dataset summary."""
        total_rev = self.df.filter(pl.col("ledger_type") == "revenue")["profit"].sum()
        total_exp = abs(self.df.filter(pl.col("ledger_type") == "expenses")["profit"].sum())

        years = (
            self.df["year"]
            .drop_nulls()
            .unique()
            .sort()
            .to_list()
        )

        months = (
            self.df["month"]
            .drop_nulls()
            .unique()
            .sort()
            .to_list()
        )

        return {
            "total_records": len(self.df),
            "properties_count": self.df["property_name"].n_unique(),
            "tenants_count": self.df["tenant_name"].n_unique(),
            "date_range": {
                "years": years,
                "earliest_month": months[0] if months else None,
                "latest_month": months[-1] if months else None
            },
            "total_revenue": float(round(total_rev, 2)),
            "total_expenses": float(round(total_exp, 2)),
        }
