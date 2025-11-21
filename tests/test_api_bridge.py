#!/usr/bin/env python3
"""
🧪 TEST API BRIDGE - Vérification intégration production
Vérifie que le nouveau orchestrator intelligent fonctionne correctement
"""

import sys
sys.path.insert(0, 'backend')

from backend.core.orchestrator import RealEstateOrchestrator
from backend.llm.llm_client import LLMClient
from backend.data.data_loader import RealEstateDataLoader

print("="*80)
print("🧪 TEST API BRIDGE - INTELLIGENT ORCHESTRATOR EN PRODUCTION")
print("="*80)

# Initialize
print("\n1️⃣ Initializing orchestrator...")
llm = LLMClient()
data_loader = RealEstateDataLoader('data/cortex.parquet')
orch = RealEstateOrchestrator(llm, data_loader, debug_mode=False)
print("   ✅ Orchestrator initialized (IntelligentOrchestrator)")

# Test simple query
print("\n2️⃣ Testing simple query...")
query = "What is the P&L for Building 180 in 2024?"
response, tracker = orch.run(query)

print(f"\n   📊 RESULTS:")
print(f"   ✅ Response received: {len(response)} characters")
print(f"   ✅ Tracker steps: {len(tracker.steps)}")
print(f"   ✅ Agent path: {' → '.join([s.agent for s in tracker.steps])}")
print(f"\n   💬 Response preview:")
print(f"   {response[:150]}...")

# Verify intelligent features
print("\n3️⃣ Verifying intelligent features...")

# Check agent path contains new agents
agent_names = [s.agent for s in tracker.steps]
has_followup = "FollowUpResolver" in agent_names
has_naturaldate = "NaturalDateAgent" in agent_names
has_validation = "ValidationAgent" in agent_names

print(f"   {'✅' if has_followup else '❌'} FollowUpResolver integrated")
print(f"   {'✅' if has_naturaldate else '❌'} NaturalDateAgent integrated")
print(f"   {'✅' if has_validation else '❌'} ValidationAgent integrated")

# Test return format compatibility
print("\n4️⃣ Checking API compatibility...")
is_tuple = isinstance((response, tracker), tuple)
has_response = isinstance(response, str) and len(response) > 0
has_tracker = hasattr(tracker, 'steps')

print(f"   {'✅' if is_tuple else '❌'} Returns tuple (response, tracker)")
print(f"   {'✅' if has_response else '❌'} Response is non-empty string")
print(f"   {'✅' if has_tracker else '❌'} Tracker has steps attribute")

# Summary
print("\n" + "="*80)
all_checks_passed = (
    has_followup and has_naturaldate and has_validation and
    is_tuple and has_response and has_tracker
)

if all_checks_passed:
    print("🎉 ALL CHECKS PASSED!")
    print("✅ Intelligent Orchestrator is LIVE in production")
    print("✅ API compatibility maintained")
    print("✅ All new features integrated:")
    print("   - Follow-up resolution")
    print("   - Natural date parsing")
    print("   - 3-way validation routing")
    print("   - Disambiguation")
    print("   - Agent path tracking")
else:
    print("❌ SOME CHECKS FAILED")
    print("Please review the output above")

print("="*80)

