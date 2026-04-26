# data_generator.py
# Génère 365 jours de données de production simulées

import numpy as np
import sqlite3
from datetime import date, timedelta
from config import PROFILS_PUITS

DB_PATH = "petroci.db"

def generer_production_historique(nb_jours=365):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()

    # Vérifier si déjà peuplé
    c.execute("SELECT COUNT(*) FROM production_journaliere")
    if c.fetchone()[0] > 100:
        conn.close()
        return

    date_fin   = date.today()
    date_debut = date_fin - timedelta(days=nb_jours)
    donnees    = []
    date_cur   = date_debut

    while date_cur <= date_fin:
        j = (date_cur - date_debut).days
        for nom, p in PROFILS_PUITS.items():
            champ = p["champ"]

            # Déclin exponentiel
            facteur = np.exp(-p["declin"] * j)
            variation = np.random.uniform(0.95, 1.05)
            prod_huile = p["prod_base"] * facteur * variation

            # Water cut croissant
            wc = min(p["wc_base"] + 0.0002 * j, 0.95)
            prod_eau = prod_huile * wc / max(1 - wc, 0.01)

            # Gaz
            gor = np.random.uniform(700, 1000)
            prod_gaz = prod_huile * gor / 1000

            # Pression
            pression = max(p["pression_base"] - 0.05 * j, 150)

            # Température
            temp = np.random.uniform(165, 195)

            # Heures
            heures = float(np.random.choice(
                [24, 24, 24, 20, 18],
                p=[0.85, 0.05, 0.05, 0.03, 0.02]
            ))

            # Statut
            if wc > 0.65 or prod_huile < 2000:
                statut = "Critique"
            elif wc > 0.50 or prod_huile < 3500:
                statut = "Alerte"
            else:
                statut = "Actif"

            donnees.append((
                str(date_cur), nom, champ,
                round(prod_huile, 0),
                round(prod_gaz, 3),
                round(prod_eau, 0),
                round(wc, 4),
                round(gor, 0),
                round(pression, 1),
                round(temp, 1),
                heures, statut
            ))

        date_cur += timedelta(days=1)

    c.executemany("""
        INSERT OR IGNORE INTO production_journaliere
        (date, puits, champ,
         production_huile_bbl, production_gaz_mmscf, production_eau_bbl,
         water_cut, gor, pression_tete_psi,
         temperature_f, heures_production, statut)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, donnees)

    conn.commit()
    conn.close()
    print(f"✅ {len(donnees)} enregistrements générés")
