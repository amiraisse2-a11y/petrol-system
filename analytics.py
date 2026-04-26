# analytics.py
# Calculs, KPIs et analyses de production

import pandas as pd
from datetime import date, timedelta
from database import lire_production, lire_puits
from config import PRIX_BARIL, TAUX

# ─────────────────────────────────────────
# KPIs JOURNALIERS
# ─────────────────────────────────────────
def kpis_journaliers(date_cible=None):
    if not date_cible:
        date_cible = str(date.today() - timedelta(days=1))

    df = lire_production(date_debut=date_cible, date_fin=date_cible)

    # Si pas de données hier, prendre avant-hier
    if df.empty:
        date_cible = str(date.today() - timedelta(days=2))
        df = lire_production(date_debut=date_cible, date_fin=date_cible)

    if df.empty:
        return {}

    prod_totale = df["production_huile_bbl"].sum()
    revenu_usd  = prod_totale * PRIX_BARIL
    revenu_xof  = revenu_usd * TAUX

    # Lire les statuts depuis la table puits (plus fiable)
    df_puits = lire_puits()
    nb_actifs    = int((df_puits["statut"] == "Actif").sum())    if not df_puits.empty else 0
    nb_alertes   = int((df_puits["statut"] == "Alerte").sum())   if not df_puits.empty else 0
    nb_critiques = int((df_puits["statut"] == "Critique").sum()) if not df_puits.empty else 0

    return {
        "date":                   date_cible,
        "production_totale_bbl":  round(prod_totale, 0),
        "production_gaz_mmscf":   round(df["production_gaz_mmscf"].sum(), 2),
        "water_cut_moyen":        round(df["water_cut"].mean(), 4),
        "pression_moyenne_psi":   round(df["pression_tete_psi"].mean(), 1),
        "nb_puits_actifs":        nb_actifs,
        "nb_puits_alerte":        nb_alertes,
        "nb_puits_critiques":     nb_critiques,
        "revenu_journalier_usd":  round(revenu_usd, 0),
        "revenu_journalier_xof":  round(revenu_xof, 0),
    }

# ─────────────────────────────────────────
# PRODUCTION PAR CHAMP
# ─────────────────────────────────────────
def production_par_champ(periode_jours=30):
    date_fin   = date.today()
    date_debut = date_fin - timedelta(days=periode_jours)

    df = lire_production(
        date_debut=str(date_debut),
        date_fin=str(date_fin)
    )

    if df.empty:
        return pd.DataFrame()

    rapport = df.groupby("champ").agg(
        Production_Totale  =("production_huile_bbl", "sum"),
        Production_Moyenne =("production_huile_bbl", "mean"),
        WaterCut_Moyen     =("water_cut", "mean"),
        GOR_Moyen          =("gor", "mean"),
        Pression_Moyenne   =("pression_tete_psi", "mean"),
        Nb_Jours           =("date", "nunique")
    ).reset_index()

    rapport["Revenu_USD"]  = rapport["Production_Totale"] * PRIX_BARIL
    rapport["Revenu_FCFA"] = rapport["Revenu_USD"] * TAUX

    return rapport.sort_values("Production_Totale", ascending=False)

# ─────────────────────────────────────────
# DÉCLIN D'UN PUITS
# ─────────────────────────────────────────
def calculer_declin(puits_nom, periode_jours=90):
    date_fin   = date.today()
    date_debut = date_fin - timedelta(days=periode_jours)

    df = lire_production(
        date_debut=str(date_debut),
        date_fin=str(date_fin),
        puits=puits_nom
    )

    if df.empty or len(df) < 2:
        return None

    df = df.sort_values("date")
    prod_debut = float(df.iloc[0]["production_huile_bbl"])
    prod_fin   = float(df.iloc[-1]["production_huile_bbl"])

    if prod_debut == 0:
        return None

    declin_total   = (prod_debut - prod_fin) / prod_debut
    declin_mensuel = declin_total / max(periode_jours / 30, 1)

    return {
        "puits":               puits_nom,
        "production_debut":    round(prod_debut, 0),
        "production_actuelle": round(prod_fin, 0),
        "declin_total_pct":    round(declin_total * 100, 2),
        "declin_mensuel_pct":  round(declin_mensuel * 100, 2),
        "periode_jours":       periode_jours,
    }

# ─────────────────────────────────────────
# HISTORIQUE PAR CHAMP (courbes)
# ─────────────────────────────────────────
def historique_champs(periode_jours=90):
    date_fin   = date.today()
    date_debut = date_fin - timedelta(days=periode_jours)

    df = lire_production(
        date_debut=str(date_debut),
        date_fin=str(date_fin)
    )

    if df.empty:
        return pd.DataFrame()

    return (
        df.groupby(["date", "champ"])["production_huile_bbl"]
        .sum()
        .reset_index()
        .sort_values("date")
    )
