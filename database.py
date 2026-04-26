# database.py
# Connexion Supabase (PostgreSQL cloud) + fallback SQLite

import pandas as pd
import sqlite3
import streamlit as st
from datetime import date, timedelta
from config import PROFILS_PUITS

# ─────────────────────────────────────────
# DÉTECTION : Supabase ou SQLite local
# ─────────────────────────────────────────
def utiliser_supabase():
    try:
        url = st.secrets["supabase"]["url"]
        return url != "" and url is not None
    except Exception:
        return False

# ─────────────────────────────────────────
# CONNEXION SUPABASE
# ─────────────────────────────────────────
def get_supabase():
    from supabase import create_client
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

# ─────────────────────────────────────────
# CONNEXION SQLITE (fallback local / démo)
# ─────────────────────────────────────────
DB_PATH = "petroci.db"

def get_sqlite():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# ─────────────────────────────────────────
# INITIALISER LES TABLES SQLITE
# ─────────────────────────────────────────
def initialiser_sqlite():
    conn = get_sqlite()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS puits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom_puits   TEXT UNIQUE NOT NULL,
            champ       TEXT,
            operateur   TEXT,
            type_puits  TEXT DEFAULT 'Producteur',
            latitude    REAL,
            longitude   REAL,
            profondeur_totale_m REAL,
            date_forage TEXT,
            statut      TEXT DEFAULT 'Actif'
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS production_journaliere (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date                 TEXT NOT NULL,
            puits                TEXT,
            champ                TEXT,
            production_huile_bbl REAL DEFAULT 0,
            production_gaz_mmscf REAL DEFAULT 0,
            production_eau_bbl   REAL DEFAULT 0,
            water_cut            REAL DEFAULT 0,
            gor                  REAL DEFAULT 0,
            pression_tete_psi    REAL DEFAULT 0,
            temperature_f        REAL DEFAULT 0,
            heures_production    REAL DEFAULT 24,
            statut               TEXT DEFAULT 'Actif'
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS alertes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_alerte     TEXT DEFAULT (datetime('now')),
            puits           TEXT,
            champ           TEXT,
            type_alerte     TEXT,
            niveau          TEXT,
            valeur_actuelle REAL,
            seuil           REAL,
            message         TEXT,
            resolue         INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()

# ─────────────────────────────────────────
# PEUPLER PUITS INITIAUX
# ─────────────────────────────────────────
def peupler_puits():
    conn = get_sqlite()
    c = conn.cursor()
    for nom, p in PROFILS_PUITS.items():
        statut = "Critique" if p["wc_base"] > 0.65 else \
                 "Alerte"   if p["wc_base"] > 0.50 else "Actif"
        c.execute("""
            INSERT OR IGNORE INTO puits
            (nom_puits, champ, operateur, latitude, longitude, statut)
            VALUES (?,?,?,?,?,?)
        """, (nom, p["champ"],
              {"Baleine":"ENI","Sankofa":"TotalEnergies",
               "Foxtrot":"PETROCI","Baobab":"CNR International"}
               .get(p["champ"],"PETROCI"),
              p["lat"], p["lon"], statut))
    conn.commit()
    conn.close()

# ─────────────────────────────────────────
# LIRE PUITS
# ─────────────────────────────────────────
def lire_puits(champ=None, statut=None):
    if utiliser_supabase():
        sb = get_supabase()
        q = sb.table("puits").select("*")
        if champ:  q = q.eq("champ", champ)
        if statut: q = q.eq("statut", statut)
        return pd.DataFrame(q.execute().data)
    else:
        conn = get_sqlite()
        sql = "SELECT * FROM puits WHERE 1=1"
        if champ:  sql += f" AND champ='{champ}'"
        if statut: sql += f" AND statut='{statut}'"
        df = pd.read_sql_query(sql, conn)
        conn.close()
        return df

# ─────────────────────────────────────────
# LIRE PRODUCTION
# ─────────────────────────────────────────
def lire_production(date_debut=None, date_fin=None,
                    champ=None, puits=None):
    if utiliser_supabase():
        sb = get_supabase()
        q = sb.table("production_journaliere").select("*")
        if date_debut: q = q.gte("date", str(date_debut))
        if date_fin:   q = q.lte("date", str(date_fin))
        if champ:      q = q.eq("champ", champ)
        if puits:      q = q.eq("puits", puits)
        data = q.execute().data
        return pd.DataFrame(data) if data else pd.DataFrame()
    else:
        conn = get_sqlite()
        sql = "SELECT * FROM production_journaliere WHERE 1=1"
        if date_debut: sql += f" AND date>='{date_debut}'"
        if date_fin:   sql += f" AND date<='{date_fin}'"
        if champ:      sql += f" AND champ='{champ}'"
        if puits:      sql += f" AND puits='{puits}'"
        sql += " ORDER BY date DESC"
        df = pd.read_sql_query(sql, conn)
        conn.close()
        return df

# ─────────────────────────────────────────
# LIRE ALERTES
# ─────────────────────────────────────────
def lire_alertes(resolues=False):
    if utiliser_supabase():
        sb = get_supabase()
        q = sb.table("alertes").select("*").eq("resolue", resolues)
        data = q.execute().data
        return pd.DataFrame(data) if data else pd.DataFrame()
    else:
        conn = get_sqlite()
        df = pd.read_sql_query(
            f"SELECT * FROM alertes WHERE resolue={1 if resolues else 0} "
            "ORDER BY date_alerte DESC", conn)
        conn.close()
        return df

# ─────────────────────────────────────────
# SAUVEGARDER ALERTE
# ─────────────────────────────────────────
def sauvegarder_alerte(puits, champ, type_alerte,
                        niveau, valeur, seuil, message):
    if utiliser_supabase():
        sb = get_supabase()
        sb.table("alertes").insert({
            "puits": puits, "champ": champ,
            "type_alerte": type_alerte, "niveau": niveau,
            "valeur_actuelle": valeur, "seuil": seuil,
            "message": message
        }).execute()
    else:
        conn = get_sqlite()
        conn.cursor().execute("""
            INSERT INTO alertes
            (puits,champ,type_alerte,niveau,valeur_actuelle,seuil,message)
            VALUES (?,?,?,?,?,?,?)
        """, (puits, champ, type_alerte, niveau, valeur, seuil, message))
        conn.commit()
        conn.close()
