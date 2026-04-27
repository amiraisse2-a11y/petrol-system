# database.py
# Connexion Supabase (PostgreSQL cloud) + SQLite fallback
# VERSION FINALE — écriture automatique dans Supabase

import pandas as pd
import sqlite3
import streamlit as st
from datetime import date, timedelta
from config import PROFILS_PUITS

DB_PATH = "petroci.db"

# ─────────────────────────────────────────
# DÉTECTION SUPABASE
# ─────────────────────────────────────────
def utiliser_supabase():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return bool(url and key and url.startswith("https://"))
    except Exception:
        return False

def get_supabase():
    from supabase import create_client
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

# ─────────────────────────────────────────
# SQLITE — CONNEXION ET INIT
# ─────────────────────────────────────────
def get_sqlite():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def initialiser_sqlite():
    conn = get_sqlite()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS puits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom_puits TEXT UNIQUE NOT NULL,
            champ TEXT, operateur TEXT,
            type_puits TEXT DEFAULT 'Producteur',
            latitude REAL, longitude REAL,
            profondeur_totale_m REAL,
            date_forage TEXT,
            statut TEXT DEFAULT 'Actif'
        )""")
    c.execute("""
        CREATE TABLE IF NOT EXISTS production_journaliere (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL, puits TEXT, champ TEXT,
            production_huile_bbl REAL DEFAULT 0,
            production_gaz_mmscf REAL DEFAULT 0,
            production_eau_bbl REAL DEFAULT 0,
            water_cut REAL DEFAULT 0,
            gor REAL DEFAULT 0,
            pression_tete_psi REAL DEFAULT 0,
            temperature_f REAL DEFAULT 0,
            heures_production REAL DEFAULT 24,
            statut TEXT DEFAULT 'Actif'
        )""")
    c.execute("""
        CREATE TABLE IF NOT EXISTS alertes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_alerte TEXT DEFAULT (datetime('now')),
            puits TEXT, champ TEXT,
            type_alerte TEXT, niveau TEXT,
            valeur_actuelle REAL, seuil REAL,
            message TEXT, resolue INTEGER DEFAULT 0
        )""")
    conn.commit()
    conn.close()

# ─────────────────────────────────────────
# PEUPLER PUITS — SQLite + Supabase
# ─────────────────────────────────────────
def peupler_puits():
    operateurs = {
        "Baleine":"ENI / PETROCI",
        "Sankofa":"TotalEnergies / PETROCI",
        "Foxtrot":"TotalEnergies / PETROCI",
        "Baobab":"CNR International / PETROCI",
        "Lion":"TotalEnergies / PETROCI",
        "Panthere":"TotalEnergies / PETROCI",
    }
    dates_forage = {
        "Baleine-A":"2022-03-15","Baleine-B":"2022-07-20",
        "Baleine-C":"2023-01-10","Sankofa-1":"2016-04-12",
        "Sankofa-2":"2016-09-08","Sankofa-3":"2017-02-22",
        "Foxtrot-1":"1997-08-10","Foxtrot-2":"1998-03-25",
        "Baobab-1":"2004-05-18","Baobab-2":"2004-11-30",
        "Baobab-3W":"2006-07-14","Lion-1":"1993-02-08",
        "Panthere-1":"1994-06-20",
    }

    # SQLite
    conn = get_sqlite()
    c = conn.cursor()
    for nom, p in PROFILS_PUITS.items():
        wc = p["wc_base"]
        statut = ("Critique" if wc > 0.70 else
                  "Alerte"   if wc > 0.55 else
                  "Fin de vie" if p["prod_base"] < 800 else "Actif")
        c.execute("""
            INSERT OR IGNORE INTO puits
            (nom_puits,champ,operateur,type_puits,
             latitude,longitude,profondeur_totale_m,
             date_forage,statut)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (nom, p["champ"],
              operateurs.get(p["champ"],"PETROCI"),
              p.get("type","Producteur"),
              p["lat"], p["lon"],
              p.get("profondeur_m", 0),
              dates_forage.get(nom,""),
              statut))
    conn.commit()
    conn.close()

    # Supabase — vérifier si puits existent déjà
    if utiliser_supabase():
        try:
            sb   = get_supabase()
            data = sb.table("puits").select("nom_puits").execute().data
            noms_existants = {r["nom_puits"] for r in data} if data else set()

            puits_a_inserer = []
            for nom, p in PROFILS_PUITS.items():
                if nom in noms_existants:
                    continue
                wc = p["wc_base"]
                statut = ("Critique" if wc > 0.70 else
                          "Alerte"   if wc > 0.55 else
                          "Fin de vie" if p["prod_base"] < 800 else "Actif")
                puits_a_inserer.append({
                    "nom_puits":            nom,
                    "champ":                p["champ"],
                    "operateur":            operateurs.get(p["champ"],"PETROCI"),
                    "type_puits":           p.get("type","Producteur"),
                    "latitude":             p["lat"],
                    "longitude":            p["lon"],
                    "profondeur_totale_m":  p.get("profondeur_m", 0),
                    "date_forage":          dates_forage.get(nom,""),
                    "statut":               statut,
                })

            if puits_a_inserer:
                sb.table("puits").insert(puits_a_inserer).execute()
        except Exception:
            pass

# ─────────────────────────────────────────
# VÉRIFIER SI PRODUCTION DÉJÀ DANS SUPABASE
# ─────────────────────────────────────────
def supabase_a_donnees():
    """Vérifie si Supabase contient déjà des données de production"""
    if not utiliser_supabase():
        return False
    try:
        sb   = get_supabase()
        data = sb.table("production_journaliere").select("id").limit(1).execute().data
        return bool(data)
    except Exception:
        return False

# ─────────────────────────────────────────
# INSÉRER DONNÉES PRODUCTION DANS SUPABASE
# ─────────────────────────────────────────
def inserer_production_supabase(donnees_liste):
    """
    donnees_liste : liste de dicts avec les champs de production
    Insère par batch de 50 pour éviter les timeouts
    """
    if not utiliser_supabase():
        return False
    try:
        sb         = get_supabase()
        batch_size = 50
        for i in range(0, len(donnees_liste), batch_size):
            batch = donnees_liste[i:i+batch_size]
            sb.table("production_journaliere").insert(batch).execute()
        return True
    except Exception as e:
        return False

# ─────────────────────────────────────────
# LIRE PUITS
# ─────────────────────────────────────────
def lire_puits(champ=None, statut=None):
    try:
        if utiliser_supabase():
            sb = get_supabase()
            q  = sb.table("puits").select("*")
            if champ:  q = q.eq("champ", champ)
            if statut: q = q.eq("statut", statut)
            data = q.execute().data
            return pd.DataFrame(data) if data else pd.DataFrame()
    except Exception:
        pass
    # Fallback SQLite
    try:
        conn = get_sqlite()
        sql  = "SELECT * FROM puits WHERE 1=1"
        if champ:  sql += f" AND champ='{champ}'"
        if statut: sql += f" AND statut='{statut}'"
        df   = pd.read_sql_query(sql, conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

# ─────────────────────────────────────────
# LIRE PRODUCTION
# ─────────────────────────────────────────
def lire_production(date_debut=None, date_fin=None,
                    champ=None, puits=None):
    try:
        if utiliser_supabase():
            sb = get_supabase()
            q  = sb.table("production_journaliere").select("*")
            if date_debut: q = q.gte("date", str(date_debut))
            if date_fin:   q = q.lte("date", str(date_fin))
            if champ:      q = q.eq("champ", champ)
            if puits:      q = q.eq("puits", puits)
            q    = q.order("date", desc=False).limit(5000)
            data = q.execute().data
            return pd.DataFrame(data) if data else pd.DataFrame()
    except Exception:
        pass
    # Fallback SQLite
    try:
        conn = get_sqlite()
        sql  = "SELECT * FROM production_journaliere WHERE 1=1"
        if date_debut: sql += f" AND date>='{date_debut}'"
        if date_fin:   sql += f" AND date<='{date_fin}'"
        if champ:      sql += f" AND champ='{champ}'"
        if puits:      sql += f" AND puits='{puits}'"
        sql += " ORDER BY date ASC"
        df   = pd.read_sql_query(sql, conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

# ─────────────────────────────────────────
# LIRE ALERTES
# ─────────────────────────────────────────
def lire_alertes(resolues=False):
    resolue_int = 1 if resolues else 0
    try:
        if utiliser_supabase():
            sb   = get_supabase()
            q    = sb.table("alertes").select("*").eq("resolue", resolue_int)
            data = q.execute().data
            return pd.DataFrame(data) if data else pd.DataFrame()
    except Exception:
        pass
    try:
        conn = get_sqlite()
        df   = pd.read_sql_query(
            f"SELECT * FROM alertes WHERE resolue={resolue_int} "
            "ORDER BY date_alerte DESC", conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

# ─────────────────────────────────────────
# SAUVEGARDER ALERTE
# ─────────────────────────────────────────
def sauvegarder_alerte(puits, champ, type_alerte,
                        niveau, valeur, seuil, message):
    # Supabase
    if utiliser_supabase():
        try:
            get_supabase().table("alertes").insert({
                "puits": puits, "champ": champ,
                "type_alerte": type_alerte, "niveau": niveau,
                "valeur_actuelle": float(valeur),
                "seuil": float(seuil),
                "message": message, "resolue": 0
            }).execute()
            return
        except Exception:
            pass
    # SQLite fallback
    try:
        conn = get_sqlite()
        conn.cursor().execute("""
            INSERT INTO alertes
            (puits,champ,type_alerte,niveau,
             valeur_actuelle,seuil,message)
            VALUES (?,?,?,?,?,?,?)
        """, (puits, champ, type_alerte, niveau,
              valeur, seuil, message))
        conn.commit()
        conn.close()
    except Exception:
        pass

# ─────────────────────────────────────────
# SAUVEGARDER PRODUCTION (saisie manuelle)
# ─────────────────────────────────────────
def sauvegarder_production(date_s, puits, champ,
                            prod_huile, prod_gaz, prod_eau,
                            wc, gor, pression, temperature,
                            heures, statut,
                            saisie_par="Systeme"):
    record = {
        "date":                 str(date_s),
        "puits":                puits,
        "champ":                champ,
        "production_huile_bbl": float(round(prod_huile, 0)),
        "production_gaz_mmscf": float(round(prod_gaz, 3)),
        "production_eau_bbl":   float(round(prod_eau, 0)),
        "water_cut":            float(round(wc, 4)),
        "gor":                  float(round(gor, 0)),
        "pression_tete_psi":    float(round(pression, 1)),
        "temperature_f":        float(round(temperature, 1)),
        "heures_production":    float(heures),
        "statut":               statut,
    }

    # Supabase en priorité
    if utiliser_supabase():
        try:
            get_supabase().table("production_journaliere").insert(record).execute()
            return True
        except Exception:
            pass

    # SQLite fallback
    try:
        conn = get_sqlite()
        conn.cursor().execute("""
            INSERT OR REPLACE INTO production_journaliere
            (date,puits,champ,
             production_huile_bbl,production_gaz_mmscf,
             production_eau_bbl,water_cut,gor,
             pression_tete_psi,temperature_f,
             heures_production,statut)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (record["date"], record["puits"], record["champ"],
              record["production_huile_bbl"], record["production_gaz_mmscf"],
              record["production_eau_bbl"], record["water_cut"],
              record["gor"], record["pression_tete_psi"],
              record["temperature_f"], record["heures_production"],
              record["statut"]))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False
