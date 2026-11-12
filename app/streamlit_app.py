"""Phase 6: Interactive Streamlit Dashboard for the Underwriting OS.
Run locally with: streamlit run app/streamlit_app.py"""
import json
import sqlite3
import sys
from pathlib import Path
import pandas as pd
import streamlit as st

# --- PATHS & DATA LOADING ---
ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "asset_underwriting.db"
OUT = ROOT / "outputs"

# Self-provision data if it hasn't been generated yet
if not DB.exists() or not (OUT / "underwriting_summary.json").exists():
    sys.path.insert(0, str(ROOT / "src" / "data"))
    import generate_dataset
    sys.path.insert(0, str(ROOT / "src" / "analytics"))
    import underwriting_engine
    import report_builder

# Load Engine Outputs
S = json.loads((OUT / "underwriting_summary.json").read_text())
conn = sqlite3.connect(DB)
profile = pd.read_sql("SELECT * FROM asset_profile", conn)
comps   = pd.read_sql("SELECT * FROM market_comps", conn)
phys    = pd.read_sql("SELECT * FROM physical_audit", conn)
stat    = pd.read_sql("SELECT * FROM statutory_compliance", conn)
art     = pd.read_sql("SELECT * FROM artisan_registry", conn)
conn.close()

# --- STREAMLIT UI ---
st.set_page_config(page_title="Asset-Hospitality-Management OS", page_icon="🏛️", layout="wide")

st.title("🏛️ Asset-Hospitality-Management OS")
st.caption("Boutique hospitality expansion decision support | Underwriting, Capex & Statutory Risk Engine")

# Sidebar for Asset Selection
st.sidebar.header("Portfolio Selector")
asset_ids = list(S["assets"].keys())
asset_names = [S["assets"][aid]["name"] for aid in asset_ids]
selected_name = st.sidebar.selectbox("Select Asset to Underwrite:", asset_names)
selected_aid = asset_ids[asset_names.index(selected_name)]

asset_data = S["assets"][selected_aid]
asset_profile_row = profile[profile.asset_id == selected_aid].iloc[0]

# --- TOP METRICS ROW ---
st.markdown("---")
c1, c2, c3, c4, c5 = st.columns(5)

verdict = asset_data["verdict"]
c1.metric("Verdict", verdict.split(" ")[0], delta=("⚠️" if "CONDITIONAL" in verdict else "✅"))
c2.metric(f"NPV @{S['hurdle']:.0%} (Base)", f"₹{asset_data['npv_base']/1e7:+.2f} Cr", 
          f"Levered: ₹{asset_data['npv_levers']/1e7:+.2f} Cr")
c3.metric("Break-even Occ.", f"{asset_data['breakeven_occ']*100:.1f}%", 
          delta=f"Target: {asset_data['target_occupancy']*100:.0f}%", delta_color="normal")
c4.metric("Total Capex (Base)", f"₹{asset_data['capex_base']/1e7:.2f} Cr", 
          f"Levered: ₹{asset_data['capex_levers']/1e7:.2f} Cr")
c5.metric("Licence Critical Path", f"{asset_data['critical_path_days']} days")

st.markdown("---")

def ebitda_cell(v):
    """Design-system heat coloring: no matplotlib required."""
    if v < 0:   return "background-color:#E71D36;color:#FFFFFF"
    if v < 1.0: return "background-color:#FF9F1C;color:#FFFFFF"
    return "background-color:#7CB518;color:#FFFFFF"

def cond_color(v):
    if v == "Critical": return "background-color:#E71D36;color:#FFFFFF"
    if v == "Poor":     return "background-color:#FF9F1C;color:#FFFFFF"
    return ""

def risk_color(v):
    if v in ("CRITICAL", "FAIL"): return "background-color:#E71D36;color:#FFFFFF"
    if v == "HIGH":               return "background-color:#FF9F1C;color:#FFFFFF"
    return ""

# --- TABS ---
t1, t2, t3, t4, t5 = st.tabs([
    "📈 P&L & Sensitivity", 
    "🧱 Capex & Statutory Gate", 
    "🌐 Market & Compset", 
    "🎨 Theming & Artisans", 
    "📄 Dossier & Provenance"
])

with t1:
    pnl = pd.read_csv(OUT / f"pnl_{selected_aid}.csv")
    sens = pd.read_csv(OUT / f"sensitivity_{selected_aid}.csv")
    
    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("9-Year Lease Horizon P&L (₹ Cr)")
        # Convert to Cr for charting
        pnl_cr = pnl.set_index("year")[["gross_revenue", "ebitda", "cash_flow"]] / 1e7
        st.line_chart(pnl_cr)
    with col_r:
        st.subheader("Sensitivity Grid: Y1 EBITDA (₹ Cr)")
        grid = sens.pivot(index="adr", columns="occupancy", values="ebitda_y1") / 1e7
        st.dataframe(grid.style.map(ebitda_cell).format("{:.2f}"), use_container_width=True)

with t2:
    st.subheader("Physical Capex Risk Register")
    p_filt = phys[phys.asset_id == selected_aid][["zone", "element", "condition", "issue", "capex_inr"]]
    st.dataframe(p_filt.style.map(cond_color, subset=["condition"]),
                 use_container_width=True, hide_index=True)                         
    
    st.subheader("Statutory Gate & Dealbreakers")
    s_filt = stat[stat.asset_id == selected_aid][["req", "status", "risk", "cost_inr", "days", "note"]]
    st.dataframe(s_filt.style.map(risk_color, subset=["risk", "status"]),
                 use_container_width=True, hide_index=True)
with t3:
    st.subheader("Compset ADR Trend (24 Months)")
    c_filt = comps[comps.asset_id == selected_aid]
    piv = c_filt.pivot_table(index="month", columns="comp_name", values="adr_inr")
    st.line_chart(piv)
    st.info(f"Direct heritage compset premium: **{asset_data['revpar_premium']*100:+.1f}%**")

with t4:
    st.subheader("AI Theming & Local Artisan Pipeline")
    a_filt = art[art.asset_id == selected_aid]
    st.dataframe(a_filt, use_container_width=True, hide_index=True)

with t5:
    st.subheader("Founder-Grade Dossier")
    dossier_path = OUT / "underwriting_dossier.md"
    if dossier_path.exists():
        st.markdown("Download the complete underwriting dossier (Markdown) to share with the investment committee.")
        with open(dossier_path, "r") as f:
            st.download_button("Download Dossier (.md)", f, file_name=f"{selected_aid}_dossier.md", mime="text/markdown")
    
    st.subheader("Methodology & Provenance")
    st.write("""
    **Module 0 Provenance:** Statutory-gate logic, capex contingency practice, and egress/setback checks 
    are ported from the **SVNIT digital-twin audit engine** (BHI 83.9 governance-capped for a lapsed Fire NOC; 
    IS 1172 norm 135 LPCD vs measured 201; NBC 2016 egress; CPWD Cl. 7.1 guarantee leverage). 
    The hospitality layer adds industry-standard unit economics: RevPAR indexing vs compset, OTA commission load, 
    FF&E reserve, rent escalation, and lease-horizon DCF at the founder hurdle rate.
    """)