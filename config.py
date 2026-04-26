# config.py
# Configuration globale du système PETROCI

CONFIG = {
    "database": {
        "url": "",       # Rempli via secrets Streamlit
        "key": ""        # Rempli via secrets Streamlit
    },
    "alertes": {
        "water_cut_alerte":   0.50,
        "water_cut_critique": 0.65,
        "production_min_bbl": 2000,
        "pression_min_psi":   200,
        "declin_mensuel_max": 0.10
    },
    "champs": {
        "Baleine": {
            "operateur":       "ENI",
            "type":            "Offshore",
            "profondeur_eau_m": 1200,
            "date_debut":      "2021-01-01"
        },
        "Sankofa": {
            "operateur":       "TotalEnergies",
            "type":            "Offshore",
            "profondeur_eau_m": 800,
            "date_debut":      "2015-06-01"
        },
        "Foxtrot": {
            "operateur":       "PETROCI",
            "type":            "Offshore",
            "profondeur_eau_m": 600,
            "date_debut":      "2005-03-01"
        },
        "Baobab": {
            "operateur":       "CNR International",
            "type":            "Offshore",
            "profondeur_eau_m": 1000,
            "date_debut":      "2005-01-01"
        }
    },
    "prix_baril_USD": 78.5,
    "taux_USD_XOF":   615
}

SEUILS      = CONFIG["alertes"]
CHAMPS      = CONFIG["champs"]
PRIX_BARIL  = CONFIG["prix_baril_USD"]
TAUX        = CONFIG["taux_USD_XOF"]

# Profils de production par puits
PROFILS_PUITS = {
    "Baleine-1": {"prod_base": 8500, "declin": 0.004, "wc_base": 0.35, "pression_base": 420, "champ": "Baleine", "lat": 4.852, "lon": -3.987},
    "Baleine-2": {"prod_base": 6200, "declin": 0.005, "wc_base": 0.42, "pression_base": 380, "champ": "Baleine", "lat": 4.855, "lon": -3.991},
    "Baleine-3": {"prod_base": 9100, "declin": 0.003, "wc_base": 0.28, "pression_base": 450, "champ": "Baleine", "lat": 4.848, "lon": -3.983},
    "Baleine-4": {"prod_base": 3800, "declin": 0.008, "wc_base": 0.61, "pression_base": 290, "champ": "Baleine", "lat": 4.860, "lon": -3.995},
    "Sankofa-1": {"prod_base": 5200, "declin": 0.006, "wc_base": 0.20, "pression_base": 310, "champ": "Sankofa", "lat": 4.120, "lon": -3.456},
    "Sankofa-2": {"prod_base": 4800, "declin": 0.006, "wc_base": 0.33, "pression_base": 340, "champ": "Sankofa", "lat": 4.125, "lon": -3.461},
    "Sankofa-3": {"prod_base": 3200, "declin": 0.007, "wc_base": 0.25, "pression_base": 360, "champ": "Sankofa", "lat": 4.118, "lon": -3.451},
    "Foxtrot-1": {"prod_base": 2100, "declin": 0.010, "wc_base": 0.55, "pression_base": 210, "champ": "Foxtrot", "lat": 3.890, "lon": -3.234},
    "Foxtrot-2": {"prod_base": 1800, "declin": 0.012, "wc_base": 0.68, "pression_base": 195, "champ": "Foxtrot", "lat": 3.895, "lon": -3.238},
    "Baobab-1":  {"prod_base": 3500, "declin": 0.007, "wc_base": 0.40, "pression_base": 280, "champ": "Baobab",  "lat": 4.350, "lon": -3.678},
}
