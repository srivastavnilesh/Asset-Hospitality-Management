# 🏛️ Asset-Hospitality-Management
**Acquisition & Underwriting OS for boutique hospitality assets — screen fast, underwrite deep.**

[![Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](STREAMLIT_URL_PLACEHOLDER)
[![Tests](https://img.shields.io/badge/tests-5%20passed-brightgreen)](tests/test_engine.py)

Seeded two-asset portfolio (Hyderabad heritage haveli + Goa Portuguese villa) run through a
four-stage engine: compset market indexing → physical Capex audit → statutory dealbreaker gate →
lease-horizon DCF (NPV/IRR vs 12% hurdle, break-even occupancy, sensitivity grid, Go/No-Go verdict).

## Live demos
- **Product (interactive):** STREAMLIT_URL_PLACEHOLDER
- **Executive visualisation (Tableau):** TABLEAU_URL_PLACEHOLDER

## Quickstart
pip install -r requirements.txt
python src/data/generate_dataset.py
python src/analytics/underwriting_engine.py
python src/analytics/report_builder.py
python src/analytics/tableau_export.py
pytest -q
streamlit run app/streamlit_app.py

## Architecture
graph TD
    A[Seeded portfolio generator] --> B[(SQLite + CSVs)]
    B --> C[Underwriting engine: NPV/IRR, break-even, sensitivity, verdict]
    C --> D[Founder dossier .md]
    C --> E[Tableau-ready exports]
    C --> F[Streamlit decision dashboard]
    G[pytest invariants x5] --> C

## Provenance (Module 0)
Statutory-gate logic, Capex contingency practice and egress/setback checks are ported from the
SVNIT digital-twin audit engine (BHI 83.9 governance-capped for a lapsed Fire NOC; IS 1172 norm
135 LPCD vs measured 201; NBC 2016 egress; CPWD Cl. 7.1 guarantee leverage).