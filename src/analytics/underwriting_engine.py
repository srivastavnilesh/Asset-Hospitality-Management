"""Phase 3: portfolio-aware hospitality underwriting engine.
Screen fast (compset indexing + statutory gate), underwrite deep
(lease-horizon P&L, NPV/IRR vs hurdle, break-even, sensitivity, verdict).
Every run writes outputs/logs/phase3_run_<ts>.log for audit & presentation."""
import json, sqlite3, sys
from datetime import datetime
from pathlib import Path
import numpy as np
import numpy_financial as npf
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from config import ASSET, MARKET, OPEX, CAPITAL

DB = ROOT / "data" / "asset_underwriting.db"
if not DB.exists():
    sys.path.insert(0, str(ROOT / "src" / "data")); import generate_dataset  # self-provision
OUT = ROOT / "outputs"; OUT.mkdir(parents=True, exist_ok=True)
LOGD = OUT / "logs"; LOGD.mkdir(parents=True, exist_ok=True)
LOG = LOGD / f"phase3_run_{datetime.now():%Y%m%d_%H%M%S}.log"

LINES = []
def emit(*args):
    s = " ".join(str(a) for a in args)
    print(s); LINES.append(s)

conn = sqlite3.connect(DB)
profile = pd.read_sql("SELECT * FROM asset_profile", conn)
comps   = pd.read_sql("SELECT * FROM market_comps", conn)
phys    = pd.read_sql("SELECT * FROM physical_audit", conn)
stat    = pd.read_sql("SELECT * FROM statutory_compliance", conn)
conn.close()
BASE_KEYS, BASE_SQFT = ASSET.keys, ASSET.total_sqft

def evaluate(a):
    aid = a["asset_id"]
    c, ph, st = comps[comps.asset_id == aid], phys[phys.asset_id == aid], stat[stat.asset_id == aid]
    mkt_adr, mkt_occ = c.adr_inr.mean(), c.occupancy_pct.mean() / 100
    revpar_premium = (a["target_adr"] * a["target_occupancy"]) / (mkt_adr * mkt_occ) - 1

    hard = float(ph.capex_inr.sum())
    soft = float(st.cost_inr.sum()) + CAPITAL.design_consultant * (a["total_sqft"] / BASE_SQFT) \
           + CAPITAL.pre_opening * (a["keys"] / BASE_KEYS)
    cont = hard * CAPITAL.contingency_pct
    wc = CAPITAL.working_capital * (a["keys"] / BASE_KEYS)
    capex_base = hard + soft + cont + wc
    capex_lev = capex_base - hard * CAPITAL.subsidy_pct_hard

    payroll = OPEX.payroll_ops_y1 * (a["keys"] / BASE_KEYS)
    rent_y1 = a["monthly_rent_y1"] * 12
    dealb = st[st.dealbreaker == True]
    crit_days = int(st.days.sum())

    def pnl(adr, occ, capex, rf):
        rows = []
        for y in range(1, int(a["lease_years"]) + 1):
            g = (1 + MARKET.revpar_growth) ** (y - 1)
            room = a["keys"] * adr * occ * 365 * g
            gross = room * (1 + MARKET.fnb_attach)
            ota = gross * MARKET.ota_commission
            rent = rent_y1 * (1 + ASSET.rent_escalation) ** (y - 1) * ((12 - rf) / 12 if y == 1 else 1)
            ops = payroll * (1 + OPEX.opex_inflation) ** (y - 1)
            ffe = gross * OPEX.ff_e_reserve_pct_revenue
            ebitda = gross - (ota + rent + ops + ffe)
            tax = 0.25 * max(0.0, ebitda - hard / a["lease_years"])
            rows.append(dict(year=y, gross_revenue=gross, ota_commission=ota, rent=rent, ops=ops,
                             ffe_reserve=ffe, ebitda=ebitda, tax=tax, cash_flow=ebitda - tax))
        df = pd.DataFrame(rows)
        cf = np.concatenate([[-capex], df.cash_flow.values, [wc]])
        return df, float(npf.npv(CAPITAL.discount_rate, cf)), float(npf.irr(cf))

    pnl_base, npv_b, irr_b = pnl(a["target_adr"], a["target_occupancy"], capex_base, 0)
    adr_lev = a["target_adr"] * (CAPITAL.adr_lever / MARKET.target_adr)
    occ_lev = min(0.85, a["target_occupancy"] + 0.02)
    pnl_lev, npv_l, irr_l = pnl(adr_lev, occ_lev, capex_lev, CAPITAL.rent_free_months_lever)

    fixed = rent_y1 + payroll
    breakeven = fixed / (a["keys"] * a["target_adr"] * (1 - MARKET.ota_commission) * 365)

    sens = []
    for adr in [a["target_adr"] * 0.9, a["target_adr"], a["target_adr"] * 1.1]:
        for occ in [a["target_occupancy"] - 0.10, a["target_occupancy"], a["target_occupancy"] + 0.10]:
            gross = a["keys"] * adr * occ * 365 * (1 + MARKET.fnb_attach)
            eb = gross - (gross * MARKET.ota_commission + fixed + gross * OPEX.ff_e_reserve_pct_revenue)
            sens.append(dict(adr=int(adr), occupancy=round(occ, 2), ebitda_y1=int(eb),
                             payback_yrs=round(capex_base / eb, 1) if eb > 0 else None))
    sensitivity = pd.DataFrame(sens)

    if npv_b >= 0: verdict = "GO"
    elif npv_l >= 0: verdict = "CONDITIONAL GO (lever-dependent)"
    else: verdict = "NO-GO"

    bits = []
    if len(dealb): bits.append(f"binding statutory constraint: {dealb.req.iloc[0]}")
    if npv_b < 0 <= npv_l: bits.append("base case fails 12% hurdle; levers (tourism subsidy + rent-free fit-out + theming-driven ADR) flip it positive")
    elif npv_b >= 0: bits.append("clears 12% hurdle on base case")
    else: bits.append("fails hurdle even with levers - restructure lease or walk away")
    bits.append(f"margin of safety {a['target_occupancy']*100 - breakeven*100:.1f} pts of occupancy")
    interp = "; ".join(bits)

    pnl_base.to_csv(OUT / f"pnl_{aid}.csv", index=False)
    sensitivity.to_csv(OUT / f"sensitivity_{aid}.csv", index=False)
    return dict(asset_id=aid, name=a["name"], verdict=verdict, npv_base=npv_b, irr_base=irr_b,
                npv_levers=npv_l, irr_levers=irr_l, hard_capex=hard, soft_capex=soft, contingency=cont,
                working_capital=wc, capex_base=capex_base, capex_levers=capex_lev, breakeven_occ=breakeven,
                target_occupancy=a["target_occupancy"], ebitda_y1=float(pnl_base.ebitda.iloc[0]),
                margin_y1=float(pnl_base.ebitda.iloc[0] / pnl_base.gross_revenue.iloc[0]),
                mkt_adr=mkt_adr, mkt_occ=mkt_occ, revpar_premium=revpar_premium,
                critical_path_days=crit_days, dealbreakers=list(dealb.req), interpretation=interp), pnl_base, sensitivity

results = [evaluate(row) for _, row in profile.iterrows()]
summary = {r[0]["asset_id"]: r[0] for r in results}
ranking = pd.DataFrame([{**{k: s[k] for k in ("asset_id","name","verdict","npv_base","npv_levers",
             "irr_levers","capex_base","breakeven_occ")}, "dealbreaker_count": len(s["dealbreakers"])}
             for s, _, _ in results]).sort_values("npv_levers", ascending=False).reset_index(drop=True)
ranking.insert(0, "rank", ranking.index + 1)
ranking.to_csv(OUT / "asset_ranking.csv", index=False)
(OUT / "underwriting_summary.json").write_text(
    json.dumps({"run_at": datetime.now().isoformat(), "hurdle": CAPITAL.discount_rate,
                "assets": summary, "ranking": ranking.to_dict("records")}, indent=2))

emit("=" * 78)
emit("ASSET-HOSPITALITY-MANAGEMENT | PORTFOLIO UNDERWRITING ENGINE | PHASE 3")
emit(f"Run: {datetime.now():%Y-%m-%d %H:%M:%S} | Hurdle rate: {CAPITAL.discount_rate:.0%}")
emit("=" * 78)
for s, pnl_base, sens in results:
    emit(f"\n--- {s['asset_id']} | {s['name']} ---")
    emit(f"VERDICT: {s['verdict']}")
    emit(f"NPV @12%: base Rs {s['npv_base']/1e7:+.2f} Cr | levered Rs {s['npv_levers']/1e7:+.2f} Cr | "
         f"IRR levered {s['irr_levers']*100:.1f}%")
    emit(f"Capex: hard Rs {s['hard_capex']/1e7:.2f} Cr + soft Rs {s['soft_capex']/1e7:.2f} Cr + "
         f"contingency Rs {s['contingency']/1e7:.2f} Cr + WC Rs {s['working_capital']/1e7:.2f} Cr "
         f"= Rs {s['capex_base']/1e7:.2f} Cr (levered Rs {s['capex_levers']/1e7:.2f} Cr)")
    emit(f"Compset ADR Rs {s['mkt_adr']:,.0f} @ {s['mkt_occ']*100:.1f}% | RevPAR premium {s['revpar_premium']*100:+.1f}%")
    emit(f"Y1 EBITDA Rs {s['ebitda_y1']/1e7:.2f} Cr ({s['margin_y1']*100:.1f}% margin) | "
         f"break-even occ {s['breakeven_occ']*100:.1f}% vs target {s['target_occupancy']*100:.0f}%")
    emit(f"Licensing critical path: {s['critical_path_days']} days | dealbreakers: {s['dealbreakers'] or 'none'}")
    emit(f"READ: {s['interpretation']}")
emit("\n--- PORTFOLIO RANKING (by levered NPV) ---")
emit(ranking.to_string(index=False))
emit(f"\n[exports] pnl_*.csv, sensitivity_*.csv, asset_ranking.csv, underwriting_summary.json -> {OUT}")

LOG.write_text("\n".join(LINES), encoding="utf-8")
print(f"[log] {LOG}")