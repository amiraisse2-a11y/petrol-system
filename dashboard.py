# dashboard.py
# Interface principale PETROCI — Version Cloud (Streamlit)
# 3 modes de saisie : Manuel / Excel / API automatique

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta
import sqlite3

from database import (
    initialiser_sqlite, peupler_puits, lire_puits,
    lire_production, lire_alertes
)
from data_generator import generer_production_historique
from analytics import (
    kpis_journaliers, production_par_champ,
    calculer_declin, historique_champs
)
from alerts import verifier_alertes, resume_alertes
from config import PRIX_BARIL, TAUX, PROFILS_PUITS

DB_PATH = "petroci.db"

# ════════════════════════════════════════════
# CONFIGURATION PAGE
# ════════════════════════════════════════════
st.set_page_config(
    page_title="PETROCI — Système de Production",
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ════════════════════════════════════════════
# INITIALISATION
# ════════════════════════════════════════════
@st.cache_resource
def setup():
    initialiser_sqlite()
    peupler_puits()
    generer_production_historique(365)
    return True

setup()

# ════════════════════════════════════════════
# FONCTION SAUVEGARDER UNE MESURE
# ════════════════════════════════════════════
def sauvegarder_mesure(date_s, puits, champ, prod_huile,
                        prod_gaz, prod_eau, wc, gor,
                        pression, temperature, heures, statut):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.cursor().execute("""
        INSERT OR REPLACE INTO production_journaliere
        (date, puits, champ,
         production_huile_bbl, production_gaz_mmscf,
         production_eau_bbl, water_cut, gor,
         pression_tete_psi, temperature_f,
         heures_production, statut)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (str(date_s), puits, champ,
          round(prod_huile,0), round(prod_gaz,3),
          round(prod_eau,0), round(wc,4),
          round(gor,0), round(pression,1),
          round(temperature,1), heures, statut))
    conn.commit()
    conn.close()

# ════════════════════════════════════════════
# SIDEBAR — NAVIGATION
# ════════════════════════════════════════════
st.sidebar.title("🛢️ PETROCI")
st.sidebar.caption("Système de Production Offshore CI")

page = st.sidebar.radio("Navigation", [
    "🏠 Tableau de Bord",
    "🛢️ Puits & Champs",
    "📊 Analyse Production",
    "📝 Saisie des Données",
    "⚠️ Alertes",
    "📈 Déclin & Prévisions",
    "📋 Rapports",
])

st.sidebar.divider()
st.sidebar.subheader("🔧 Filtres")

champs_dispo = ["Tous", "Baleine", "Sankofa", "Foxtrot", "Baobab"]
champ_filtre = st.sidebar.selectbox("Champ pétrolier", champs_dispo)

periode_label = st.sidebar.selectbox(
    "Période",
    ["7 jours", "30 jours", "90 jours", "365 jours"]
)
nb_jours   = int(periode_label.split()[0])
date_fin   = date.today()
date_debut = date_fin - timedelta(days=nb_jours)

if st.sidebar.button("🔄 Actualiser & Vérifier alertes"):
    verifier_alertes()
    st.rerun()

resume = resume_alertes()
if resume["critiques"] > 0:
    st.sidebar.error(f"🔴 {resume['critiques']} alerte(s) critique(s)")
if resume["alertes"] > 0:
    st.sidebar.warning(f"⚠️ {resume['alertes']} alerte(s) active(s)")

# ════════════════════════════════════════════
# PAGE 1 — TABLEAU DE BORD
# ════════════════════════════════════════════
if page == "🏠 Tableau de Bord":

    st.title("🛢️ PETROCI — Tableau de Bord Production")
    st.caption(f"Données au {date.today().strftime('%d/%m/%Y')} | "
               f"Champs offshore Côte d'Ivoire")

    kpis = kpis_journaliers()
    if kpis:
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("🛢️ Production",
                  f"{kpis['production_totale_bbl']:,.0f} bbl/j")
        c2.metric("💰 Revenu/jour",
                  f"${kpis['revenu_journalier_usd']:,.0f}",
                  delta=f"{kpis['revenu_journalier_xof']/1e6:.1f}M FCFA")
        c3.metric("✅ Puits Actifs",  kpis["nb_puits_actifs"])
        c4.metric("⚠️ Alertes",       kpis["nb_puits_alerte"],
                  delta_color="inverse")
        c5.metric("🔴 Critiques",     kpis["nb_puits_critiques"],
                  delta_color="inverse")

    st.divider()

    df_hist = historique_champs(nb_jours)

    if not df_hist.empty:
        cg, cd = st.columns(2)
        with cg:
            df_total = (df_hist.groupby("date")["production_huile_bbl"]
                        .sum().reset_index())
            fig = px.area(
                df_total, x="date", y="production_huile_bbl",
                title=f"Production Totale CI — {periode_label}",
                labels={"production_huile_bbl": "bbl/jour", "date": "Date"},
                color_discrete_sequence=["#00CC96"]
            )
            fig.update_layout(hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
        with cd:
            fig2 = px.line(
                df_hist, x="date", y="production_huile_bbl",
                color="champ",
                title=f"Production par Champ — {periode_label}",
                labels={"production_huile_bbl": "bbl/jour", "date": "Date"}
            )
            st.plotly_chart(fig2, use_container_width=True)

    st.subheader("🗺️ Carte des Puits Offshore CI")
    df_puits = lire_puits()
    if not df_puits.empty and "latitude" in df_puits.columns:
        couleurs = {"Actif":"#00CC96","Alerte":"#FFA500","Critique":"#FF0000"}
        fig_map = px.scatter_mapbox(
            df_puits, lat="latitude", lon="longitude",
            color="statut", hover_name="nom_puits",
            hover_data=["champ","operateur","statut"],
            color_discrete_map=couleurs,
            title="Localisation des puits offshore Côte d'Ivoire",
            zoom=7, center={"lat":4.3,"lon":-3.7}
        )
        fig_map.update_layout(mapbox_style="open-street-map", height=450)
        st.plotly_chart(fig_map, use_container_width=True)

# ════════════════════════════════════════════
# PAGE 2 — PUITS & CHAMPS
# ════════════════════════════════════════════
elif page == "🛢️ Puits & Champs":

    st.title("🛢️ Puits & Champs Pétroliers")

    champ_q = None if champ_filtre == "Tous" else champ_filtre
    df = lire_puits(champ=champ_q)

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Puits", len(df))
    c2.metric("Actifs",    int((df["statut"]=="Actif").sum())    if not df.empty else 0)
    c3.metric("Alertes",   int((df["statut"]=="Alerte").sum())   if not df.empty else 0)
    c4.metric("Critiques", int((df["statut"]=="Critique").sum()) if not df.empty else 0)

    st.subheader("Liste des Puits")

    def style_statut(val):
        if val == "Critique": return "background-color:#FF000033;color:red"
        if val == "Alerte":   return "background-color:#FFA50033;color:orange"
        return "background-color:#00CC9633;color:green"

    cols_afficher = [c for c in
        ["nom_puits","champ","operateur","type_puits","statut","date_forage"]
        if c in df.columns]

    st.dataframe(
        df[cols_afficher].style.map(style_statut, subset=["statut"])
        if not df.empty else df,
        use_container_width=True, hide_index=True
    )

    if not df.empty:
        cg, cd = st.columns(2)
        with cg:
            fig = px.pie(df, names="champ", title="Puits par champ",
                         color_discrete_sequence=px.colors.qualitative.Set2)
            st.plotly_chart(fig, use_container_width=True)
        with cd:
            cnt = df.groupby(["champ","statut"]).size().reset_index(name="count")
            fig2 = px.bar(cnt, x="champ", y="count", color="statut",
                          title="Statut par champ",
                          color_discrete_map={"Actif":"#00CC96",
                                              "Alerte":"#FFA500",
                                              "Critique":"#FF0000"})
            st.plotly_chart(fig2, use_container_width=True)

# ════════════════════════════════════════════
# PAGE 3 — ANALYSE PRODUCTION
# ════════════════════════════════════════════
elif page == "📊 Analyse Production":

    st.title("📊 Analyse de Production")
    rapport = production_par_champ(nb_jours)

    if not rapport.empty:
        c1,c2,c3 = st.columns(3)
        c1.metric("Production Période",
                  f"{rapport['Production_Totale'].sum():,.0f} bbl")
        c2.metric("Revenus Totaux",
                  f"${rapport['Revenu_USD'].sum():,.0f}")
        c3.metric("Revenus FCFA",
                  f"{rapport['Revenu_FCFA'].sum()/1e9:.2f} Mds FCFA")

        st.divider()
        st.subheader("Performance par Champ")
        aff = rapport.copy()
        aff["WaterCut_Moyen"]    = aff["WaterCut_Moyen"].map("{:.1%}".format)
        aff["Production_Totale"] = aff["Production_Totale"].map("{:,.0f}".format)
        aff["Revenu_USD"]        = aff["Revenu_USD"].map("${:,.0f}".format)
        aff["Revenu_FCFA"]       = aff["Revenu_FCFA"].map("{:,.0f}".format)
        st.dataframe(aff, use_container_width=True, hide_index=True)

        fig = go.Figure(go.Bar(
            x=rapport["champ"],
            y=rapport["Revenu_FCFA"]/1e6,
            text=[f"{v/1e6:.0f}M" for v in rapport["Revenu_FCFA"]],
            textposition="auto",
            marker_color=["#00CC96","#636EFA","#FFA500","#FF6692"]
        ))
        fig.update_layout(
            title=f"Revenus par Champ — {periode_label} (Millions FCFA)",
            xaxis_title="Champ", yaxis_title="Revenus (M FCFA)"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucune donnée disponible pour cette période.")

# ════════════════════════════════════════════
# PAGE 4 — SAISIE DES DONNÉES (3 FAÇONS)
# ════════════════════════════════════════════
elif page == "📝 Saisie des Données":

    st.title("📝 Saisie des Données de Production")
    st.caption("3 façons d'entrer vos données dans le système")

    onglet1, onglet2, onglet3 = st.tabs([
        "✏️ Saisie Manuelle",
        "📂 Import Fichier Excel/CSV",
        "🔗 Coller / URL / API"
    ])

    # ─────────────────────────────────
    # ONGLET 1 — SAISIE MANUELLE
    # ─────────────────────────────────
    with onglet1:
        st.subheader("✏️ Saisie Manuelle Journalière")
        st.info("L'ingénieur terrain remplit ce formulaire chaque jour depuis son téléphone.")

        col1, col2 = st.columns(2)

        with col1:
            date_saisie = st.date_input("📅 Date", value=date.today())
            puits_saisi = st.selectbox("🛢️ Puits", list(PROFILS_PUITS.keys()))
            champ_auto  = PROFILS_PUITS[puits_saisi]["champ"]
            st.info(f"Champ : **{champ_auto}**")
            production  = st.number_input("🛢️ Production huile (bbl/j)",
                                           min_value=0.0, value=5000.0, step=50.0)
            wc_pct      = st.slider("💧 Water Cut (%)",
                                     min_value=0.0, max_value=100.0,
                                     value=35.0, step=0.1)
            wc          = wc_pct / 100

        with col2:
            gor         = st.number_input("⛽ GOR (scf/stb)",
                                           min_value=0.0, value=800.0, step=10.0)
            pression    = st.number_input("🔧 Pression tête (psi)",
                                           min_value=0.0, value=380.0, step=5.0)
            temperature = st.number_input("🌡️ Température (°F)",
                                           min_value=0.0, value=175.0, step=1.0)
            heures      = st.slider("⏱️ Heures de production",
                                     min_value=0, max_value=24, value=24)
            st.text_area("📝 Commentaire",
                          placeholder="Observations terrain...")

        prod_eau = production * wc / max(1 - wc, 0.01)
        prod_gaz = production * gor / 1000
        statut   = ("Critique" if wc > 0.65 else
                    "Alerte"   if wc > 0.50 else "Actif")

        st.divider()
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Huile",  f"{production:,.0f} bbl/j")
        c2.metric("Eau",    f"{prod_eau:,.0f} bbl/j")
        c3.metric("Gaz",    f"{prod_gaz:.1f} MMscf/j")
        c4.metric("Statut", statut)

        if st.button("💾 Enregistrer", type="primary"):
            sauvegarder_mesure(
                date_saisie, puits_saisi, champ_auto,
                production, prod_gaz, prod_eau,
                wc, gor, pression, temperature, heures, statut
            )
            st.success(
                f"✅ **{puits_saisi}** enregistré — "
                f"{production:,.0f} bbl/j | WC: {wc_pct:.1f}% | "
                f"{date_saisie.strftime('%d/%m/%Y')}"
            )
            st.balloons()

    # ─────────────────────────────────
    # ONGLET 2 — IMPORT EXCEL / CSV
    # ─────────────────────────────────
    with onglet2:
        st.subheader("📂 Import depuis un fichier Excel ou CSV")
        st.info("Uploadez votre fichier de production. Le système importe toutes les données automatiquement.")

        # Modèle à télécharger
        st.subheader("1️⃣ Télécharger le modèle")
        modele = pd.DataFrame({
            "date":                 ["2026-04-26","2026-04-26"],
            "puits":                ["Baleine-1", "Sankofa-1"],
            "champ":                ["Baleine",   "Sankofa"],
            "production_huile_bbl": [8500,         5200],
            "production_gaz_mmscf": [7.2,          3.4],
            "production_eau_bbl":   [4590,         1300],
            "water_cut":            [0.35,         0.20],
            "gor":                  [850,          650],
            "pression_tete_psi":    [420,          310],
            "temperature_f":        [185,          172],
            "heures_production":    [24,           24],
            "statut":               ["Actif",      "Actif"],
        })
        st.download_button(
            "⬇️ Télécharger le modèle CSV",
            data=modele.to_csv(index=False).encode("utf-8"),
            file_name="modele_saisie_petroci.csv",
            mime="text/csv"
        )

        st.divider()
        st.subheader("2️⃣ Uploader votre fichier")

        fichier = st.file_uploader(
            "Choisir un fichier (.xlsx ou .csv)",
            type=["xlsx","csv"]
        )

        if fichier is not None:
            try:
                df_import = (pd.read_csv(fichier)
                             if fichier.name.endswith(".csv")
                             else pd.read_excel(fichier))

                st.success(f"✅ **{len(df_import)} lignes** détectées")
                st.dataframe(df_import.head(10), use_container_width=True)

                cols_req = ["date","puits","champ","production_huile_bbl","water_cut"]
                manquantes = [c for c in cols_req if c not in df_import.columns]

                if manquantes:
                    st.error(f"❌ Colonnes manquantes : {manquantes}")
                else:
                    c1,c2,c3 = st.columns(3)
                    c1.metric("Lignes", len(df_import))
                    c2.metric("Puits", df_import["puits"].nunique())
                    c3.metric("Période",
                              f"{df_import['date'].min()} → {df_import['date'].max()}")

                    if st.button("📥 Importer toutes les données", type="primary"):
                        conn   = sqlite3.connect(DB_PATH, check_same_thread=False)
                        succes = 0
                        for _, row in df_import.iterrows():
                            try:
                                conn.cursor().execute("""
                                    INSERT OR REPLACE INTO production_journaliere
                                    (date,puits,champ,
                                     production_huile_bbl,production_gaz_mmscf,
                                     production_eau_bbl,water_cut,gor,
                                     pression_tete_psi,temperature_f,
                                     heures_production,statut)
                                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                                """, (
                                    str(row.get("date","")),
                                    str(row.get("puits","")),
                                    str(row.get("champ","")),
                                    float(row.get("production_huile_bbl",0)),
                                    float(row.get("production_gaz_mmscf",0)),
                                    float(row.get("production_eau_bbl",0)),
                                    float(row.get("water_cut",0)),
                                    float(row.get("gor",0)),
                                    float(row.get("pression_tete_psi",0)),
                                    float(row.get("temperature_f",0)),
                                    float(row.get("heures_production",24)),
                                    str(row.get("statut","Actif"))
                                ))
                                succes += 1
                            except Exception:
                                pass
                        conn.commit()
                        conn.close()
                        st.success(f"✅ **{succes} lignes** importées avec succès")
                        st.balloons()
            except Exception as e:
                st.error(f"❌ Erreur lecture fichier : {e}")

    # ─────────────────────────────────
    # ONGLET 3 — COLLER / URL / API
    # ─────────────────────────────────
    with onglet3:
        st.subheader("🔗 Import depuis URL ou saisie directe")

        source = st.radio("Type de source", [
            "📋 Coller les données (CSV)",
            "📎 URL fichier CSV en ligne",
            "🔌 API JSON externe"
        ])

        # ── COLLER CSV ──
        if source == "📋 Coller les données (CSV)":
            st.caption("Format : date,puits,champ,production_huile_bbl,water_cut,statut")
            donnees = st.text_area(
                "Collez vos données ici", height=200,
                placeholder=(
                    "date,puits,champ,production_huile_bbl,water_cut,statut\n"
                    "2026-04-26,Baleine-1,Baleine,8500,0.35,Actif\n"
                    "2026-04-26,Sankofa-1,Sankofa,5200,0.20,Actif"
                )
            )
            if donnees and st.button("📥 Importer", type="primary"):
                try:
                    from io import StringIO
                    df_c   = pd.read_csv(StringIO(donnees))
                    st.success(f"✅ {len(df_c)} lignes détectées")
                    st.dataframe(df_c, use_container_width=True)
                    conn   = sqlite3.connect(DB_PATH, check_same_thread=False)
                    succes = 0
                    for _, row in df_c.iterrows():
                        try:
                            conn.cursor().execute("""
                                INSERT OR REPLACE INTO production_journaliere
                                (date,puits,champ,
                                 production_huile_bbl,water_cut,statut)
                                VALUES (?,?,?,?,?,?)
                            """, (
                                str(row.get("date","")),
                                str(row.get("puits","")),
                                str(row.get("champ","")),
                                float(row.get("production_huile_bbl",0)),
                                float(row.get("water_cut",0)),
                                str(row.get("statut","Actif"))
                            ))
                            succes += 1
                        except Exception:
                            pass
                    conn.commit()
                    conn.close()
                    st.success(f"✅ {succes} lignes importées")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Erreur : {e}")

        # ── URL CSV ──
        elif source == "📎 URL fichier CSV en ligne":
            url = st.text_input("URL du fichier CSV",
                                 placeholder="https://exemple.com/production.csv")
            if url and st.button("📥 Charger", type="primary"):
                try:
                    df_url = pd.read_csv(url)
                    st.success(f"✅ {len(df_url)} lignes chargées")
                    st.dataframe(df_url.head(), use_container_width=True)
                    conn   = sqlite3.connect(DB_PATH, check_same_thread=False)
                    for _, row in df_url.iterrows():
                        try:
                            conn.cursor().execute("""
                                INSERT OR REPLACE INTO production_journaliere
                                (date,puits,champ,
                                 production_huile_bbl,water_cut,statut)
                                VALUES (?,?,?,?,?,?)
                            """, (
                                str(row.get("date","")),
                                str(row.get("puits","")),
                                str(row.get("champ","")),
                                float(row.get("production_huile_bbl",0)),
                                float(row.get("water_cut",0)),
                                str(row.get("statut","Actif"))
                            ))
                        except Exception:
                            pass
                    conn.commit()
                    conn.close()
                    st.success("✅ Données importées avec succès")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Impossible de charger : {e}")

        # ── API JSON ──
        else:
            url_api = st.text_input("URL de l'API",
                                     placeholder="https://api.votresysteme.com/production")
            token   = st.text_input("Token (optionnel)", type="password")
            if url_api and st.button("🔌 Appeler l'API", type="primary"):
                try:
                    import urllib.request, json
                    headers = {"Authorization": f"Bearer {token}"} if token else {}
                    req     = urllib.request.Request(url_api, headers=headers)
                    with urllib.request.urlopen(req, timeout=10) as r:
                        data = json.loads(r.read())
                    df_api = pd.DataFrame(
                        data if isinstance(data, list)
                        else data.get("data", [data])
                    )
                    st.success(f"✅ {len(df_api)} enregistrements reçus")
                    st.dataframe(df_api.head(), use_container_width=True)
                except Exception as e:
                    st.error(f"❌ Erreur API : {e}")

# ════════════════════════════════════════════
# PAGE 5 — ALERTES
# ════════════════════════════════════════════
elif page == "⚠️ Alertes":

    st.title("⚠️ Système d'Alertes")

    if st.button("🔍 Vérifier maintenant"):
        nb = len(verifier_alertes())
        st.success(f"✅ {nb} alertes générées")

    df_al = lire_alertes(resolues=False)

    if not df_al.empty:
        c1,c2,c3 = st.columns(3)
        c1.metric("Total", len(df_al))
        c2.metric("Critiques", int((df_al["niveau"]=="CRITIQUE").sum()))
        c3.metric("Alertes",   int((df_al["niveau"]=="ALERTE").sum()))
        st.divider()
        for _, a in df_al[df_al["niveau"]=="CRITIQUE"].iterrows():
            st.error(f"🔴 **CRITIQUE** | {a['puits']} ({a['champ']}) | {a['message']}")
        for _, a in df_al[df_al["niveau"]=="ALERTE"].iterrows():
            st.warning(f"⚠️ **ALERTE** | {a['puits']} ({a['champ']}) | {a['message']}")
    else:
        st.success("✅ Aucune alerte active")

# ════════════════════════════════════════════
# PAGE 6 — DÉCLIN & PRÉVISIONS
# ════════════════════════════════════════════
elif page == "📈 Déclin & Prévisions":

    st.title("📈 Analyse de Déclin & Prévisions")

    puits_choisi = st.selectbox("Choisir un puits", list(PROFILS_PUITS.keys()))
    declin       = calculer_declin(puits_choisi, nb_jours)

    if declin:
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Production Début",    f"{declin['production_debut']:,.0f} bbl/j")
        c2.metric("Production Actuelle", f"{declin['production_actuelle']:,.0f} bbl/j")
        c3.metric("Déclin Total",        f"{declin['declin_total_pct']:.1f}%",
                  delta_color="inverse")
        c4.metric("Déclin Mensuel",      f"{declin['declin_mensuel_pct']:.1f}%/mois",
                  delta_color="inverse")

    df_p = lire_production(date_debut=str(date_debut),
                            date_fin=str(date_fin), puits=puits_choisi)

    if not df_p.empty:
        df_p = df_p.sort_values("date")
        fig  = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_p["date"], y=df_p["production_huile_bbl"],
            name="Production Huile", mode="lines",
            line=dict(color="#00CC96", width=2)
        ))
        fig.add_trace(go.Scatter(
            x=df_p["date"],
            y=df_p["water_cut"].astype(float) *
              df_p["production_huile_bbl"].astype(float).max(),
            name="Water Cut (normalisé)", mode="lines",
            line=dict(color="#FFA500", width=1.5, dash="dash")
        ))
        fig.update_layout(
            title=f"Courbe de Déclin — {puits_choisi}",
            xaxis_title="Date", yaxis_title="Production (bbl/jour)",
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucune donnée pour ce puits.")

# ════════════════════════════════════════════
# PAGE 7 — RAPPORTS
# ════════════════════════════════════════════
elif page == "📋 Rapports":

    st.title("📋 Génération de Rapports")

    type_r = st.selectbox("Type de rapport", [
        "Rapport Production par Champ",
        "Rapport Performance Opérateurs",
        "Rapport Alertes Actives",
    ])

    if st.button("📄 Générer"):
        with st.spinner("Génération..."):
            rapport = production_par_champ(nb_jours)
            st.subheader(f"📊 {type_r}")
            st.caption(f"Période : {date_debut} → {date_fin} | "
                       f"Généré le : {date.today().strftime('%d/%m/%Y')}")

            if not rapport.empty:
                prod_tot = rapport["Production_Totale"].sum()
                rev_tot  = rapport["Revenu_USD"].sum()
                st.info(
                    f"Production : {prod_tot:,.0f} bbl | "
                    f"Revenus : ${rev_tot:,.0f} | "
                    f"{rev_tot*TAUX/1e9:.2f} Mds FCFA"
                )

                if type_r == "Rapport Performance Opérateurs":
                    df_op = lire_production(date_debut=str(date_debut),
                                             date_fin=str(date_fin))
                    if not df_op.empty:
                        from config import CHAMPS
                        df_op["operateur"] = df_op["champ"].map(
                            {k: v["operateur"] for k,v in CHAMPS.items()}
                        )
                        grp = df_op.groupby("operateur").agg(
                            Production=("production_huile_bbl","sum"),
                            WC_Moyen  =("water_cut","mean"),
                            Nb_Puits  =("puits","nunique")
                        ).reset_index()
                        st.dataframe(grp, use_container_width=True, hide_index=True)

                elif type_r == "Rapport Alertes Actives":
                    df_al = lire_alertes(resolues=False)
                    st.dataframe(df_al, use_container_width=True, hide_index=True) \
                        if not df_al.empty else st.success("Aucune alerte.")
                else:
                    st.dataframe(rapport, use_container_width=True, hide_index=True)

                fig = px.bar(rapport, x="champ", y="Production_Totale",
                             color="champ", title="Production par champ",
                             text="Production_Totale")
                fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
                st.plotly_chart(fig, use_container_width=True)

                st.download_button(
                    "⬇️ Télécharger CSV",
                    data=rapport.to_csv(index=False).encode("utf-8"),
                    file_name=f"rapport_petroci_{date.today()}.csv",
                    mime="text/csv"
                )
                st.success("✅ Rapport généré")
            else:
                st.warning("Aucune donnée disponible.")
