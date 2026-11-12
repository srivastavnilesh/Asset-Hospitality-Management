"""Single source of truth: Project Asaf Jah underwriting assumptions.
Provenance: audit methodology ported from SVNIT digital-twin engine
(IS 1172 water norms, NBC 2016 egress, CPWD Cl.7.1 guarantee leverage)."""
from dataclasses import dataclass

@dataclass(frozen=True)
class AssetConfig:
    asset_id: str = "HYD-OLD-001"
    name: str = "The Asaf Jah Haveli"
    location: str = "Purani Haveli, Old City, Hyderabad"
    built_year: int = 1904
    total_sqft: float = 8500.0
    keys: int = 15                      # guest rooms
    lease_years: int = 9                # leasehold, not freehold
    monthly_rent_y1: float = 450_000.0
    rent_escalation: float = 0.05       # 5% yearly escalation (market standard)
    heritage_grade: str = "Grade IIB"
    setback_ft: float = 8.0             # actual street setback
    fire_tender_setback_req_ft: float = 15.0   # Telangana Fire NOC requirement

@dataclass(frozen=True)
class MarketConfig:
    target_adr: float = 8500.0          # positioned above Rs 7,200 compset
    target_occupancy: float = 0.70
    fnb_attach: float = 0.25            # F&B revenue = 25% of room revenue
    ota_commission: float = 0.18        # MMT/Booking/Airbnb blended commission
    revpar_growth: float = 0.06

@dataclass(frozen=True)
class OpexConfig:
    payroll_ops_y1: float = 12_500_000.0   # 15-key boutique staffing + utilities
    opex_inflation: float = 0.06
    ff_e_reserve_pct_revenue: float = 0.04 # industry-standard FF&E reserve

@dataclass(frozen=True)
class CapitalConfig:
    contingency_pct: float = 0.10          # heritage retrofit contingency
    design_consultant: float = 4_500_000.0
    pre_opening: float = 6_000_000.0
    working_capital: float = 10_000_000.0  # recovered at lease end
    subsidy_pct_hard: float = 0.15         # Telangana tourism capex subsidy (lever)
    rent_free_months_lever: int = 6        # negotiation lever
    adr_lever: float = 9200.0              # theming-driven pricing lever
    occ_lever: float = 0.72
    discount_rate: float = 0.12            # founder hurdle rate

ASSET, MARKET, OPEX, CAPITAL = AssetConfig(), MarketConfig(), OpexConfig(), CapitalConfig()