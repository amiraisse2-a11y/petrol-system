# data_generator.py
# Génère les données et les envoie dans Supabase OU SQLite

import numpy as np
import sqlite3
from datetime import date, timedelta
from config import PROFILS_PUITS

DB_PATH = "petroci.db"

def generer_production_historique(nb_jours=365):
    """
    Génère les données de production.
    Si Supabase est connecté et vide → envoie dans Supabase.
    Sinon → SQLite local.
    """
    from database import (utiliser_supabase, supabase_a_donnees,
                           inserer_production_supabase)

    # Vérifier si Supabase a déjà des données
    if utiliser_supabase() and supabase_a_donnees():
        return  # Données déjà dans Supabase — ne rien faire

    # Vérifier si SQLite a déjà des données
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c    = conn.cursor()
    c.execute("SELECT COUNT(*) FROM production_journaliere")
    count_sqlite = c.fetchone()[0]

    if count_sqlite > 100 and not utiliser_supabase():
        conn.close()
        return  # SQLite déjà peuplé

    np.random.seed(42)

    date_fin   = date.today() - timedelta(days=1)
    date_debut = date_fin - timedelta(days=nb_jours - 1)

    donnees_sqlite   = []
    donnees_supabase = []
    date_cur = date_debut

    while date_cur <= date_fin:
        j = (date_cur - date_debut).days

        for nom, p in PROFILS_PUITS.items():
            champ   = p["champ"]
            facteur = np.exp(-p["declin"] * j)
            bruit   = np.random.uniform(0.95, 1.05)
            prod    = max(0.0, round(p["prod_base"] * facteur * bruit, 0))

            arret  = np.random.random() < 0.03
            heures = 0.0 if arret else 24.0
            if arret:
                prod = 0.0

            wc       = min(p["wc_base"] + 0.00015*j + np.random.normal(0, 0.008), 0.97)
            wc       = round(max(0.0, wc), 4)
            prod_eau = round(prod * wc / max(1-wc, 0.01), 0)
            gor_val  = round(p["pression_base"] * 1.5 * (1+0.15*(1-facteur)) + np.random.normal(0, 30), 0)
            prod_gaz = round(prod * gor_val / 1000, 3)
            pression = round(max(p["pression_base"] * facteur * np.random.uniform(0.97, 1.03), 100), 1)
            temp     = round(np.random.normal(178, 5), 1)

            if arret:
                statut = "Arret"
            elif wc > 0.70 or prod < 500:
                statut = "Critique"
            elif wc > 0.55 or prod < 1500:
                statut = "Alerte"
            else:
                statut = "Actif"

            donnees_sqlite.append((
                str(date_cur), nom, champ,
                prod, prod_gaz, prod_eau,
                wc, gor_val, pression, temp,
                heures, statut
            ))

            donnees_supabase.append({
                "date":                 str(date_cur),
                "puits":                nom,
                "champ":                champ,
                "production_huile_bbl": float(prod),
                "production_gaz_mmscf": float(prod_gaz),
                "production_eau_bbl":   float(prod_eau),
                "water_cut":            float(wc),
                "gor":                  float(gor_val),
                "pression_tete_psi":    float(pression),
                "temperature_f":        float(temp),
                "heures_production":    float(heures),
                "statut":               statut,
            })

        date_cur += timedelta(days=1)

    # Insérer dans SQLite
    c.executemany("""
        INSERT OR IGNORE INTO production_journaliere
        (date,puits,champ,
         production_huile_bbl,production_gaz_mmscf,
         production_eau_bbl,water_cut,gor,
         pression_tete_psi,temperature_f,
         heures_production,statut)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, donnees_sqlite)
    conn.commit()
    conn.close()

    # Envoyer dans Supabase si connecté
    if utiliser_supabase():
        ok = inserer_production_supabase(donnees_supabase)
        if ok:
            print(f"Supabase : {len(donnees_supabase)} enregistrements inseres")
        else:
            print("Supabase : echec insertion — donnees dans SQLite uniquement")
    else:
        print(f"SQLite : {len(donnees_sqlite)} enregistrements inseres")
