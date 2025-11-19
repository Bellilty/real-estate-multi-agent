"""
Query Agent - Executes data queries based on extracted entities
"""

from typing import Dict, Any
from src.data_loader import RealEstateDataLoader


class QueryAgent:
    """Executes queries against the real estate dataset"""
    
    def __init__(self, data_loader: RealEstateDataLoader):
        """Initialize the query agent
        
        Args:
            data_loader: Data loader instance
        """
        self.data_loader = data_loader
    
    def execute_query(self, intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the appropriate query based on intent and entities
        
        Args:
            intent: The classified intent
            entities: Extracted entities
            
        Returns:
            Query results
        """
        try:
            if intent == "property_comparison":
                return self._query_comparison(entities)
            elif intent == "pl_calculation":
                return self._query_pl(entities)
            elif intent == "property_details":
                return self._query_property_details(entities)
            elif intent == "tenant_info":
                return self._query_tenant_info(entities)
            elif intent == "general_query":
                return self._query_general_info()
            else:
                return {"error": "Unsupported query intent"}
                
        except Exception as e:
            return {"error": f"Query execution failed: {str(e)}"}
    
    def _query_comparison(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Execute property comparison query"""
        properties = entities.get("properties", [])
        
        if len(properties) < 2:
            return {
                "error": "Need at least 2 properties for comparison",
                "available_properties": self.data_loader.get_properties()
            }
        
        prop1, prop2 = properties[0], properties[1]
        
        result = self.data_loader.compare_properties(prop1, prop2)
        return result
    
    def _query_pl(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Execute P&L calculation query"""
        year = entities.get("year")
        quarter = entities.get("quarter")
        month = entities.get("month")
        property_name = entities.get("property")
        
        result = self.data_loader.calculate_pl(
            year=year,
            quarter=quarter,
            month=month,
            property_name=property_name
        )
        
        return result
    
    def _query_property_details(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Execute property details query"""
        property_name = entities.get("property")
        
        if not property_name:
            return {
                "error": "No property specified",
                "available_properties": self.data_loader.get_properties()
            }
        
        result = self.data_loader.get_property_details(property_name)
        return result
    
    def _query_tenant_info(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tenant information query"""
        tenant = entities.get("tenant")
        
        if not tenant:
            return {
                "info": "Available tenants",
                "tenants": self.data_loader.get_tenants()
            }
        
        # Filter data for specific tenant
        tenant_data = self.data_loader.df.filter(
            self.data_loader.df["tenant_name"] == tenant
        )
        
        if len(tenant_data) == 0:
            return {
                "error": f"No data found for tenant: {tenant}",
                "available_tenants": self.data_loader.get_tenants()
            }
        
        # Calculate tenant stats
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

