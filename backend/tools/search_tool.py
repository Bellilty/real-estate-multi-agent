"""
Search Tool for Cross-Column Entity Discovery
Inspired by reference implementation's validation-first approach
"""

from typing import Dict, Any, List
import polars as pl


class SearchTool:
    """Search for entities across all dataset columns"""
    
    def __init__(self, df: pl.DataFrame):
        self.df = df
        
        # Define searchable columns (excluding numeric columns)
        self.searchable_columns = [
            'entity_name',
            'property_name',
            'tenant_name',
            'ledger_type',
            'ledger_group',
            'ledger_category',
            'ledger_description',
            'month',
            'quarter',
            'year'
        ]
    
    def search_term_in_dataset(self, term: str) -> Dict[str, Any]:
        """
        Search for a term across ALL columns in the dataset
        
        Use this when you get no results to find where the term might exist
        Returns where the term was found or confirms it's truly absent
        
        Args:
            term: Search term (e.g., "parking", "Building 180", "expenses")
            
        Returns:
            Dictionary with search results:
            - found: bool
            - results: List of {column, count, examples}
            - marker: "[NO_MATCHES_FOUND]" if nothing found
        """
        results = []
        
        # Escape term for safety (though Polars handles this)
        term_lower = term.lower().strip()
        
        for column in self.searchable_columns:
            try:
                # Skip if column doesn't exist
                if column not in self.df.columns:
                    continue
                
                # Search case-insensitively
                matches = self.df.filter(
                    pl.col(column).is_not_null() &
                    pl.col(column).cast(pl.Utf8).str.to_lowercase().str.contains(term_lower)
                )
                
                count = len(matches)
                
                if count > 0:
                    # Get up to 3 examples
                    examples = matches[column].unique().head(3).to_list()
                    
                    results.append({
                        "column": column,
                        "count": count,
                        "examples": examples
                    })
                    
                    # Special note for case differences
                    if column in ['property_name', 'tenant_name']:
                        exact_match = self.df.filter(
                            pl.col(column) == term
                        )
                        if len(exact_match) == 0 and len(matches) > 0:
                            actual_case = examples[0]
                            results[-1]["note"] = f"Found as '{actual_case}' (not '{term}')"
                            
            except Exception as e:
                # Skip columns that cause errors
                continue
        
        # Check for partial matches if no exact matches
        if not results and ' ' in term:
            words = term.split()
            for word in words:
                if len(word) > 2:  # Skip very short words
                    partial_results = self.search_term_in_dataset(word)
                    if partial_results["found"]:
                        return {
                            "found": True,
                            "partial": True,
                            "original_term": term,
                            "found_word": word,
                            "results": partial_results["results"]
                        }
        
        if results:
            return {
                "found": True,
                "term": term,
                "results": results,
                "total_columns": len(results)
            }
        else:
            return {
                "found": False,
                "term": term,
                "marker": "[NO_MATCHES_FOUND]",
                "message": f"Term '{term}' not found in any column of the dataset"
            }
    
    def validate_entity(
        self,
        entity_type: str,
        entity_value: str
    ) -> Dict[str, Any]:
        """
        Validate if a specific entity exists in the dataset
        
        This is the "Validation-First" approach from the reference implementation
        
        Args:
            entity_type: Type of entity (property, tenant, year, quarter, etc.)
            entity_value: Value to validate
            
        Returns:
            Dictionary with validation result:
            - valid: bool
            - exists: bool
            - suggestions: List of available values if not found
        """
        column_map = {
            "property": "property_name",
            "tenant": "tenant_name",
            "year": "year",
            "quarter": "quarter",
            "month": "month",
            "ledger_type": "ledger_type",
            "ledger_group": "ledger_group",
            "ledger_category": "ledger_category"
        }
        
        if entity_type not in column_map:
            return {"valid": False, "error": f"Unknown entity type: {entity_type}"}
        
        column = column_map[entity_type]
        
        if column not in self.df.columns:
            return {"valid": False, "error": f"Column {column} not found in dataset"}
        
        try:
            # Case-insensitive search
            matches = self.df.filter(
                pl.col(column).is_not_null() &
                (pl.col(column).cast(pl.Utf8).str.to_lowercase() == entity_value.lower())
            )
            
            exists = len(matches) > 0
            
            if exists:
                # Get the actual case-correct value
                actual_value = matches[column].unique()[0]
                return {
                    "valid": True,
                    "exists": True,
                    "actual_value": actual_value
                }
            else:
                # Get suggestions (available values)
                available = self.df.filter(
                    pl.col(column).is_not_null()
                )[column].unique().sort().to_list()
                
                return {
                    "valid": False,
                    "exists": False,
                    "entity_type": entity_type,
                    "entity_value": entity_value,
                    "suggestions": available[:10]  # Limit to 10 suggestions
                }
                
        except Exception as e:
            return {
                "valid": False,
                "error": f"Validation error: {str(e)}"
            }
    
    def get_available_values(self, entity_type: str) -> List[str]:
        """Get all available values for an entity type"""
        column_map = {
            "property": "property_name",
            "tenant": "tenant_name",
            "year": "year",
            "quarter": "quarter",
            "month": "month"
        }
        
        if entity_type not in column_map:
            return []
        
        column = column_map[entity_type]
        
        if column not in self.df.columns:
            return []
        
        try:
            return self.df.filter(
                pl.col(column).is_not_null()
            )[column].unique().sort().to_list()
        except:
            return []

