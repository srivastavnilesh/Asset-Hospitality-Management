"""Phase 4: converts Phase 3 engine outputs into a founder-grade markdown dossier.
Adds direct-compset positioning, assumption register, and Module-0 provenance.
Writes outputs/underwriting_dossier.md + outputs/logs/phase4_run_<ts>.log."""
import json, sqlite3, sys, dataclasses
from datetime import datetime
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from config import ASSET, MARKET, OPEX, CAPITAL

OUT = ROOT / "outputs"
LOGD = OUT / "logs"
if LOGD.exists() and not LOGD.is_dir(): LOGD.unlink()
LOGD.mkdir(parents=True, exist_ok=True)
LOG = LOGD / f"phase4_run_{datetime.now():%Y%m%d_%H%M%S}.log"
LINES = []
def emit(*a):
    s = " ".join(str(x) for x in a); print(s); LINES.append(s)

S = json.loads((OUT / "underwriting_summary.json").read_text())
ranking = pd.read_csv(OUT / "asset_ranking.csv")
conn = sqlite3.connect(ROOT / "data" / "asset_underwriting.db")
profile = pd.read_sql("SELECT * FROM asset_profile", conn)
comps   = pd.read_sql("SELECT * FROM market_comps", conn)
phys    = pd.read_sql("SELECT * FROM physical_audit", conn)
stat    = pd.read_sql("SELECT * FROM statutory_compliance", conn)
art     = pd.read_sql("SELECT * FROM artisan_registry", conn)
conn.close()

def md(df):
    c = [str(x) for x in df.columns]
    out = ["| " + " | ".join(c) + " |", "| " + " | ".join(["---"] * len(c)) + " |"]
    out += ["| " + " | ".join(str(v) for v in row) + " |" for row in df.values]
    return "\n".join(out)

def cr(x): return f"Rs {x/1e7:.2f} Cr"

rk = ranking.copy()
rk["npv_base_Cr"] = (rk.npv_base / 1e7).round(2); rk["npv_levers_Cr"] = (rk.npv_levers / 1e7).round(2)
rk["irr_levers_pct"] = (rk.irr_levers * 100).round(1); rk["capex_Cr"] = (rk.capex_base / 1e7).round(2)
rk["breakeven_pct"] = (rk.breakeven_occ * 100).round(1)
rk = rk[["rank","asset_id","name","verdict","npv_base_Cr","npv_levers_Cr","irr_levers_pct",
         "capex_Cr","breakeven_pct","dealbreaker_count"]]

sections = []
for aid, s in S["assets"].items():
    row = profile[profile.asset_id == aid].iloc[0]
    pnl = pd.read_csv(OUT / f"pnl_{aid}.csv")
    sens = pd.read_csv(OUT / f"sensitivity_{aid}.csv")
    c = comps[comps.asset_id == aid]
    direct = c[~c.comp_name.str.contains("proxy", case=False)]
    prem_direct = row.target_adr / direct.adr_inr.mean() - 1
    ph = phys[phys.asset_id == aid][["zone","element","condition","issue","capex_inr","heritage_certified"]]
    st = stat[stat.asset_id == aid][["req","status","risk","cost_inr","days","dealbreaker","note"]]
    ar = art[art.asset_id == aid]
    piv = (sens.pivot(index="adr", columns="occupancy", values="ebitda_y1") / 1e7).round(2).reset_index()
    pl = pnl[["year","gross_revenue","ota_commission","rent","ops","ffe_reserve","ebitda","tax","cash_flow"]].copy()
    for col in pl.columns[1:]: pl[col] = (pl[col] / 1e7).round(2)

    sections.append(f"""### {aid} — {s['name']}
**Verdict:** {s['verdict']} | NPV@12% base {cr(s['npv_base'])} -> levered {cr(s['npv_levers'])} | IRR levered {s['irr_levers']*100:.1f}% vs hurdle {S['hurdle']:.0%}

**Market positioning.** Blended compset ADR Rs {s['mkt_adr']:,.0f} @ {s['mkt_occ']*100:.1f}% (RevPAR premium {s['revpar_premium']*100:+.1f}%). Direct heritage compset mean ADR Rs {direct.adr_inr.mean():,.0f}; target ADR Rs {row.target_adr:,.0f} carries a {prem_direct*100:+.1f}% premium earned via theming scarcity + standardised operations. Positioning sits between direct compset and luxury proxy = deliberate conservatism.

**Capital stack.** Hard {cr(s['hard_capex'])} | soft {cr(s['soft_capex'])} | contingency {cr(s['contingency'])} | working capital {cr(s['working_capital'])} | **total {cr(s['capex_base'])}** (levered {cr(s['capex_levers'])} after {CAPITAL.subsidy_pct_hard:.0%} tourism subsidy).

**Operating case.** Y1 EBITDA {cr(s['ebitda_y1'])} ({s['margin_y1']*100:.1f}% margin). Break-even occupancy {s['breakeven_occ']*100:.1f}% vs target {s['target_occupancy']*100:.0f}% = {s['target_occupancy']*100 - s['breakeven_occ']*100:.1f} pts margin of safety.

**Statutory gate.** Licensing critical path {s['critical_path_days']} days | dealbreakers: {', '.join(s['dealbreakers']) or 'none'}.
{md(st)}

**Physical capex risk register.**
{md(ph)}

**Lease-horizon P&L (Rs Cr).**
{md(pl)}

**Sensitivity — Y1 EBITDA (Rs Cr), ADR x occupancy.**
{md(piv)}

**Theming & artisan pipeline.**
{md(ar)}

**Read:** {s['interpretation']}
""")

assum = pd.concat([
    pd.DataFrame([{"layer": n, "param": f.name, "value": getattr(dc, f.name)} for f in dataclasses.fields(dc)])
    for n, dc in [("asset_primary", ASSET), ("market", MARKET), ("opex", OPEX), ("capital", CAPITAL)]])

doc = f"""# Asset-Hospitality-Management — Portfolio Underwriting Dossier
Run: {S['run_at']} | Hurdle: {S['hurdle']:.0%} | Engine: Phase 3 portfolio underwriter

## 0. Executive summary (ranked by levered NPV)
{md(rk)}

## 1. Asset dossiers
{''.join(sections)}
## 2. Methodology & provenance (Module 0)
Statutory-gate logic, capex contingency practice and egress/setback checks are ported from the
SVNIT digital-twin audit engine (BHI 83.9 governance-capped for a lapsed Fire NOC; IS 1172 norm
135 LPCD vs measured 201; NBC 2016 egress; CPWD Cl. 7.1 guarantee leverage). Hospitality layer adds
industry-standard unit economics: RevPAR indexing vs compset, OTA commission load, FF&E reserve,
rent escalation, and lease-horizon DCF at the founder hurdle rate.

## 3. Assumptions register (single source of truth: config.py)
{md(assum)}
"""
(OUT / "underwriting_dossier.md").write_text(doc)
emit("=" * 70)
emit("PHASE 4 | DOSSIER BUILDER")
emit(f"dossier -> {OUT/'underwriting_dossier.md'} ({len(doc):,} chars, {doc.count(chr(10))+1} lines)")
emit(f"sections: exec summary + {len(sections)} asset dossiers + provenance + assumptions register")
LOG.write_text("\n".join(LINES), encoding="utf-8")
print(f"[log] {LOG}")