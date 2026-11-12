"""Phase 5: pytest invariant suite.
Locks the underwriting engine's math so no future edit silently breaks the interview numbers.
Run with: pytest -v"""
import json
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"

# Load engine outputs
S = json.loads((OUT / "underwriting_summary.json").read_text())
RANK = list(csv.DictReader(open(OUT / "asset_ranking.csv")))

def test_breakeven_below_target():
    """Margin of safety: break-even occupancy must be strictly below target occupancy."""
    for aid, a in S["assets"].items():
        assert a["breakeven_occ"] < a["target_occupancy"], f"{aid} break-even exceeds target"

def test_capex_rollup_consistent():
    """Total capex must be greater than hard capex, which must be positive."""
    for aid, a in S["assets"].items():
        assert a["capex_base"] > a["hard_capex"] > 0, f"{aid} capex rollup logic broken"

def test_verdict_domain():
    """Verdict must be one of the three engineered states."""
    valid = {"GO", "CONDITIONAL GO (lever-dependent)", "NO-GO"}
    for aid, a in S["assets"].items():
        assert a["verdict"] in valid, f"{aid} verdict '{a['verdict']}' outside domain"

def test_levers_improve_npv():
    """Levered case (subsidy + rent-free + ADR push) must strictly improve NPV vs base case."""
    for aid, a in S["assets"].items():
        assert a["npv_levers"] > a["npv_base"], f"{aid} levers did not improve NPV"

def test_statutory_gate_flagged():
    """Portfolio must contain at least one statutory dealbreaker (HYD has Fire NOC)."""
    total_dealbreakers = sum(len(a["dealbreakers"]) for a in S["assets"].values())
    assert total_dealbreakers >= 1, "No dealbreakers found in portfolio"