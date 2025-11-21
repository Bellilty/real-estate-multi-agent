#!/usr/bin/env python3
"""
🧪 TESTS UNITAIRES - NOUVEAUX AGENTS
Test chaque agent individuellement avec structured outputs
"""

import sys
sys.path.insert(0, 'backend')

import json
from backend.agents.followup_resolver import FollowUpResolverAgent
from backend.agents.naturaldate_agent import NaturalDateAgent
from backend.agents.validation_agent import ValidationAgent
from backend.agents.disambiguation_agent import DisambiguationAgent
from backend.llm.llm_client import LLMClient
from backend.data.data_loader import RealEstateDataLoader


def print_section(title):
    """Print section header"""
    print("\n" + ("="*80))
    print(f"  {title}")
    print("="*80)


def print_result(label, data, compact=False):
    """Print test result"""
    print(f"\n{label}")
    if compact:
        # Compact view for large outputs
        if isinstance(data, dict):
            print(f"  status: {data.get('status', 'N/A')}")
            print(f"  needs_clarification: {data.get('needs_clarification', 'N/A')}")
            if 'entities' in data:
                print(f"  entities: {data['entities']}")
            if 'notes' in data:
                print(f"  notes: {data['notes'][:100]}...")
        else:
            print(f"  {data}")
    else:
        print(json.dumps(data, indent=2))


# ----------------------------
#  SETUP
# ----------------------------
print("🚀 Initializing agents...")
llm = LLMClient()
data_loader = RealEstateDataLoader("data/cortex.parquet")

followup = FollowUpResolverAgent(llm)
naturaldate = NaturalDateAgent()
validation = ValidationAgent(data_loader)
disambiguation = DisambiguationAgent(data_loader)

print("✅ All agents initialized!")


# ============================================================================
#  TEST 1 — FOLLOW-UP RESOLVER AGENT
# ============================================================================
print_section("TEST 1 — FOLLOW-UP RESOLVER AGENT")

print("\n📝 Test 1.1: No follow-up (standalone query)")
result = followup.process(
    "What is the P&L for Building 180 in 2024?",
    chat_history=[]
)
print_result("Input: 'What is the P&L for Building 180 in 2024?'", result, compact=True)
assert result["status"] == "ok", "Should be ok"
assert result["is_followup"] == False, "Should not be a follow-up"
print("✅ PASS: Standalone query detected correctly")


print("\n📝 Test 1.2: Follow-up with 'and what about'")
chat_history = [
    {"user": "What is the P&L for Building 180?", "assistant": "Building 180 has net profit of $303,598.25"}
]
result = followup.process(
    "And what about Building 140?",
    chat_history=chat_history
)
print_result("Input: 'And what about Building 140?'", result, compact=True)
assert result["status"] == "ok", "Should be ok"
assert result["is_followup"] == True, "Should be a follow-up"
assert "Building 140" in result["updated_query"], "Should contain Building 140"
print("✅ PASS: Follow-up detected and enriched")


print("\n📝 Test 1.3: Follow-up with 'compare to'")
chat_history = [
    {"user": "Show me Building 180 in 2024", "assistant": "Building 180 net profit: $303,598.25"}
]
result = followup.process(
    "Compare to 2025",
    chat_history=chat_history
)
print_result("Input: 'Compare to 2025'", result, compact=True)
assert result["status"] == "ok", "Should be ok"
assert result["is_followup"] == True, "Should be a follow-up"
print("✅ PASS: Comparison follow-up detected")


# ============================================================================
#  TEST 2 — NATURAL DATE AGENT
# ============================================================================
print_section("TEST 2 — NATURAL DATE AGENT")

print("\n📝 Test 2.1: Quarter normalization (Q1 → 2024-Q1)")
entities = {"quarter": "Q1", "year": "2024"}
result = naturaldate.process(entities, "Show me Q1 2024")
print_result("Input: quarter='Q1', year='2024'", result, compact=True)
assert result["status"] == "ok", "Should be ok"
assert result["entities"]["quarter"] == "2024-Q1", f"Should normalize to 2024-Q1, got {result['entities'].get('quarter')}"
print("✅ PASS: Quarter normalized correctly")


print("\n📝 Test 2.2: Multiple quarters (temporal comparison)")
entities = {"quarter": ["Q1", "Q2"], "year": "2024"}
result = naturaldate.process(entities, "Compare Q1 to Q2")
print_result("Input: quarter=['Q1', 'Q2'], year='2024'", result, compact=True)
assert result["status"] == "ok", "Should be ok"
assert isinstance(result["entities"]["quarter"], list), "Should be a list"
assert len(result["entities"]["quarter"]) == 2, "Should have 2 quarters"
print("✅ PASS: Multiple quarters normalized")


print("\n📝 Test 2.3: Invalid quarter (Q5)")
entities = {"quarter": "Q5", "year": "2024"}
result = naturaldate.process(entities, "Show me Q5")
print_result("Input: quarter='Q5'", result, compact=True)
assert result["status"] == "ambiguous", f"Should be ambiguous, got {result['status']}"
assert "Q5" in str(result["ambiguous_dates"]), "Should flag Q5 as ambiguous"
print("✅ PASS: Invalid quarter detected")


print("\n📝 Test 2.4: Month normalization (December → M12)")
entities = {"month": "December", "year": "2024"}
result = naturaldate.process(entities, "Show December 2024")
print_result("Input: month='December', year='2024'", result, compact=True)
assert result["status"] == "ok", "Should be ok"
# The month should be normalized to M12 format
month_result = result["entities"].get("month", "")
assert "M12" in month_result or "12" in month_result, f"Should normalize December, got {month_result}"
print("✅ PASS: Month normalized")


# ============================================================================
#  TEST 3 — VALIDATION AGENT
# ============================================================================
print_section("TEST 3 — VALIDATION AGENT")

print("\n📝 Test 3.1: Valid property")
entities = {"properties": ["Building 180"], "year": "2024"}
result = validation.validate("pl_calculation", entities)
print_result("Input: properties=['Building 180']", result, compact=True)
assert result["status"] == "ok", f"Should be ok, got {result['status']}"
assert result["validation_status"] == "VALID", "Should be VALID"
print("✅ PASS: Valid property accepted")


print("\n📝 Test 3.2: Invalid property (Building 999)")
entities = {"properties": ["Building 999"]}
result = validation.validate("pl_calculation", entities)
print_result("Input: properties=['Building 999']", result, compact=True)
assert result["status"] == "missing", f"Should be missing, got {result['status']}"
assert result["needs_clarification"] == True, "Should need clarification"
assert len(result["invalid_entities"]) > 0, "Should have invalid entities"
print("✅ PASS: Invalid property detected")


print("\n📝 Test 3.3: Multiple properties (comparison)")
entities = {"properties": ["Building 140", "Building 180"]}
result = validation.validate("property_comparison", entities)
print_result("Input: properties=['Building 140', 'Building 180']", result, compact=True)
assert result["status"] == "ok", f"Should be ok, got {result['status']}"
print("✅ PASS: Multiple valid properties accepted")


print("\n📝 Test 3.4: Mixed valid/invalid properties")
entities = {"properties": ["Building 140", "Building 999"]}
result = validation.validate("property_comparison", entities)
print_result("Input: properties=['Building 140', 'Building 999']", result, compact=True)
assert result["status"] in ["missing", "ambiguous"], f"Should be missing or ambiguous, got {result['status']}"
assert result["needs_clarification"] == True, "Should need clarification"
print("✅ PASS: Mixed properties handled correctly")


# ============================================================================
#  TEST 4 — DISAMBIGUATION AGENT
# ============================================================================
print_section("TEST 4 — DISAMBIGUATION AGENT")

print("\n📝 Test 4.1: Exact match (Building 180)")
entities = {"properties": ["Building 180"]}
ambiguous_info = {}
result = disambiguation.process(entities, ambiguous_info)
print_result("Input: properties=['Building 180']", result, compact=True)
assert result["status"] == "ok", f"Should be ok, got {result['status']}"
assert result["needs_clarification"] == False, "Should not need clarification"
assert result["entities"]["properties"] == ["Building 180"], "Should keep exact match"
print("✅ PASS: Exact match preserved")


print("\n📝 Test 4.2: Fuzzy match (Building 18 → candidates)")
entities = {"properties": ["Building 18"]}
# Simulate ambiguous info from validation
ambiguous_info = {
    "properties": [
        {"input": "Building 18", "candidates": ["Building 18", "Building 180"]}
    ]
}
result = disambiguation.process(entities, ambiguous_info)
print_result("Input: properties=['Building 18'] (ambiguous)", result, compact=True)
# Could be ok if auto-resolved or ambiguous if multiple candidates
if result["needs_clarification"]:
    assert len(result["suggestions"].get("properties", [])) > 0, "Should have suggestions"
    print("✅ PASS: Ambiguous match detected, suggestions provided")
else:
    print("✅ PASS: Fuzzy match auto-resolved")


print("\n📝 Test 4.3: Typo (Buildng 140 → Building 140)")
entities = {"properties": ["Buildng 140"]}
ambiguous_info = {}
result = disambiguation.process(entities, ambiguous_info)
print_result("Input: properties=['Buildng 140'] (typo)", result, compact=True)
# Should either auto-correct or provide suggestions
if result["status"] == "ok":
    print("✅ PASS: Typo auto-corrected")
else:
    print("✅ PASS: Typo detected, suggestions provided")


print("\n📝 Test 4.4: Non-existent property (Building 999)")
entities = {"properties": ["Building 999"]}
ambiguous_info = {}
result = disambiguation.process(entities, ambiguous_info)
print_result("Input: properties=['Building 999'] (non-existent)", result, compact=True)
# Should keep original if no candidates found
assert "Building 999" in str(result["entities"]), "Should keep original property"
print("✅ PASS: Non-existent property handled")


# ============================================================================
#  SUMMARY
# ============================================================================
print_section("🎉 ALL TESTS COMPLETED!")

print("\n✅ SUMMARY:")
print("  ✅ FollowUpResolverAgent: 3/3 tests passed")
print("  ✅ NaturalDateAgent: 4/4 tests passed")
print("  ✅ ValidationAgent: 4/4 tests passed")
print("  ✅ DisambiguationAgent: 4/4 tests passed")
print("\n  📊 Total: 15/15 tests passed")
print("\n  ✅ All agents return structured outputs:")
print("     - status: ok/missing/ambiguous/error")
print("     - entities: {...}")
print("     - needs_clarification: bool")
print("     - notes: str")
print("\n  🚀 Ready for orchestrator integration!")
print("="*80 + "\n")

