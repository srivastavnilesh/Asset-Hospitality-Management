"""Seeded synthetic portfolio for Asset-Hospitality-Management OS.
Case studies: HYD-OLD-001 (heritage haveli) + GOA-VIL-002 (Portuguese villa).
Runs at import so Streamlit Cloud can self-provision data."""
import sqlite3
import numpy as np
import pandas as pd
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from config import ASSET, MARKET  # primary-asset economics live in config.py

DB = ROOT / "data" / "asset_underwriting.db"; DB.parent.mkdir(parents=True, exist_ok=True)
CSV = ROOT / "data" / "csv"; CSV.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(42)

MONTHS = pd.period_range("2025-01", periods=24, freq="M").astype(str)
SEASON = {  # monthly demand factors: Hyderabad winter-peak vs Goa monsoon-trough
    "HYD-OLD-001": {1:1.18,2:1.15,3:1.05,4:0.88,5:0.82,6:0.85,7:0.90,8:0.92,9:0.95,10:1.05,11:1.12,12:1.20},
    "GOA-VIL-002": {1:1.30,2:1.10,3:0.95,4:0.90,5:0.75,6:0.60,7:0.65,8:0.70,9:0.85,10:1.00,11:1.15,12:1.35},
}
PHASES = [("P0 Statutory & design","M1-M4",0.12), ("P1 Structural & facade","M3-M7",0.28),
          ("P2 MEP & plumbing","M5-M9",0.22), ("P3 Interiors & FF&E","M8-M12",0.30),
          ("P4 Pre-opening & soft launch","M11-M13",0.08)]

HYD_PHYSICAL = [
    ("Main Courtyard","Timber roof trusses","Critical","Termite damage ~30% beams",8_500_000,True),
    ("Guest Wings","Plumbing (15 en-suites)","Poor","Legacy lead pipes; full re-pipe",4_800_000,False),
    ("Facade","Lime plaster & jharokhas","Fair","Heritage-certified restoration",6_200_000,True),
    ("Electrical","LT panel 30kW->90kW","Critical","AC + kitchen load upgrade",3_800_000,False),
    ("Interiors","FF&E bespoke Nizam-era","N/A","Thematic sourcing via local artisans",29_500_000,True),
    ("MEP","HVAC, kitchen, laundry","N/A","New installation",11_000_000,False)]
GOA_PHYSICAL = [
    ("Roof","Mangalore tiles + timber rafters","Critical","Monsoon ingress; rafter rot",7_500_000,True),
    ("Guest Wings","Plumbing (12 en-suites)","Fair","Partial re-pipe + pressure boosting",3_200_000,False),
    ("Facade","Ochre plaster & azulejos panels","Fair","Conservation-grade repaint",4_800_000,True),
    ("Electrical","LT panel 25kW->70kW","Poor","AC + kitchen load upgrade",2_600_000,False),
    ("Interiors","FF&E Indo-Portuguese","N/A","Antique sourcing via local dealers",18_000_000,True),
    ("MEP","HVAC, kitchen, laundry","N/A","New installation",7_500_000,False)]
HYD_STAT = [
    ("GHMC change of land use (res->comm)","Pending","HIGH",350_000,90,False,""),
    ("Telangana Fire NOC","FAIL","CRITICAL",1_800_000,45,True,
     "Setback 8ft vs 15ft tender access; external cantilevered steel egress + waiver required"),
    ("Heritage Conservation Committee","Approved","LOW",50_000,30,False,""),
    ("FSSAI central kitchen","Not started","MEDIUM",25_000,20,False,"")]
GOA_STAT = [
    ("TCP change of use (res->commercial)","Pending","HIGH",300_000,75,False,""),
    ("Goa Fire NOC","Pending","MEDIUM",400_000,40,False,""),
    ("IPCHC facade consent (Portuguese-era)","Pending","HIGH",200_000,60,False,
     "Alteration restrictions on azulejos & balcao"),
    ("FSSAI central kitchen","Not started","MEDIUM",25_000,20,False,"")]
HYD_ART = [("Bidriware inlay","Kothi outreach cell",6.2,3), ("Kalamkari textiles","Dabirpura weavers co-op",4.8,5),
           ("Zari & Paithani borders","Charminar zari guild",2.1,4), ("Lime plaster (chuna) work","HCC-empanelled masons",9.5,2),
           ("Teak restoration","Gowliguda carpentry lane",3.4,6), ("Deccan mural art","Hyderabad art collective",7.7,4)]
GOA_ART = [("Azulejos tile restoration","Fontainhas conservation cell",1.2,2),
           ("Mother-of-pearl shell windows","Santo Tome artisans",2.6,3),
           ("Cane & bamboo furniture","Goa cane co-op",8.4,4), ("Terracotta & pottery","Bicholim pottery cluster",21.0,3)]

ASSETS = [
    dict(asset_id=ASSET.asset_id, name=ASSET.name, location=ASSET.location, built_year=ASSET.built_year,
         total_sqft=ASSET.total_sqft, keys=ASSET.keys, lease_years=ASSET.lease_years,
         monthly_rent_y1=ASSET.monthly_rent_y1, heritage_grade=ASSET.heritage_grade,
         setback_ft=ASSET.setback_ft, fire_req_ft=ASSET.fire_tender_setback_req_ft,
         target_adr=MARKET.target_adr, target_occupancy=MARKET.target_occupancy,
         comps=[("C1","Taj Falaknuma (luxury proxy)",18500,0.78), ("C2","Boutique Haveli Charminar",7200,0.65),
                ("C3","Premium Airbnb Old City",4500,0.58)],
         physical=HYD_PHYSICAL, statutory=HYD_STAT, artisans=HYD_ART),
    dict(asset_id="GOA-VIL-002", name="Casa Fontainhas", location="Fontainhas, Panaji, Goa",
         built_year=1892, total_sqft=6200.0, keys=12, lease_years=9, monthly_rent_y1=380_000.0,
         heritage_grade="Goa Heritage (Portuguese-era)", setback_ft=12.0, fire_req_ft=12.0,
         target_adr=7800.0, target_occupancy=0.68,
         comps=[("C1","Taj Fort Aguada (luxury proxy)",16500,0.74), ("C2","Heritage boutique Panaji",6800,0.62),
                ("C3","Premium Airbnb Fontainhas",4200,0.55)],
         physical=GOA_PHYSICAL, statutory=GOA_STAT, artisans=GOA_ART),
]

profile, comps, phys, stat, phases, arts = [], [], [], [], [], []
for a in ASSETS:
    profile.append({k: a[k] for k in ("asset_id","name","location","built_year","total_sqft","keys",
        "lease_years","monthly_rent_y1","heritage_grade","setback_ft","fire_req_ft","target_adr","target_occupancy")})
    for cid, cname, adr, occ in a["comps"]:
        for m in MONTHS:
            f = SEASON[a["asset_id"]][int(m[5:7])]
            comps.append(dict(asset_id=a["asset_id"], comp_id=cid, comp_name=cname, month=m,
                              adr_inr=int(adr*f*rng.normal(1,0.03)),
                              occupancy_pct=round(min(97.0, occ*f*100*rng.normal(1,0.02)), 1)))
    for zone, element, cond, issue, capex, cert in a["physical"]:
        phys.append(dict(asset_id=a["asset_id"], zone=zone, element=element, condition=cond,
                         issue=issue, capex_inr=capex, heritage_certified=cert))
    for req, status, risk, cost, days, dbk, note in a["statutory"]:
        stat.append(dict(asset_id=a["asset_id"], req=req, status=status, risk=risk,
                         cost_inr=cost, days=days, dealbreaker=dbk, note=note))
    for ph, mo, pct in PHASES:
        phases.append(dict(asset_id=a["asset_id"], phase=ph, months=mo, spend_pct=pct))
    for craft, cluster, dist, partners in a["artisans"]:
        arts.append(dict(asset_id=a["asset_id"], craft=craft, cluster=cluster,
                         distance_km=dist, partners=partners))

tables = {"asset_profile": pd.DataFrame(profile), "market_comps": pd.DataFrame(comps),
          "physical_audit": pd.DataFrame(phys), "statutory_compliance": pd.DataFrame(stat),
          "capex_phases": pd.DataFrame(phases), "artisan_registry": pd.DataFrame(arts)}

conn = sqlite3.connect(DB)
for name, df in tables.items():
    df.to_sql(name, conn, if_exists="replace", index=False)
    df.to_csv(CSV / f"{name}.csv", index=False)
conn.close()

print("=" * 70)
print("ASSET-HOSPITALITY-MANAGEMENT | SEEDED PORTFOLIO MANIFEST")
print("=" * 70)
for name, df in tables.items():
    print(f"  {name:<22} {len(df):>4} rows")
print("\nCompset means (ADR Rs / occ %):")
print(tables["market_comps"].groupby("asset_id")[["adr_inr","occupancy_pct"]].mean().round(1))
print("\nHard capex per asset (Rs Cr):")
print((tables["physical_audit"].groupby("asset_id").capex_inr.sum() / 1e7).round(2))
print(f"\n[data] DB -> {DB} | CSVs -> {CSV}")