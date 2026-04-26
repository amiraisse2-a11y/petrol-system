# dashboard.py
# PETROCI — Design Premium 9/10
# Couleurs : Or #F0A500 + Bleu nuit #0A0E1A

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
# CONFIG PAGE
# ════════════════════════════════════════════
st.set_page_config(
    page_title="PETROCI — Production Dashboard",
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ════════════════════════════════════════════
# CSS PREMIUM
# ════════════════════════════════════════════
st.markdown("""
<style>
/* ── Fond global ── */
.stApp {
    background: linear-gradient(135deg, #0A0E1A 0%, #141B2D 100%);
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0D1220 0%, #141B2D 100%);
    border-right: 1px solid rgba(240,165,0,0.19);
}

/* ── Titre sidebar ── */
[data-testid="stSidebar"] h1 {
    color: #F0A500 !important;
    font-size: 1.4rem !important;
    letter-spacing: 2px;
}

/* ── Métriques KPI ── */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, #141B2D, #1E2A42);
    border: 1px solid rgba(240,165,0,0.25);
    border-radius: 12px;
    padding: 16px !important;
    box-shadow: 0 4px 20px rgba(240,165,0,0.08);
    transition: transform 0.2s ease;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    border-color: #F0A500;
    box-shadow: 0 8px 30px rgba(240,165,0,0.15);
}
[data-testid="stMetricLabel"] {
    color: #8B9BB4 !important;
    font-size: 0.75rem !important;
    letter-spacing: 1px;
    text-transform: uppercase;
}
[data-testid="stMetricValue"] {
    color: #F0A500 !important;
    font-size: 1.6rem !important;
    font-weight: 700 !important;
}

/* ── Boutons ── */
.stButton > button {
    background: linear-gradient(135deg, #F0A500, #D4870A) !important;
    color: #0A0E1A !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    letter-spacing: 0.5px;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 15px rgba(240,165,0,0.3) !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(240,165,0,0.5) !important;
}

/* ── Tabs ── */
[data-testid="stTabs"] button {
    color: #8B9BB4 !important;
    font-weight: 600;
    border-radius: 8px 8px 0 0 !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #F0A500 !important;
    border-bottom: 2px solid #F0A500 !important;
    background: #1E2A4220 !important;
}

/* ── Selectbox / Input ── */
[data-testid="stSelectbox"] > div > div,
[data-testid="stNumberInput"] input,
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    background: #1E2A42 !important;
    border: 1px solid rgba(240,165,0,0.19) !important;
    border-radius: 8px !important;
    color: #E8EDF5 !important;
}

/* ── Divider ── */
hr {
    border-color: rgba(240,165,0,0.19) !important;
}

/* ── Titres ── */
h1, h2, h3 {
    color: #E8EDF5 !important;
}

/* ── Radio buttons ── */
[data-testid="stRadio"] label {
    color: #8B9BB4 !important;
    font-size: 0.9rem;
}
[data-testid="stRadio"] label:hover {
    color: #F0A500 !important;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    border: 1px solid #F0A50020;
    border-radius: 8px;
}

/* ── Alerte boxes ── */
[data-testid="stAlert"] {
    border-radius: 8px !important;
    border-left: 4px solid #F0A500 !important;
}

/* ── Upload zone ── */
[data-testid="stFileUploader"] {
    background: #1E2A42 !important;
    border: 2px dashed #F0A50050 !important;
    border-radius: 12px !important;
}
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════
# HEADER PREMIUM
# ════════════════════════════════════════════
def afficher_header(titre, sous_titre=""):
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #141B2D, #1E2A42);
        border-left: 4px solid #F0A500;
        border-radius: 0 12px 12px 0;
        padding: 20px 24px;
        margin-bottom: 24px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    ">
        <h1 style="
            color: #F0A500;
            margin: 0;
            font-size: 1.8rem;
            letter-spacing: 1px;
        ">🛢️ {titre}</h1>
        <p style="
            color: #8B9BB4;
            margin: 4px 0 0 0;
            font-size: 0.85rem;
            letter-spacing: 0.5px;
        ">{sous_titre}</p>
    </div>
    """, unsafe_allow_html=True)


def kpi_card(label, valeur, sous_valeur="", couleur="#F0A500", icone="📊"):
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #141B2D, #1E2A42);
        border: 1px solid {couleur}40;
        border-top: 3px solid {couleur};
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        transition: all 0.3s ease;
        margin-bottom: 8px;
    ">
        <div style="font-size: 1.8rem; margin-bottom: 8px;">{icone}</div>
        <div style="color: #8B9BB4; font-size: 0.7rem;
                    letter-spacing: 1.5px; text-transform: uppercase;
                    margin-bottom: 6px;">{label}</div>
        <div style="color: {couleur}; font-size: 1.6rem;
                    font-weight: 800; line-height: 1.1;">{valeur}</div>
        <div style="color: #5A6A80; font-size: 0.75rem;
                    margin-top: 4px;">{sous_valeur}</div>
    </div>
    """, unsafe_allow_html=True)


def badge_statut(statut):
    cfg = {
        "Actif":    ("#00CC96", "#00CC9615", "●"),
        "Alerte":   ("#F0A500", "#F0A50015", "▲"),
        "Critique": ("#FF4B4B", "#FF4B4B15", "■"),
    }.get(statut, ("#8B9BB4", "#8B9BB415", "○"))
    return (f'<span style="background:{cfg[1]};color:{cfg[0]};'
            f'padding:3px 10px;border-radius:20px;font-size:0.8rem;'
            f'font-weight:600;border:1px solid {cfg[0]}40;">'
            f'{cfg[2]} {statut}</span>')


# ════════════════════════════════════════════
# INIT
# ════════════════════════════════════════════
@st.cache_resource
def setup():
    initialiser_sqlite()
    peupler_puits()
    generer_production_historique(365)
    return True

setup()


def sauvegarder_mesure(date_s, puits, champ, prod_huile,
                        prod_gaz, prod_eau, wc, gor,
                        pression, temperature, heures, statut):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.cursor().execute("""
        INSERT OR REPLACE INTO production_journaliere
        (date,puits,champ,
         production_huile_bbl,production_gaz_mmscf,
         production_eau_bbl,water_cut,gor,
         pression_tete_psi,temperature_f,
         heures_production,statut)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (str(date_s), puits, champ,
          round(prod_huile,0), round(prod_gaz,3),
          round(prod_eau,0), round(wc,4),
          round(gor,0), round(pression,1),
          round(temperature,1), heures, statut))
    conn.commit()
    conn.close()


# ════════════════════════════════════════════
# SIDEBAR PREMIUM
# ════════════════════════════════════════════
st.sidebar.markdown("""
<div style="text-align:center; padding: 16px 0 8px 0;">
    <div style="font-size:2.5rem;">🛢️</div>
    <div style="color:#F0A500; font-size:1.2rem;
                font-weight:800; letter-spacing:3px;">PETROCI</div>
    <div style="color:#5A6A80; font-size:0.7rem;
                letter-spacing:2px;">PRODUCTION DASHBOARD</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown(
    '<hr style="border-color:rgba(240,165,0,0.19); margin:8px 0;">',
    unsafe_allow_html=True
)

page = st.sidebar.radio("", [
    "🏠  Tableau de Bord",
    "🛢️  Puits & Champs",
    "📊  Analyse Production",
    "📝  Saisie des Données",
    "⚠️  Alertes",
    "📈  Déclin & Prévisions",
    "📋  Rapports",
])

st.sidebar.markdown(
    '<hr style="border-color:rgba(240,165,0,0.19); margin:8px 0;">',
    unsafe_allow_html=True
)
st.sidebar.markdown(
    '<div style="color:#5A6A80; font-size:0.7rem; '
    'letter-spacing:1px; text-transform:uppercase; '
    'padding: 0 0 6px 0;">Filtres</div>',
    unsafe_allow_html=True
)

champs_dispo = ["Tous", "Baleine", "Sankofa", "Foxtrot", "Baobab"]
champ_filtre = st.sidebar.selectbox("Champ", champs_dispo, label_visibility="collapsed")

periode_label = st.sidebar.selectbox(
    "Période", ["7 jours","30 jours","90 jours","365 jours"],
    label_visibility="collapsed"
)
nb_jours   = int(periode_label.split()[0])
date_fin   = date.today()
date_debut = date_fin - timedelta(days=nb_jours)

if st.sidebar.button("🔄  Actualiser", width='stretch'):
    verifier_alertes()
    st.rerun()

resume = resume_alertes()
if resume["critiques"] > 0:
    st.sidebar.markdown(
        f'<div style="background:#FF4B4B15;border:1px solid rgba(255,75,75,0.25);'
        f'border-radius:8px;padding:8px 12px;margin:4px 0;'
        f'color:#FF4B4B;font-size:0.8rem;">🔴 {resume["critiques"]} critique(s)</div>',
        unsafe_allow_html=True
    )
if resume["alertes"] > 0:
    st.sidebar.markdown(
        f'<div style="background:#F0A50015;border:1px solid rgba(240,165,0,0.25);'
        f'border-radius:8px;padding:8px 12px;margin:4px 0;'
        f'color:#F0A500;font-size:0.8rem;">⚠️ {resume["alertes"]} alerte(s)</div>',
        unsafe_allow_html=True
    )

st.sidebar.markdown("""
<div style="position:fixed; bottom:20px; left:0; width:280px;
            text-align:center; color:#2A3A52; font-size:0.65rem;
            letter-spacing:1px;">
    PETROCI © 2026 — Côte d'Ivoire
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════
# PAGE 1 — TABLEAU DE BORD
# ════════════════════════════════════════════
if page == "🏠  Tableau de Bord":

    afficher_header(
        "Tableau de Bord Production",
        f"Données au {date.today().strftime('%d %B %Y')} · "
        f"Champs offshore Côte d'Ivoire"
    )

    kpis = kpis_journaliers()
    if kpis:
        c1,c2,c3,c4,c5 = st.columns(5)
        with c1:
            kpi_card("Production Totale",
                     f"{kpis['production_totale_bbl']:,.0f}",
                     "bbl / jour", "#F0A500", "🛢️")
        with c2:
            kpi_card("Revenu Journalier",
                     f"${kpis['revenu_journalier_usd']:,.0f}",
                     f"{kpis['revenu_journalier_xof']/1e6:.0f}M FCFA",
                     "#00CC96", "💰")
        with c3:
            kpi_card("Puits Actifs",
                     str(kpis["nb_puits_actifs"]),
                     "en production", "#00CC96", "✅")
        with c4:
            kpi_card("Alertes",
                     str(kpis["nb_puits_alerte"]),
                     "surveillance requise", "#F0A500", "⚠️")
        with c5:
            kpi_card("Critiques",
                     str(kpis["nb_puits_critiques"]),
                     "intervention requise", "#FF4B4B", "🔴")

    st.markdown("<br>", unsafe_allow_html=True)

    df_hist = historique_champs(nb_jours)

    if not df_hist.empty:
        cg, cd = st.columns(2)

        with cg:
            df_total = (df_hist.groupby("date")["production_huile_bbl"]
                        .sum().reset_index())
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_total["date"],
                y=df_total["production_huile_bbl"],
                fill="tozeroy",
                fillcolor="rgba(240,165,0,0.1)",
                line=dict(color="#F0A500", width=2.5),
                name="Production"
            ))
            fig.update_layout(
                title=dict(text=f"Production Totale CI — {periode_label}",
                           font=dict(color="#E8EDF5", size=14)),
                paper_bgcolor="#141B2D",
                plot_bgcolor="#141B2D",
                xaxis=dict(gridcolor="#1E2A42", color="#8B9BB4"),
                yaxis=dict(gridcolor="#1E2A42", color="#8B9BB4",
                           title="bbl/jour"),
                hovermode="x unified",
                margin=dict(l=10, r=10, t=40, b=10)
            )
            st.plotly_chart(fig, width='stretch')

        with cd:
            couleurs_champs = {
                "Baleine": "#F0A500",
                "Sankofa": "#00CC96",
                "Foxtrot": "#FF4B4B",
                "Baobab":  "#636EFA"
            }
            fig2 = go.Figure()
            for champ in df_hist["champ"].unique():
                df_c = df_hist[df_hist["champ"] == champ]
                fig2.add_trace(go.Scatter(
                    x=df_c["date"],
                    y=df_c["production_huile_bbl"],
                    name=champ,
                    mode="lines",
                    line=dict(
                        color=couleurs_champs.get(champ, "#636EFA"),
                        width=2
                    )
                ))
            fig2.update_layout(
                title=dict(text=f"Production par Champ — {periode_label}",
                           font=dict(color="#E8EDF5", size=14)),
                paper_bgcolor="#141B2D",
                plot_bgcolor="#141B2D",
                xaxis=dict(gridcolor="#1E2A42", color="#8B9BB4"),
                yaxis=dict(gridcolor="#1E2A42", color="#8B9BB4"),
                legend=dict(bgcolor="#1E2A42", bordercolor="rgba(240,165,0,0.2)"),
                hovermode="x unified",
                margin=dict(l=10, r=10, t=40, b=10)
            )
            st.plotly_chart(fig2, width='stretch')

    # Carte puits
    st.markdown("""
    <div style="color:#8B9BB4; font-size:0.75rem; letter-spacing:1.5px;
                text-transform:uppercase; margin: 8px 0 12px 0;">
        🗺️ Localisation des Puits Offshore
    </div>
    """, unsafe_allow_html=True)

    df_puits = lire_puits()
    if not df_puits.empty and "latitude" in df_puits.columns:
        couleurs = {"Actif":"#00CC96","Alerte":"#F0A500","Critique":"#FF4B4B"}
        fig_map  = px.scatter_map(
            df_puits, lat="latitude", lon="longitude",
            color="statut", hover_name="nom_puits",
            hover_data=["champ","operateur","statut"],
            color_discrete_map=couleurs,
            zoom=7, center={"lat":4.3,"lon":-3.7}
        )
        fig_map.update_layout(
            map_style="carto-darkmatter",
            height=420,
            paper_bgcolor="#141B2D",
            margin=dict(l=0, r=0, t=0, b=0),
            legend=dict(bgcolor="#1E2A42", bordercolor="rgba(240,165,0,0.2)",
                        font=dict(color="#E8EDF5"))
        )
        st.plotly_chart(fig_map, width='stretch')

# ════════════════════════════════════════════
# PAGE 2 — PUITS & CHAMPS
# ════════════════════════════════════════════
elif page == "🛢️  Puits & Champs":

    afficher_header("Puits & Champs Pétroliers",
                    "Vue d'ensemble des actifs offshore CI")

    champ_q = None if champ_filtre == "Tous" else champ_filtre
    df      = lire_puits(champ=champ_q)

    c1,c2,c3,c4 = st.columns(4)
    with c1: kpi_card("Total Puits",   str(len(df)),
                       "", "#636EFA", "🛢️")
    with c2: kpi_card("Actifs",
                       str(int((df["statut"]=="Actif").sum()) if not df.empty else 0),
                       "", "#00CC96", "✅")
    with c3: kpi_card("Alertes",
                       str(int((df["statut"]=="Alerte").sum()) if not df.empty else 0),
                       "", "#F0A500", "⚠️")
    with c4: kpi_card("Critiques",
                       str(int((df["statut"]=="Critique").sum()) if not df.empty else 0),
                       "", "#FF4B4B", "🔴")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="color:#8B9BB4; font-size:0.75rem; letter-spacing:1.5px;
                text-transform:uppercase; margin-bottom:12px;">
        Liste des Puits
    </div>
    """, unsafe_allow_html=True)

    def style_statut(val):
        if val == "Critique": return "background-color:#FF4B4B20;color:#FF4B4B;font-weight:600"
        if val == "Alerte":   return "background-color:#F0A50020;color:#F0A500;font-weight:600"
        return "background-color:#00CC9620;color:#00CC96;font-weight:600"

    cols_afficher = [c for c in
        ["nom_puits","champ","operateur","type_puits","statut","date_forage"]
        if c in df.columns]

    st.dataframe(
        df[cols_afficher].style.map(style_statut, subset=["statut"])
        if not df.empty else df,
        width='stretch', hide_index=True
    )

    if not df.empty:
        cg, cd = st.columns(2)
        with cg:
            fig = px.pie(df, names="champ",
                         title="Répartition par Champ",
                         color_discrete_sequence=["#F0A500","#00CC96",
                                                   "#FF4B4B","#636EFA"])
            fig.update_layout(
                paper_bgcolor="#141B2D",
                plot_bgcolor="#141B2D",
                font=dict(color="#E8EDF5"),
                title_font=dict(color="#E8EDF5")
            )
            st.plotly_chart(fig, width='stretch')
        with cd:
            cnt  = df.groupby(["champ","statut"]).size().reset_index(name="count")
            fig2 = px.bar(cnt, x="champ", y="count", color="statut",
                          title="Statut par Champ",
                          color_discrete_map={"Actif":"#00CC96",
                                              "Alerte":"#F0A500",
                                              "Critique":"#FF4B4B"})
            fig2.update_layout(
                paper_bgcolor="#141B2D",
                plot_bgcolor="#141B2D",
                xaxis=dict(gridcolor="#1E2A42", color="#8B9BB4"),
                yaxis=dict(gridcolor="#1E2A42", color="#8B9BB4"),
                font=dict(color="#E8EDF5"),
                title_font=dict(color="#E8EDF5"),
                legend=dict(bgcolor="#1E2A42")
            )
            st.plotly_chart(fig2, width='stretch')

# ════════════════════════════════════════════
# PAGE 3 — ANALYSE PRODUCTION
# ════════════════════════════════════════════
elif page == "📊  Analyse Production":

    afficher_header("Analyse de Production",
                    f"Performance sur les {nb_jours} derniers jours")

    rapport = production_par_champ(nb_jours)

    if not rapport.empty:
        c1,c2,c3 = st.columns(3)
        with c1:
            kpi_card("Production Totale",
                     f"{rapport['Production_Totale'].sum():,.0f}",
                     "barils", "#F0A500", "🛢️")
        with c2:
            kpi_card("Revenus USD",
                     f"${rapport['Revenu_USD'].sum():,.0f}",
                     "dollars", "#00CC96", "💵")
        with c3:
            kpi_card("Revenus FCFA",
                     f"{rapport['Revenu_FCFA'].sum()/1e9:.2f} Mds",
                     "francs CFA", "#636EFA", "💶")

        st.markdown("<br>", unsafe_allow_html=True)

        cg, cd = st.columns(2)
        with cg:
            fig = go.Figure(go.Bar(
                x=rapport["champ"],
                y=rapport["Revenu_FCFA"]/1e6,
                text=[f"{v/1e6:.0f}M FCFA" for v in rapport["Revenu_FCFA"]],
                textposition="outside",
                textfont=dict(color="#E8EDF5"),
                marker=dict(
                    color=["#F0A500","#00CC96","#FF4B4B","#636EFA"],
                    line=dict(width=0)
                )
            ))
            fig.update_layout(
                title=dict(text="Revenus par Champ (Millions FCFA)",
                           font=dict(color="#E8EDF5")),
                paper_bgcolor="#141B2D",
                plot_bgcolor="#141B2D",
                xaxis=dict(gridcolor="#1E2A42", color="#8B9BB4"),
                yaxis=dict(gridcolor="#1E2A42", color="#8B9BB4"),
                margin=dict(l=10, r=10, t=50, b=10)
            )
            st.plotly_chart(fig, width='stretch')

        with cd:
            fig2 = px.pie(
                rapport, values="Production_Totale", names="champ",
                title="Part de Production par Champ",
                color_discrete_sequence=["#F0A500","#00CC96","#FF4B4B","#636EFA"],
                hole=0.4
            )
            fig2.update_layout(
                paper_bgcolor="#141B2D",
                font=dict(color="#E8EDF5"),
                title_font=dict(color="#E8EDF5"),
                legend=dict(bgcolor="#1E2A42")
            )
            st.plotly_chart(fig2, width='stretch')

        st.markdown("""
        <div style="color:#8B9BB4; font-size:0.75rem; letter-spacing:1.5px;
                    text-transform:uppercase; margin:12px 0 8px 0;">
            Détail par Champ
        </div>
        """, unsafe_allow_html=True)

        aff = rapport.copy()
        aff["WaterCut_Moyen"]    = aff["WaterCut_Moyen"].map("{:.1%}".format)
        aff["Production_Totale"] = aff["Production_Totale"].map("{:,.0f} bbl".format)
        aff["Revenu_USD"]        = aff["Revenu_USD"].map("${:,.0f}".format)
        aff["Revenu_FCFA"]       = aff["Revenu_FCFA"].map("{:,.0f} FCFA".format)
        st.dataframe(aff, width='stretch', hide_index=True)
    else:
        st.info("Aucune donnée disponible pour cette période.")

# ════════════════════════════════════════════
# PAGE 4 — SAISIE DES DONNÉES
# ════════════════════════════════════════════
elif page == "📝  Saisie des Données":

    afficher_header("Saisie des Données",
                    "3 façons d'entrer vos données de production")

    onglet1, onglet2, onglet3 = st.tabs([
        "✏️  Saisie Manuelle",
        "📂  Import Excel / CSV",
        "🔗  URL / API / Coller"
    ])

    with onglet1:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="background:#1E2A42;border:1px solid rgba(240,165,0,0.19);
                    border-radius:10px;padding:14px 18px;margin-bottom:20px;
                    color:#8B9BB4;font-size:0.85rem;">
            📱 L'ingénieur terrain remplit ce formulaire depuis son téléphone
            chaque matin après relevé des compteurs.
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            date_saisie = st.date_input("📅 Date de production", value=date.today())
            puits_saisi = st.selectbox("🛢️ Puits", list(PROFILS_PUITS.keys()))
            champ_auto  = PROFILS_PUITS[puits_saisi]["champ"]
            st.markdown(
                f'<div style="background:#F0A50015;border:1px solid rgba(240,165,0,0.19);'
                f'border-radius:8px;padding:8px 14px;margin:4px 0 12px 0;'
                f'color:#F0A500;font-size:0.85rem;">Champ : <b>{champ_auto}</b></div>',
                unsafe_allow_html=True
            )
            production  = st.number_input("🛢️ Production huile (bbl/j)",
                                           min_value=0.0, value=5000.0, step=50.0)
            wc_pct      = st.slider("💧 Water Cut (%)", 0.0, 100.0, 35.0, 0.1)
            wc          = wc_pct / 100

        with col2:
            gor         = st.number_input("⛽ GOR (scf/stb)", min_value=0.0,
                                           value=800.0, step=10.0)
            pression    = st.number_input("🔧 Pression tête (psi)", min_value=0.0,
                                           value=380.0, step=5.0)
            temperature = st.number_input("🌡️ Température (°F)", min_value=0.0,
                                           value=175.0, step=1.0)
            heures      = st.slider("⏱️ Heures de production", 0, 24, 24)
            st.text_area("📝 Commentaire",
                          placeholder="Observations, incidents, interventions...")

        prod_eau = production * wc / max(1 - wc, 0.01)
        prod_gaz = production * gor / 1000
        statut   = ("Critique" if wc > 0.65 else
                    "Alerte"   if wc > 0.50 else "Actif")

        st.markdown("<br>", unsafe_allow_html=True)
        c1,c2,c3,c4 = st.columns(4)
        with c1: kpi_card("Huile",  f"{production:,.0f}", "bbl/j",  "#F0A500", "🛢️")
        with c2: kpi_card("Eau",    f"{prod_eau:,.0f}",   "bbl/j",  "#636EFA", "💧")
        with c3: kpi_card("Gaz",    f"{prod_gaz:.1f}",    "MMscf/j","#00CC96", "⛽")
        with c4: kpi_card("Statut", statut, "",
                           "#FF4B4B" if statut=="Critique" else
                           "#F0A500" if statut=="Alerte" else "#00CC96", "📊")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾  Enregistrer la mesure", type="primary",
                     width='stretch'):
            sauvegarder_mesure(
                date_saisie, puits_saisi, champ_auto,
                production, prod_gaz, prod_eau,
                wc, gor, pression, temperature, heures, statut
            )
            st.success(
                f"✅ Mesure enregistrée — **{puits_saisi}** | "
                f"{production:,.0f} bbl/j | WC: {wc_pct:.1f}% | "
                f"{date_saisie.strftime('%d/%m/%Y')}"
            )
            st.balloons()

    with onglet2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="background:#1E2A42;border:1px solid rgba(240,165,0,0.19);
                    border-radius:10px;padding:14px 18px;margin-bottom:20px;
                    color:#8B9BB4;font-size:0.85rem;">
            📂 Uploadez votre fichier Excel ou CSV mensuel.
            Toutes les données sont importées automatiquement.
        </div>
        """, unsafe_allow_html=True)

        modele = pd.DataFrame({
            "date":["2026-04-26","2026-04-26"],
            "puits":["Baleine-1","Sankofa-1"],
            "champ":["Baleine","Sankofa"],
            "production_huile_bbl":[8500,5200],
            "production_gaz_mmscf":[7.2,3.4],
            "production_eau_bbl":[4590,1300],
            "water_cut":[0.35,0.20],
            "gor":[850,650],
            "pression_tete_psi":[420,310],
            "temperature_f":[185,172],
            "heures_production":[24,24],
            "statut":["Actif","Actif"],
        })
        st.download_button("⬇️  Télécharger le modèle CSV",
                           data=modele.to_csv(index=False).encode("utf-8"),
                           file_name="modele_petroci.csv", mime="text/csv")

        st.divider()
        fichier = st.file_uploader("Uploader votre fichier",
                                    type=["xlsx","csv"])
        if fichier:
            try:
                df_import = (pd.read_csv(fichier)
                             if fichier.name.endswith(".csv")
                             else pd.read_excel(fichier))
                st.success(f"✅ **{len(df_import)} lignes** détectées")
                st.dataframe(df_import.head(), width='stretch')

                cols_req  = ["date","puits","champ","production_huile_bbl","water_cut"]
                manquants = [c for c in cols_req if c not in df_import.columns]
                if manquants:
                    st.error(f"❌ Colonnes manquantes : {manquants}")
                else:
                    if st.button("📥  Importer toutes les données",
                                 type="primary", width='stretch'):
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
                st.error(f"❌ Erreur : {e}")

    with onglet3:
        st.markdown("<br>", unsafe_allow_html=True)
        source = st.radio("Type de source", [
            "📋  Coller les données (CSV)",
            "📎  URL fichier CSV",
            "🔌  API JSON"
        ])

        if source == "📋  Coller les données (CSV)":
            st.caption("Format : date,puits,champ,production_huile_bbl,water_cut,statut")
            donnees = st.text_area("Données CSV", height=180,
                placeholder=(
                    "date,puits,champ,production_huile_bbl,water_cut,statut\n"
                    "2026-04-26,Baleine-1,Baleine,8500,0.35,Actif\n"
                    "2026-04-26,Sankofa-1,Sankofa,5200,0.20,Actif"
                ))
            if donnees and st.button("📥  Importer", type="primary",
                                      width='stretch'):
                try:
                    from io import StringIO
                    df_c   = pd.read_csv(StringIO(donnees))
                    conn   = sqlite3.connect(DB_PATH, check_same_thread=False)
                    succes = 0
                    for _, row in df_c.iterrows():
                        try:
                            conn.cursor().execute("""
                                INSERT OR REPLACE INTO production_journaliere
                                (date,puits,champ,production_huile_bbl,water_cut,statut)
                                VALUES (?,?,?,?,?,?)
                            """, (str(row.get("date","")), str(row.get("puits","")),
                                  str(row.get("champ","")),
                                  float(row.get("production_huile_bbl",0)),
                                  float(row.get("water_cut",0)),
                                  str(row.get("statut","Actif"))))
                            succes += 1
                        except Exception:
                            pass
                    conn.commit(); conn.close()
                    st.success(f"✅ {succes} lignes importées")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ {e}")

        elif source == "📎  URL fichier CSV":
            url = st.text_input("URL", placeholder="https://...")
            if url and st.button("📥  Charger", type="primary"):
                try:
                    df_url = pd.read_csv(url)
                    st.success(f"✅ {len(df_url)} lignes")
                    st.dataframe(df_url.head())
                except Exception as e:
                    st.error(f"❌ {e}")
        else:
            url_api = st.text_input("URL API", placeholder="https://api...")
            token   = st.text_input("Token", type="password")
            if url_api and st.button("🔌  Appeler", type="primary"):
                try:
                    import urllib.request, json
                    h   = {"Authorization": f"Bearer {token}"} if token else {}
                    req = urllib.request.Request(url_api, headers=h)
                    with urllib.request.urlopen(req, timeout=10) as r:
                        data = json.loads(r.read())
                    df_api = pd.DataFrame(data if isinstance(data, list)
                                          else data.get("data",[data]))
                    st.success(f"✅ {len(df_api)} enregistrements")
                    st.dataframe(df_api.head())
                except Exception as e:
                    st.error(f"❌ {e}")

# ════════════════════════════════════════════
# PAGE 5 — ALERTES
# ════════════════════════════════════════════
elif page == "⚠️  Alertes":

    afficher_header("Système d'Alertes",
                    "Surveillance en temps réel des seuils critiques")

    if st.button("🔍  Vérifier toutes les alertes", width='stretch'):
        nb = len(verifier_alertes())
        st.success(f"✅ Vérification terminée — {nb} alertes générées")

    df_al = lire_alertes(resolues=False)

    if not df_al.empty:
        c1,c2,c3 = st.columns(3)
        with c1: kpi_card("Total Alertes", str(len(df_al)),
                           "actives", "#F0A500", "⚠️")
        with c2: kpi_card("Critiques",
                           str(int((df_al["niveau"]=="CRITIQUE").sum())),
                           "intervention requise", "#FF4B4B", "🔴")
        with c3: kpi_card("Alertes",
                           str(int((df_al["niveau"]=="ALERTE").sum())),
                           "surveillance", "#F0A500", "⚠️")

        st.markdown("<br>", unsafe_allow_html=True)

        for _, a in df_al[df_al["niveau"]=="CRITIQUE"].iterrows():
            st.markdown(f"""
            <div style="background:#FF4B4B10;border:1px solid rgba(255,75,75,0.25);
                        border-left:4px solid #FF4B4B;border-radius:8px;
                        padding:12px 16px;margin:6px 0;color:#E8EDF5;">
                🔴 <b>CRITIQUE</b> &nbsp;|&nbsp; <b>{a['puits']}</b>
                ({a['champ']}) &nbsp;|&nbsp; {a['type_alerte']}
                <br><span style="color:#8B9BB4;font-size:0.85rem;">
                {a['message']}</span>
            </div>
            """, unsafe_allow_html=True)

        for _, a in df_al[df_al["niveau"]=="ALERTE"].iterrows():
            st.markdown(f"""
            <div style="background:#F0A50010;border:1px solid rgba(240,165,0,0.25);
                        border-left:4px solid #F0A500;border-radius:8px;
                        padding:12px 16px;margin:6px 0;color:#E8EDF5;">
                ⚠️ <b>ALERTE</b> &nbsp;|&nbsp; <b>{a['puits']}</b>
                ({a['champ']}) &nbsp;|&nbsp; {a['type_alerte']}
                <br><span style="color:#8B9BB4;font-size:0.85rem;">
                {a['message']}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background:#00CC9610;border:1px solid #00CC9640;
                    border-radius:10px;padding:20px;text-align:center;
                    color:#00CC96;font-size:1.1rem;margin-top:20px;">
            ✅ Aucune alerte active — Tous les puits fonctionnent normalement
        </div>
        """, unsafe_allow_html=True)

# ════════════════════════════════════════════
# PAGE 6 — DÉCLIN & PRÉVISIONS
# ════════════════════════════════════════════
elif page == "📈  Déclin & Prévisions":

    afficher_header("Déclin & Prévisions",
                    "Analyse de performance et tendances de production")

    puits_choisi = st.selectbox("Choisir un puits",
                                 list(PROFILS_PUITS.keys()))
    declin       = calculer_declin(puits_choisi, nb_jours)

    if declin:
        c1,c2,c3,c4 = st.columns(4)
        with c1: kpi_card("Production Début",
                           f"{declin['production_debut']:,.0f}", "bbl/j",
                           "#636EFA", "📅")
        with c2: kpi_card("Production Actuelle",
                           f"{declin['production_actuelle']:,.0f}", "bbl/j",
                           "#F0A500", "🛢️")
        with c3: kpi_card("Déclin Total",
                           f"{declin['declin_total_pct']:.1f}%", "",
                           "#FF4B4B", "📉")
        with c4: kpi_card("Déclin Mensuel",
                           f"{declin['declin_mensuel_pct']:.1f}%", "par mois",
                           "#FF4B4B", "📊")

    df_p = lire_production(date_debut=str(date_debut),
                            date_fin=str(date_fin), puits=puits_choisi)

    if not df_p.empty:
        df_p = df_p.sort_values("date")
        fig  = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_p["date"], y=df_p["production_huile_bbl"],
            name="Production Huile", mode="lines",
            fill="tozeroy", fillcolor="rgba(240,165,0,0.08)",
            line=dict(color="#F0A500", width=2.5)
        ))
        fig.add_trace(go.Scatter(
            x=df_p["date"],
            y=df_p["water_cut"].astype(float) *
              df_p["production_huile_bbl"].astype(float).max(),
            name="Water Cut (normalisé)", mode="lines",
            line=dict(color="#FF4B4B", width=1.5, dash="dash")
        ))
        fig.update_layout(
            title=dict(text=f"Courbe de Déclin — {puits_choisi}",
                       font=dict(color="#E8EDF5")),
            paper_bgcolor="#141B2D",
            plot_bgcolor="#141B2D",
            xaxis=dict(gridcolor="#1E2A42", color="#8B9BB4"),
            yaxis=dict(gridcolor="#1E2A42", color="#8B9BB4",
                       title="Production (bbl/jour)"),
            legend=dict(bgcolor="#1E2A42", bordercolor="rgba(240,165,0,0.2)",
                        font=dict(color="#E8EDF5")),
            hovermode="x unified",
            margin=dict(l=10, r=10, t=50, b=10)
        )
        st.plotly_chart(fig, width='stretch')
    else:
        st.info("Aucune donnée pour ce puits sur la période sélectionnée.")

# ════════════════════════════════════════════
# PAGE 7 — RAPPORTS
# ════════════════════════════════════════════
elif page == "📋  Rapports":

    afficher_header("Génération de Rapports",
                    "Rapports automatiques exportables")

    type_r = st.selectbox("Type de rapport", [
        "Rapport Production par Champ",
        "Rapport Performance Opérateurs",
        "Rapport Alertes Actives",
    ])

    if st.button("📄  Générer le Rapport", type="primary",
                 width='stretch'):
        with st.spinner("Génération en cours..."):
            rapport = production_par_champ(nb_jours)
            st.markdown(f"""
            <div style="background:#1E2A42;border:1px solid rgba(240,165,0,0.19);
                        border-radius:10px;padding:16px 20px;margin:16px 0;">
                <div style="color:#F0A500;font-size:1rem;font-weight:700;
                            margin-bottom:8px;">📊 {type_r}</div>
                <div style="color:#8B9BB4;font-size:0.8rem;">
                    Période : {date_debut} → {date_fin} &nbsp;|&nbsp;
                    Généré le : {date.today().strftime('%d/%m/%Y')}
                </div>
            </div>
            """, unsafe_allow_html=True)

            if not rapport.empty:
                prod_tot = rapport["Production_Totale"].sum()
                rev_tot  = rapport["Revenu_USD"].sum()

                c1,c2,c3 = st.columns(3)
                with c1: kpi_card("Production",
                                   f"{prod_tot:,.0f}", "bbl", "#F0A500","🛢️")
                with c2: kpi_card("Revenus USD",
                                   f"${rev_tot:,.0f}", "", "#00CC96","💵")
                with c3: kpi_card("Revenus FCFA",
                                   f"{rev_tot*TAUX/1e9:.2f} Mds", "", "#636EFA","💶")

                st.markdown("<br>", unsafe_allow_html=True)

                if type_r == "Rapport Performance Opérateurs":
                    df_op = lire_production(date_debut=str(date_debut),
                                             date_fin=str(date_fin))
                    if not df_op.empty:
                        from config import CHAMPS
                        df_op["operateur"] = df_op["champ"].map(
                            {k:v["operateur"] for k,v in CHAMPS.items()}
                        )
                        grp = df_op.groupby("operateur").agg(
                            Production=("production_huile_bbl","sum"),
                            WC_Moyen  =("water_cut","mean"),
                            Nb_Puits  =("puits","nunique")
                        ).reset_index()
                        st.dataframe(grp, width='stretch', hide_index=True)

                elif type_r == "Rapport Alertes Actives":
                    df_al = lire_alertes(resolues=False)
                    (st.dataframe(df_al, width='stretch', hide_index=True)
                     if not df_al.empty else st.success("Aucune alerte active."))
                else:
                    aff = rapport.copy()
                    aff["WaterCut_Moyen"]    = aff["WaterCut_Moyen"].map("{:.1%}".format)
                    aff["Production_Totale"] = aff["Production_Totale"].map("{:,.0f}".format)
                    aff["Revenu_USD"]        = aff["Revenu_USD"].map("${:,.0f}".format)
                    st.dataframe(aff, width='stretch', hide_index=True)

                fig = go.Figure(go.Bar(
                    x=rapport["champ"],
                    y=rapport["Production_Totale"],
                    text=[f"{v:,.0f}" for v in rapport["Production_Totale"]],
                    textposition="outside",
                    textfont=dict(color="#E8EDF5"),
                    marker=dict(color=["#F0A500","#00CC96","#FF4B4B","#636EFA"])
                ))
                fig.update_layout(
                    paper_bgcolor="#141B2D", plot_bgcolor="#141B2D",
                    xaxis=dict(gridcolor="#1E2A42", color="#8B9BB4"),
                    yaxis=dict(gridcolor="#1E2A42", color="#8B9BB4"),
                    title=dict(text="Production par Champ (bbl)",
                               font=dict(color="#E8EDF5")),
                    margin=dict(l=10, r=10, t=50, b=10)
                )
                st.plotly_chart(fig, width='stretch')

                st.download_button(
                    "⬇️  Télécharger CSV",
                    data=rapport.to_csv(index=False).encode("utf-8"),
                    file_name=f"rapport_petroci_{date.today()}.csv",
                    mime="text/csv", width='stretch'
                )
            else:
                st.warning("Aucune donnée disponible.")
