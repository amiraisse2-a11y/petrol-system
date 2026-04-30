"""
PETRO AFRICA — Configuration Centrale
Mise à jour : ajout PRIX_GAZ_MMSCFD + constantes gaz Afrique de l'Ouest
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ─── Supabase ────────────────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# ─── Application ─────────────────────────────────────────────────────────────
APP_NAME    = "PETRO AFRICA"
APP_VERSION = "2.1.0"
APP_LOGO    = "🛢️"

# ─── Unités par défaut ───────────────────────────────────────────────────────
UNITE_DEBIT    = "BOPD"    # Barils par jour
UNITE_GPI      = "MMscfd"  # Millions de pieds cubes par jour
UNITE_PRESSION = "psi"
UNITE_TEMP     = "°C"

# ─── PRIX & RÉFÉRENCES MARCHÉ ────────────────────────────────────────────────

# Huile — référence Brent/Dated
PRIX_BARIL = 75.0          # USD/bbl  (Brent spot, mise à jour manuelle recommandée)

# Gaz — référence Afrique de l'Ouest
# Sources : NLNG (Nigeria), GTA (Sénégal/Mauritanie), Foxtrot/Sankofa (CI)
# Fourchette typique : 3.5–6.0 USD/MMBtu selon contrat et destination
PRIX_GAZ_MMBTU    = 4.5    # USD/MMBtu  ← NOUVEAU — tarif moyen contrats AOG
PRIX_GAZ_MMSCFD   = 4.5    # Alias explicite pour la facturation par MMscfd/j
                             # (1 MMscfd ≈ 1 000 MMBtu/j en conditions standard)

# Conversion énergétique gaz → BOE
# 1 BOE ≈ 5.8 MMBtu  (API/SPE standard)
GAZ_MMBTU_PAR_BOE = 5.8

# Condensat (si champ gaz à condensat)
PRIX_CONDENSAT = 72.0       # USD/bbl  (rabais ~3–5 $/bbl vs Brent)

# ─── PARAMÈTRES FISCAUX CÔTE D'IVOIRE (Code Pétrolier 1996, amendé 2012) ───
ROYALTIES_HUILE_PCT = 12.5  # % sur revenus bruts huile
ROYALTIES_GAZ_PCT   = 8.0   # % sur revenus bruts gaz
IMPOT_SOCIETES_PCT  = 30.0  # % (taux standard Côte d'Ivoire)
PROFIT_OIL_SPLIT    = 0.60  # Part état sur profit oil (contrat de partage type)

# ─── PARAMÈTRES PRODUCTION ───────────────────────────────────────────────────
DECLINE_RATE_DEFAULT = 10.0   # % annuel (déclin exponentiel)
WATER_CUT_DEFAULT    = 0.20   # fraction (20%)
GOR_DEFAULT          = 500.0  # scf/bbl (Gas-Oil Ratio)

# ─── ESG / FLARING ───────────────────────────────────────────────────────────
# Facteurs d'émission IPCC/GIE
CO2_PAR_TONNE_GAZ_TORCHE  = 2.75   # tCO2/t gaz brûlé
GAZ_DENSITÉ_KG_M3          = 0.75   # kg/m³ (gaz naturel moyen)
METHANE_GWP100             = 28.0   # Global Warming Potential CH4 (GIEC AR6)
FLARING_FRACTION_DEFAULT   = 0.05   # 5% de la production gaz torchée (benchmark CI)

# Réglementation PETROCI : objectif zéro torchage systématique d'ici 2030
PETROCI_FLARING_TARGET_PCT = 2.0   # % cible max flaring 2030

# ─── WACC / FINANCE ──────────────────────────────────────────────────────────
WACC_DEFAULT    = 12.0   # % (risque pays CI inclus)
WACC_LOW_RISK   = 10.0   # % (opérateur majeur, financement BEI/IFC)
WACC_HIGH_RISK  = 18.0   # % (exploration early-stage)

# ─── CHAMPS RÉFÉRENCE CÔTE D'IVOIRE ─────────────────────────────────────────
CHAMPS = {
    "Baleine":  {"type": "huile",    "operateur": "ENI/PETROCI", "debut": 2023},
    "Sankofa":  {"type": "gaz",      "operateur": "ENI/PETROCI", "debut": 2017},
    "Foxtrot":  {"type": "gaz",      "operateur": "FOXTROT Int.","debut": 1999},
    "Espoir":   {"type": "huile/gaz","operateur": "CNR Int.",    "debut": 2002},
    "Baobab":   {"type": "huile",    "operateur": "CNR Int.",    "debut": 2005},
}

# ─── ALERTES & SEUILS ────────────────────────────────────────────────────────
SEUIL_ALERTE_WATERCUT   = 0.80   # 80% — seuil critique
SEUIL_ALERTE_GOR        = 2000   # scf/bbl — gas coning potentiel
SEUIL_ALERTE_DECLINE    = 20.0   # %/an — déclin accéléré anormal
SEUIL_FLARING_ALERTE    = 0.10   # 10% — alerte réglementaire

# ─── RAPPORT ─────────────────────────────────────────────────────────────────
RAPPORT_LOGO_PATH   = "assets/logo_petro_africa.png"
RAPPORT_FOOTER      = "PETRO AFRICA Dashboard — Confidentiel"
RAPPORT_AUTEUR      = "PETRO AFRICA Analytics Platform"
EXCEL_COULEUR_HEADER = "1B4F72"   # Bleu pétrole (hex sans #)
EXCEL_COULEUR_ACCENT = "F39C12"   # Or/orange
