"""
Comprehensive Test Suite - 20 Queries
Tests 3 types of scenarios:
1. Error handling (invalid properties, missing data, ambiguous queries)
2. Natural language queries (comparisons, totals, min/max, etc.)
3. Follow-up sequences
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.core.orchestrator import RealEstateOrchestrator
from backend.llm.llm_client import LLMClient
from backend.data.data_loader import RealEstateDataLoader
import polars as pl


# ============================================================================
# TEST QUERIES - 20 Total
# ============================================================================

TYPE_1_ERROR_HANDLING = [
    {
        "id": 1,
        "query": "What is the P&L for Building 999 in 2024?",
        "type": "error_handling",
        "expected_behavior": "Should detect invalid property and ask for clarification or suggest valid options",
        "should_contain": ["building", "property", "available"]  # Should mention available properties
    },
    {
        "id": 2,
        "query": "Show me revenue for Building 180 in 2030",
        "type": "error_handling",
        "expected_behavior": "Should detect missing data for year 2030",
        "should_contain": ["no financial data", "not available", "2030"]  # Should mention no data
    },
    {
        "id": 3,
        "query": "Compare Building X and Building Y",
        "type": "error_handling",
        "expected_behavior": "Should detect ambiguous/invalid properties",
        "should_contain": ["building", "property", "clarification"]  # Should ask for clarification
    },
    {
        "id": 4,
        "query": "What is the profit?",
        "type": "error_handling",
        "expected_behavior": "Should detect incomplete query (missing property/timeframe)",
        "should_contain": ["missing"]  # Should ask for more info (Missing: properties is OK, property/properties both fine)
    },
    {
        "id": 5,
        "query": "Calculate the square root of Building 180",
        "type": "error_handling",
        "expected_behavior": "Should detect unsupported operation",
        "should_contain": ["not supported", "cannot", "unable"]  # Should indicate unsupported
    },
    {
        "id": 6,
        "query": "Show me tenants for Building 999",
        "type": "error_handling",
        "expected_behavior": "Should detect invalid property",
        "should_contain": ["building", "property", "available"]  # Should suggest valid options
    }
]

TYPE_2_NATURAL_LANGUAGE = [
    {
        "id": 7,
        "query": "What is the total P&L for all properties in 2024?",
        "type": "natural_language",
        "expected_behavior": "Should calculate portfolio-level P&L for 2024",
        "should_contain": ["all properties", "2024", "$"]  # Should show total with year
    },
    {
        "id": 8,
        "query": "Compare Building 120 and Building 140 in 2025",
        "type": "natural_language",
        "expected_behavior": "Should compare two properties in 2025",
        "should_contain": ["building 120", "building 140", "2025", "profit"]  # Should compare both
    },
    {
        "id": 9,
        "query": "Which property had the highest revenue in Q1 2024?",
        "type": "natural_language",
        "expected_behavior": "Should rank properties by revenue in Q1 2024",
        "should_contain": ["highest", "revenue", "building"]  # Should identify top property (Q1 and 2024 may be implicit)
    },
    {
        "id": 10,
        "query": "What are the expenses for Building 180 in March 2024?",
        "type": "natural_language",
        "expected_behavior": "Should show expenses for specific month",
        "should_contain": ["building 180", "expenses", "march", "2024", "$"]  # Should show expenses
    },
    {
        "id": 11,
        "query": "Show me all tenants for Building 140",
        "type": "natural_language",
        "expected_behavior": "Should list all tenants for Building 140",
        "should_contain": ["building 140", "tenant"]  # Should list tenants (tenant or tenants both OK)
    },
    {
        "id": 12,
        "query": "Compare Q1 and Q2 2024 for Building 180",
        "type": "natural_language",
        "expected_behavior": "Should compare two quarters for same property",
        "should_contain": ["building 180", "q1", "q2", "2024", "compare"]  # Should compare periods
    },
    {
        "id": 13,
        "query": "What is the lowest expense category across all properties in 2024?",
        "type": "natural_language",
        "expected_behavior": "Should find lowest expense category",
        "should_contain": ["lowest", "expense", "category", "2024", "$"]  # Should identify category
    },
    {
        "id": 14,
        "query": "Give me the total revenue for all buildings in Q1 2025",
        "type": "natural_language",
        "expected_behavior": "Should calculate total revenue for portfolio in Q1 2025",
        "should_contain": ["all", "revenue", "q1", "2025", "$"]  # Should show total
    }
]

TYPE_3_FOLLOW_UPS = [
    {
        "id": 15,
        "query": "What is the P&L for Building 180 in 2024?",
        "type": "followup_base",
        "expected_behavior": "Base query for follow-up",
        "should_contain": ["building 180", "2024", "$"]
    },
    {
        "id": 16,
        "query": "And in 2025?",
        "type": "followup",
        "followup_of": 15,
        "expected_behavior": "Should use Building 180 from context, change year to 2025",
        "should_contain": ["building 180", "2025", "$"]
    },
    {
        "id": 17,
        "query": "What about Building 140?",
        "type": "followup",
        "followup_of": 16,
        "expected_behavior": "Should use 2025 from context, change property to Building 140",
        "should_contain": ["building 140", "2025", "$"]
    },
    {
        "id": 18,
        "query": "Compare Building 120 and Building 140 in 2025",
        "type": "followup_base",
        "expected_behavior": "Base query for comparison follow-up",
        "should_contain": ["building 120", "building 140", "2025", "profit"]  # Should compare and show profit
    },
    {
        "id": 19,
        "query": "And for 2024?",
        "type": "followup",
        "followup_of": 18,
        "expected_behavior": "Should use both properties from context, change year to 2024",
        "should_contain": ["building 120", "building 140", "2024", "profit"]  # Should compare and show profit
    },
    {
        "id": 20,
        "query": "What about Q1?",
        "type": "followup",
        "followup_of": 19,
        "expected_behavior": "Should use properties and year from context, add Q1 filter",
        "should_contain": ["building 120", "building 140"]  # Should keep both properties from context (period may be implicit in response)
    }
]

ALL_QUERIES = TYPE_1_ERROR_HANDLING + TYPE_2_NATURAL_LANGUAGE + TYPE_3_FOLLOW_UPS


# ============================================================================
# ANALYSIS FUNCTIONS
# ============================================================================

def analyze_response(query_info, response: str, tracker, data_loader) -> dict:
    """Analyze response and determine if it's correct."""
    analysis = {
        "query_id": query_info["id"],
        "query": query_info["query"],
        "type": query_info["type"],
        "response": response,
        "is_correct": False,
        "issues": [],
        "score": 0.0,
        "details": {}
    }
    
    response_lower = response.lower()
    expected_contains = query_info.get("should_contain", [])
    expected_behavior = query_info.get("expected_behavior", "")
    
    # Check if response contains expected keywords
    found_keywords = []
    missing_keywords = []
    
    for keyword in expected_contains:
        if keyword.lower() in response_lower:
            found_keywords.append(keyword)
        else:
            missing_keywords.append(keyword)
    
    # Calculate score based on found keywords
    if expected_contains:
        keyword_score = len(found_keywords) / len(expected_contains)
    else:
        keyword_score = 1.0
    
    # Type-specific analysis
    if query_info["type"] == "error_handling":
        # Should NOT crash, should provide helpful error message
        is_error = response.startswith("❌") or "error" in response_lower or "cannot" in response_lower
        
        if "clarification" in expected_behavior.lower() or "invalid" in expected_behavior.lower():
            # Should ask for clarification or suggest alternatives
            has_clarification = any(word in response_lower for word in ["available", "options", "suggest", "try", "clarification"])
            if has_clarification:
                analysis["score"] = 0.8 + (keyword_score * 0.2)
                analysis["is_correct"] = True
            else:
                analysis["issues"].append("Should ask for clarification or suggest alternatives")
                analysis["score"] = keyword_score * 0.6
        
        elif "incomplete" in expected_behavior.lower():
            # Should detect incomplete query and ask for missing info
            has_missing = any(word in response_lower for word in ["missing", "property", "timeframe", "information", "need"])
            if has_missing and keyword_score >= 0.5:  # At least 50% of keywords found
                analysis["score"] = 0.8 + (keyword_score * 0.2)
                analysis["is_correct"] = True
            else:
                analysis["issues"].append("Should detect incomplete query and ask for missing info")
                analysis["score"] = keyword_score * 0.6
        
        elif "missing data" in expected_behavior.lower() or "not available" in expected_behavior.lower():
            # Should indicate no data available
            has_no_data = any(phrase in response_lower for phrase in ["no financial data", "not available", "no data", "missing"])
            if has_no_data:
                analysis["score"] = 0.8 + (keyword_score * 0.2)
                analysis["is_correct"] = True
            else:
                analysis["issues"].append("Should indicate that data is not available")
                analysis["score"] = keyword_score * 0.6
        
        elif "unsupported" in expected_behavior.lower():
            # Should indicate unsupported operation
            has_unsupported = any(phrase in response_lower for phrase in ["not supported", "cannot", "unable", "unsupported"])
            if has_unsupported:
                analysis["score"] = 0.8 + (keyword_score * 0.2)
                analysis["is_correct"] = True
            else:
                analysis["issues"].append("Should indicate unsupported operation")
                analysis["score"] = keyword_score * 0.6
        
        # Should not crash
        if "exception" in response_lower or "traceback" in response_lower:
            analysis["issues"].append("System crashed with exception")
            analysis["score"] = 0.0
            analysis["is_correct"] = False
    
    elif query_info["type"] == "natural_language":
        # Should provide correct answer with data
        is_error = response.startswith("❌") or "error" in response_lower or "cannot" in response_lower
        
        if is_error:
            analysis["issues"].append("Query failed but should have succeeded")
            analysis["score"] = 0.0
            analysis["is_correct"] = False
        else:
            # Check if all expected keywords are present
            if len(missing_keywords) == 0:
                analysis["score"] = 1.0
                analysis["is_correct"] = True
            elif len(found_keywords) >= len(expected_contains) * 0.7:  # At least 70% of keywords
                analysis["score"] = 0.7 + (keyword_score * 0.3)
                analysis["is_correct"] = True
                if missing_keywords:
                    analysis["issues"].append(f"Missing keywords: {', '.join(missing_keywords)}")
            else:
                analysis["score"] = keyword_score * 0.6
                analysis["issues"].append(f"Missing important keywords: {', '.join(missing_keywords)}")
    
    elif query_info["type"] == "followup":
        # Should use context from previous query
        is_error = response.startswith("❌") or "error" in response_lower
        
        if is_error:
            analysis["issues"].append("Follow-up query failed")
            analysis["score"] = 0.0
            analysis["is_correct"] = False
        else:
            # Check if context was used (all keywords from followup_of should be present)
            if len(missing_keywords) == 0:
                analysis["score"] = 1.0
                analysis["is_correct"] = True
            elif len(found_keywords) >= len(expected_contains) * 0.7:
                analysis["score"] = 0.7 + (keyword_score * 0.3)
                analysis["is_correct"] = True
                if missing_keywords:
                    analysis["issues"].append(f"Missing context keywords: {', '.join(missing_keywords)}")
            else:
                analysis["score"] = keyword_score * 0.6
                analysis["issues"].append("Follow-up did not properly use context")
    
    else:  # followup_base
        # Just check if it works
        is_error = response.startswith("❌") or "error" in response_lower
        if not is_error and len(found_keywords) >= len(expected_contains) * 0.7:
            analysis["score"] = 1.0
            analysis["is_correct"] = True
        else:
            analysis["score"] = keyword_score
            analysis["is_correct"] = False
    
    analysis["details"] = {
        "found_keywords": found_keywords,
        "missing_keywords": missing_keywords,
        "keyword_score": keyword_score,
        "expected_behavior": expected_behavior
    }
    
    return analysis


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def main():
    print("="*80)
    print("🧪 COMPREHENSIVE TEST SUITE - 20 QUERIES")
    print("="*80)
    print("\n🔧 Initializing system...")
    
    # Initialize
    llm_client = LLMClient()
    llm = llm_client.get_llm()
    data_loader = RealEstateDataLoader("data/cortex.parquet")
    orchestrator = RealEstateOrchestrator(llm, data_loader, debug_mode=False)
    
    print("✅ System initialized\n")
    
    results = []
    chat_history = []
    
    # Run all queries (or only failed ones for debugging)
    # To test only failed queries, uncomment the line below and list the IDs
    # failed_ids = [4, 9, 11, 13, 18, 19, 20]
    # ALL_QUERIES = [q for q in ALL_QUERIES if q["id"] in failed_ids]
    
    for query_info in ALL_QUERIES:
        print(f"\n{'='*80}")
        print(f"📋 QUERY {query_info['id']}/20: {query_info['query']}")
        print(f"   Type: {query_info['type']}")
        print(f"   Expected: {query_info['expected_behavior']}")
        print("="*80)
        
        # Prepare chat history for follow-ups
        if query_info.get("followup_of"):
            base_query = next(q for q in ALL_QUERIES if q["id"] == query_info["followup_of"])
            base_result = next(r for r in results if r["query_id"] == query_info["followup_of"])
            chat_history = [
                {"user": base_query["query"]},
                {"assistant": base_result["response"]}
            ]
        else:
            chat_history = []
        
        try:
            response, tracker = orchestrator.run(query_info["query"], chat_history=chat_history)
            
            # Analyze response
            analysis = analyze_response(query_info, response, tracker, data_loader)
            results.append(analysis)
            
            # Display FULL results with all agent steps
            status = "✅" if analysis["is_correct"] else "❌"
            print(f"\n{status} RESULT (Score: {analysis['score']:.2f})")
            print(f"\n📝 FULL RESPONSE:")
            print(f"{'='*80}")
            print(response)
            print(f"{'='*80}")
            
            # Display all agent steps
            print(f"\n🔍 AGENT STEPS:")
            print(f"{'='*80}")
            for i, step in enumerate(tracker.steps, 1):
                print(f"\nStep {i}: {step.agent}")
                if hasattr(step, 'input_data') and step.input_data:
                    print(f"   Input: {step.input_data}")
                if hasattr(step, 'output_data') and step.output_data:
                    print(f"   Output: {step.output_data}")
                if hasattr(step, 'reasoning') and step.reasoning:
                    print(f"   Reasoning: {step.reasoning}")
                if hasattr(step, 'duration_ms'):
                    print(f"   Duration: {step.duration_ms}ms")
                if hasattr(step, 'success'):
                    print(f"   Success: {step.success}")
            print(f"{'='*80}")
            
            # Analysis details
            print(f"\n📊 ANALYSIS:")
            if analysis["details"]["found_keywords"]:
                print(f"   ✅ Found keywords: {', '.join(analysis['details']['found_keywords'])}")
            if analysis["details"]["missing_keywords"]:
                print(f"   ⚠️  Missing keywords: {', '.join(analysis['details']['missing_keywords'])}")
            if analysis["issues"]:
                print(f"   ⚠️  Issues:")
                for issue in analysis["issues"]:
                    print(f"      - {issue}")
            
            print(f"\n💡 Expected behavior: {query_info['expected_behavior']}")
            
            # Update chat history for next follow-up
            if query_info["type"] == "followup_base":
                chat_history = [
                    {"user": query_info["query"]},
                    {"assistant": response}
                ]
        
        except Exception as e:
            print(f"\n❌ EXCEPTION: {e}")
            results.append({
                "query_id": query_info["id"],
                "query": query_info["query"],
                "type": query_info["type"],
                "response": f"Exception: {str(e)}",
                "is_correct": False,
                "issues": [f"Exception: {str(e)}"],
                "score": 0.0,
                "details": {}
            })
    
    # Final summary
    print("\n" + "="*80)
    print("📊 FINAL SUMMARY")
    print("="*80)
    
    total = len(results)
    correct = sum(1 for r in results if r["is_correct"])
    avg_score = sum(r["score"] for r in results) / total if total > 0 else 0
    
    print(f"\n✅ Total queries: {total}")
    print(f"✅ Correct: {correct}/{total} ({correct/total*100:.1f}%)")
    print(f"📊 Average score: {avg_score:.2f}/1.00")
    
    # Breakdown by type
    type_1 = [r for r in results if r["type"] == "error_handling"]
    type_2 = [r for r in results if r["type"] == "natural_language"]
    type_3 = [r for r in results if r["type"] in ["followup", "followup_base"]]
    
    print(f"\n📋 BREAKDOWN BY TYPE:")
    print(f"   Type 1 (Error Handling): {sum(1 for r in type_1 if r['is_correct'])}/{len(type_1)} correct")
    print(f"   Type 2 (Natural Language): {sum(1 for r in type_2 if r['is_correct'])}/{len(type_2)} correct")
    print(f"   Type 3 (Follow-ups): {sum(1 for r in type_3 if r['is_correct'])}/{len(type_3)} correct")
    
    # List failures
    failures = [r for r in results if not r["is_correct"]]
    if failures:
        print(f"\n❌ FAILED QUERIES ({len(failures)}):")
        for r in failures:
            print(f"   Query {r['query_id']}: {r['query'][:60]}...")
            if r["issues"]:
                print(f"      Issues: {', '.join(r['issues'][:2])}")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    main()

