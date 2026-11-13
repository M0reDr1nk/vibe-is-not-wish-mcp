#!/usr/bin/env python3
"""Run consistency check (text method) on L4 implementation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from vinw.store.project import Project
from vinw.workflow.consistency_llm import TextConsistencyChecker

# Check the vinw code against its own design docs
proj = Project(Path("/mnt/agents/output/vinw-design"))
checker = TextConsistencyChecker(proj)

# api-design.md vs vinw/ code
result = checker.check(
    design_layer="L3-方案细化",
    design_doc="api-design.md",
    code_scope=["vinw"]
)

print("=" * 60)
print("CONSISTENCY CHECK (method='text')")
print("=" * 60)
print(f"Design doc: {result['design_doc']}")
print(f"Overall: {result['overall']}")
print(f"Design symbols found: {result['design_symbols_found']}")
print(f"Matched: {len(result['matched'])}")
print(f"Inconsistencies: {len(result['inconsistencies'])}")

if result['inconsistencies']:
    print("\n--- Inconsistencies ---")
    for inc in result['inconsistencies']:
        print(f"\n  [{inc['severity'].upper()}] {inc['id']}")
        print(f"    Description: {inc['description']}")
        print(f"    Design ref:  {inc['design_ref']}")
        print(f"    Suggestion:  {inc['suggestion']}")
else:
    print("\n✅ No text-level inconsistencies found")

# Store report
from vinw.workflow.consistency_llm import LLMConsistencyAuditor
auditor = LLMConsistencyAuditor(proj)
report_path = auditor.store_report(result, report_id="L4-r1-text")
print(f"\nReport stored: {report_path}")
