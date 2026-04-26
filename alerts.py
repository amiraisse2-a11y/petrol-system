# alerts.py
# Système de détection et gestion des alertes

from datetime import date, timedelta
from database import lire_production, sauvegarder_alerte, lire_alertes
from config import SEUILS

# ─────────────────────────────────────────
# VÉRIFIER TOUTES LES ALERTES
# ─────────────────────────────────────────
def verifier_alertes():
    hier = str(date.today() - timedelta(days=1))
    df   = lire_production(date_debut=hier, date_fin=hier)

    if df.empty:
        return []

    alertes_generees = []

    for _, row in df.iterrows():
        puits = row["puits"]
        champ = row["champ"]
        wc    = float(row["water_cut"])
        prod  = float(row["production_huile_bbl"])
        press = float(row["pression_tete_psi"])

        # ── Water cut critique ──
        if wc > SEUILS["water_cut_critique"]:
            msg = (f"Water cut {wc:.1%} dépasse le seuil "
                   f"critique {SEUILS['water_cut_critique']:.0%}")
            sauvegarder_alerte(puits, champ, "Water Cut Critique",
                               "CRITIQUE", wc,
                               SEUILS["water_cut_critique"], msg)
            alertes_generees.append({"puits": puits, "niveau": "CRITIQUE", "message": msg})

        elif wc > SEUILS["water_cut_alerte"]:
            msg = (f"Water cut {wc:.1%} au-dessus du seuil "
                   f"{SEUILS['water_cut_alerte']:.0%}")
            sauvegarder_alerte(puits, champ, "Water Cut Élevé",
                               "ALERTE", wc,
                               SEUILS["water_cut_alerte"], msg)
            alertes_generees.append({"puits": puits, "niveau": "ALERTE", "message": msg})

        # ── Production faible ──
        if prod < SEUILS["production_min_bbl"]:
            msg = (f"Production {prod:,.0f} bbl/j sous le minimum "
                   f"{SEUILS['production_min_bbl']:,} bbl/j")
            sauvegarder_alerte(puits, champ, "Production Faible",
                               "ALERTE", prod,
                               SEUILS["production_min_bbl"], msg)
            alertes_generees.append({"puits": puits, "niveau": "ALERTE", "message": msg})

        # ── Pression basse ──
        if press < SEUILS["pression_min_psi"]:
            msg = (f"Pression tête {press:.0f} psi sous le minimum "
                   f"{SEUILS['pression_min_psi']} psi")
            sauvegarder_alerte(puits, champ, "Pression Basse",
                               "CRITIQUE", press,
                               SEUILS["pression_min_psi"], msg)
            alertes_generees.append({"puits": puits, "niveau": "CRITIQUE", "message": msg})

    return alertes_generees


# ─────────────────────────────────────────
# RÉSUMER LES ALERTES ACTIVES
# ─────────────────────────────────────────
def resume_alertes():
    df = lire_alertes(resolues=False)
    if df.empty:
        return {"total": 0, "critiques": 0, "alertes": 0}
    return {
        "total":    len(df),
        "critiques": int((df["niveau"] == "CRITIQUE").sum()),
        "alertes":   int((df["niveau"] == "ALERTE").sum()),
    }
