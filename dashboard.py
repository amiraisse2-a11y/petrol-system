# dashboard.py — PETRO AFRICA v2.0
# Systeme complet de gestion de production petroliere CI

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta
import sqlite3
import io

# ════════════════════════════════════════════
# CONFIG PAGE
# ════════════════════════════════════════════
st.set_page_config(
    page_title="PETRO AFRICA — Production System",
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ════════════════════════════════════════════
# CSS GLOBAL — BLANC / ORANGE / MOBILE
# ════════════════════════════════════════════
st.markdown("""
<style>
/* ── Global ── */
.stApp { background-color: #F4F6F9; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg,#FFFFFF 0%,#FFF8F0 100%);
    border-right: 2px solid rgba(224,123,0,0.15);
}

/* ── Boutons ── */
.stButton > button {
    background: linear-gradient(135deg,#E07B00,#F0A500) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    box-shadow: 0 3px 10px rgba(224,123,0,0.3) !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 5px 15px rgba(224,123,0,0.45) !important;
}

/* ── Tabs ── */
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #E07B00 !important;
    border-bottom: 3px solid #E07B00 !important;
    font-weight: 700 !important;
}
[data-testid="stTabs"] button { color: #666 !important; }

/* ── Mobile ── */
@media (max-width: 768px) {
    [data-testid="stSidebar"] { width: 280px !important; }
    .block-container { padding: 8px 12px !important; }
    h1 { font-size: 1.2rem !important; }
    h2 { font-size: 1rem !important; }
}

/* ── Download ── */
[data-testid="stDownloadButton"] button {
    background: linear-gradient(135deg,#1A5276,#2E86C1) !important;
    color: white !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    border: 2px dashed rgba(224,123,0,0.4) !important;
    border-radius: 10px !important;
    background: #FFF8F0 !important;
}

/* ── Mode impression ── */
@media print {
    [data-testid="stSidebar"],
    .stButton, header, footer { display: none !important; }
    .main { margin: 0 !important; padding: 0 !important; }
    .block-container { max-width: 100% !important; }
}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════
# IMPORTS MODULES
# ════════════════════════════════════════════
from auth import (afficher_page_login, verifier_session,
                   get_user, deconnecter, verifier_acces_champ)
from database import (initialiser_sqlite, peupler_puits,
                       lire_puits, lire_production,
                       lire_alertes, sauvegarder_production,
                       lire_drilling)
from data_real_ci import (generer_donnees_realistes,
                            generer_donnees_drilling)
from analytics import (kpis_journaliers, production_par_champ,
                        calculer_declin, historique_champs,
                        analyse_benchmark)
from alerts import (verifier_alertes, resume_alertes,
                     envoyer_email_alerte, envoyer_rapport_quotidien)
from reports import generer_rapport_pdf
from config import (PRIX_BARIL, TAUX, PROFILS_PUITS,
                     CHAMPS_PRODUCTION, BLOCS_EXPLORATION,
                     BENCHMARKS, SEUILS)

DB_PATH = "petro_africa.db"

# ════════════════════════════════════════════
# INITIALISATION
# ════════════════════════════════════════════
@st.cache_resource
def setup():
    initialiser_sqlite()
    peupler_puits()
    generer_donnees_realistes(730)
    generer_donnees_drilling()
    return True

setup()

# ════════════════════════════════════════════
# AUTHENTIFICATION
# ════════════════════════════════════════════
if not verifier_session():
    afficher_page_login()
    st.stop()

user = get_user()

# ════════════════════════════════════════════
# COMPOSANTS UI
# ════════════════════════════════════════════
COLORS = {
    "Baleine": "#E07B00", "Sankofa": "#27AE60",
    "Foxtrot": "#E74C3C", "Baobab":  "#2E86C1",
    "Lion":    "#8E44AD", "Panthere":"#16A085",
    "defaut":  ["#E07B00","#27AE60","#E74C3C",
                "#2E86C1","#8E44AD","#16A085"]
}
LAYOUT = dict(
    paper_bgcolor="white", plot_bgcolor="#FAFAFA",
    font=dict(color="#333", size=11),
    margin=dict(l=10, r=10, t=55, b=10)
)
CFG_PLOTLY = {"displayModeBar": False}

def header(titre, sous=""):
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#E07B00,#F0A500);
                border-radius:10px;padding:18px 24px;
                margin-bottom:20px;
                box-shadow:0 4px 15px rgba(224,123,0,0.2);">
        <div style="color:white;font-size:1.4rem;font-weight:800;
                    letter-spacing:0.3px;">{titre}</div>
        <div style="color:rgba(255,255,255,0.85);font-size:0.78rem;
                    margin-top:3px;">{sous}</div>
    </div>""", unsafe_allow_html=True)

def kpi(label, valeur, sous="", couleur="#E07B00", icone=""):
    icone_html = (f'<div style="font-size:1.4rem;margin-bottom:5px;">'
                  f'{icone}</div>') if icone else ""
    st.markdown(f"""
    <div style="background:white;border-top:4px solid {couleur};
                border-radius:10px;padding:16px;text-align:center;
                box-shadow:0 2px 8px rgba(0,0,0,0.06);
                margin-bottom:8px;">
        {icone_html}
        <div style="color:#999;font-size:0.65rem;letter-spacing:1.5px;
                    text-transform:uppercase;font-weight:600;
                    margin-bottom:5px;">{label}</div>
        <div style="color:{couleur};font-size:1.4rem;font-weight:800;
                    line-height:1.1;">{valeur}</div>
        <div style="color:#BBB;font-size:0.7rem;margin-top:3px;">
            {sous}</div>
    </div>""", unsafe_allow_html=True)

def badge(niveau):
    cfg = {
        "CRITIQUE": ("#CC0000","#FFF0F0","Critique"),
        "ALERTE":   ("#CC7700","#FFFBF0","Alerte"),
        "Actif":    ("#1A7A4A","#E8F8F0","Actif"),
        "Arret":    ("#555","#F0F0F0","Arret"),
    }.get(niveau, ("#666","#F5F5F5", niveau))
    return (f'<span style="background:{cfg[1]};color:{cfg[0]};'
            f'padding:3px 10px;border-radius:20px;font-size:0.75rem;'
            f'font-weight:700;border:1px solid {cfg[0]}40;">'
            f'{cfg[2]}</span>')

# ════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════
st.sidebar.markdown(f"""
<div style="text-align:center;padding:16px 0 10px 0;">
    <div style="font-size:2.5rem;">🛢️</div>
    <div style="color:#E07B00;font-size:1.2rem;font-weight:800;
                letter-spacing:3px;margin:6px 0 2px 0;">PETRO AFRICA</div>
    <div style="color:#AAA;font-size:0.65rem;letter-spacing:2px;">
        PRODUCTION SYSTEM v2.0</div>
</div>
<div style="background:#FFF8F0;border-radius:8px;padding:8px 12px;
            margin:8px 4px;font-size:0.78rem;color:#666;">
    <b style="color:#E07B00;">{user.get('nom','')}</b><br>
    {user.get('compagnie','')} — {user.get('role','').upper()}
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown(
    '<hr style="border-color:rgba(224,123,0,0.2);margin:8px 0;">',
    unsafe_allow_html=True
)

PAGES = [
    "Tableau de Bord",
    "Puits et Champs",
    "Exploration",
    "Analyse Production",
    "Saisie des Donnees",
    "Previsions ML",
    "Forage DDR",
    "Benchmarks",
    "Alertes",
    "Rapports",
]

page = st.sidebar.radio("", PAGES, label_visibility="collapsed")

st.sidebar.markdown(
    '<hr style="border-color:rgba(224,123,0,0.2);margin:8px 0;">',
    unsafe_allow_html=True
)

champ_filtre = st.sidebar.selectbox(
    "Champ",
    ["Tous"] + list(CHAMPS_PRODUCTION.keys()),
    label_visibility="collapsed"
)
periode_label = st.sidebar.selectbox(
    "Periode",
    ["7 jours","30 jours","90 jours","365 jours","730 jours"],
    index=1,
    label_visibility="collapsed"
)
nb_jours   = int(periode_label.split()[0])
date_fin   = date.today()
date_debut = date_fin - timedelta(days=nb_jours)

if st.sidebar.button("Actualiser", use_container_width=True):
    alertes = verifier_alertes()
    if alertes:
        ok, msg = envoyer_email_alerte(alertes)
    st.rerun()

resume = resume_alertes()
if resume["critiques"] > 0:
    st.sidebar.markdown(
        f'<div style="background:#FFF0F0;border:1px solid #FF000040;'
        f'border-radius:8px;padding:8px 12px;margin:4px 0;'
        f'color:#CC0000;font-size:0.8rem;font-weight:600;">'
        f'CRITIQUE : {resume["critiques"]} alerte(s)</div>',
        unsafe_allow_html=True
    )
if resume["alertes"] > 0:
    st.sidebar.markdown(
        f'<div style="background:#FFFBF0;border:1px solid #F0A50040;'
        f'border-radius:8px;padding:8px 12px;margin:4px 0;'
        f'color:#CC7700;font-size:0.8rem;font-weight:600;">'
        f'ALERTE : {resume["alertes"]} alerte(s)</div>',
        unsafe_allow_html=True
    )

if st.sidebar.button("Deconnexion", use_container_width=True):
    deconnecter()

st.sidebar.markdown(
    '<div style="text-align:center;color:#CCC;font-size:0.62rem;'
    'margin-top:30px;">PETRO AFRICA © 2026</div>',
    unsafe_allow_html=True
)

# ════════════════════════════════════════════
# PAGE 1 — TABLEAU DE BORD
# ════════════════════════════════════════════
if page == "Tableau de Bord":

    header(
        "Tableau de Bord Production",
        f"Donnees au {date.today().strftime('%d %B %Y')} — "
        f"Champs offshore Cote d'Ivoire"
    )

    kpis = kpis_journaliers()
    if kpis:
        c1,c2,c3,c4,c5,c6 = st.columns(6)
        with c1: kpi("Production", f"{kpis['production_totale_bbl']:,.0f}",
                      "bbl/jour", "#E07B00", "🛢️")
        with c2: kpi("Revenu USD", f"${kpis['revenu_journalier_usd']:,.0f}",
                      "par jour", "#27AE60", "💵")
        with c3: kpi("En FCFA",
                      f"{kpis['revenu_journalier_xof']/1e6:.0f}M",
                      "FCFA/jour", "#27AE60", "💶")
        with c4: kpi("Puits Actifs",
                      str(kpis["nb_puits_actifs"]), "", "#2E86C1", "✅")
        with c5: kpi("Alertes",
                      str(kpis["nb_puits_alerte"]), "", "#F0A500", "⚠️")
        with c6: kpi("Uptime",
                      f"{kpis.get('uptime_moyen',0):.1f}%",
                      "cible 95%", "#8E44AD", "📊")

    st.markdown("<br>", unsafe_allow_html=True)

    df_hist = historique_champs(nb_jours)
    if not df_hist.empty:
        cg, cd = st.columns(2)
        with cg:
            df_t = (df_hist.groupby("date")["production_huile_bbl"]
                    .sum().reset_index())
            fig = go.Figure(go.Scatter(
                x=df_t["date"], y=df_t["production_huile_bbl"],
                fill="tozeroy",
                fillcolor="rgba(224,123,0,0.1)",
                line=dict(color="#E07B00", width=2.5),
                name="Production CI"
            ))
            fig.update_layout(
                title="Production Totale CI",
                xaxis=dict(gridcolor="#EEE", color="#888"),
                yaxis=dict(gridcolor="#EEE", color="#888",
                           title="bbl/jour"),
                hovermode="x unified", **LAYOUT
            )
            st.plotly_chart(fig, use_container_width=True,
                            config=CFG_PLOTLY)

        with cd:
            fig2 = go.Figure()
            for ch in df_hist["champ"].unique():
                df_c = df_hist[df_hist["champ"]==ch]
                fig2.add_trace(go.Scatter(
                    x=df_c["date"],
                    y=df_c["production_huile_bbl"],
                    name=ch, mode="lines",
                    line=dict(color=COLORS.get(ch,"#666"), width=2)
                ))
            fig2.update_layout(
                title="Production par Champ",
                xaxis=dict(gridcolor="#EEE", color="#888"),
                yaxis=dict(gridcolor="#EEE", color="#888"),
                legend=dict(bgcolor="white",
                            bordercolor="rgba(224,123,0,0.3)"),
                hovermode="x unified", **LAYOUT
            )
            st.plotly_chart(fig2, use_container_width=True,
                            config=CFG_PLOTLY)

        # ── Ligne 2 : Gaz + Water Cut ──────────────────────────
        cg2, cd2 = st.columns(2)
        with cg2:
            df_gaz = (df_hist.groupby("date")["production_gaz_mmscf"]
                      .sum().reset_index())
            fig_gaz = go.Figure(go.Scatter(
                x=df_gaz["date"], y=df_gaz["production_gaz_mmscf"],
                fill="tozeroy",
                fillcolor="rgba(39,174,96,0.12)",
                line=dict(color="#27AE60", width=2.5),
                name="Gaz CI"
            ))
            fig_gaz.update_layout(
                title="Production Gaz Totale CI",
                xaxis=dict(gridcolor="#EEE", color="#888"),
                yaxis=dict(gridcolor="#EEE", color="#888",
                           title="MMscf/jour"),
                hovermode="x unified", **LAYOUT
            )
            st.plotly_chart(fig_gaz, use_container_width=True,
                            config=CFG_PLOTLY)

        with cd2:
            fig_wc = go.Figure()
            for ch in df_hist["champ"].unique():
                df_c = df_hist[df_hist["champ"] == ch]
                df_wc = df_c.groupby("date")["water_cut"].mean().reset_index()
                fig_wc.add_trace(go.Scatter(
                    x=df_wc["date"],
                    y=df_wc["water_cut"] * 100,
                    name=ch, mode="lines",
                    line=dict(color=COLORS.get(ch, "#666"), width=2)
                ))
            fig_wc.add_hline(y=70, line_dash="dash",
                             line_color="#E74C3C",
                             annotation_text="Seuil critique 70%")
            fig_wc.update_layout(
                title="Water Cut par Champ (%)",
                xaxis=dict(gridcolor="#EEE", color="#888"),
                yaxis=dict(gridcolor="#EEE", color="#888",
                           title="%", range=[0, 100]),
                legend=dict(bgcolor="white",
                            bordercolor="rgba(224,123,0,0.3)"),
                hovermode="x unified", **LAYOUT
            )
            st.plotly_chart(fig_wc, use_container_width=True,
                            config=CFG_PLOTLY)

    # Carte offshore CI
    st.markdown(
        '<div style="color:#999;font-size:0.7rem;letter-spacing:1.5px;'
        'text-transform:uppercase;margin:8px 0 10px 0;font-weight:600;">'
        'Localisation des Puits et Blocs Offshore CI</div>',
        unsafe_allow_html=True
    )
    df_puits = lire_puits()
    if not df_puits.empty and "latitude" in df_puits.columns:
        couleurs = {
            "Actif":"#27AE60","Alerte":"#F0A500",
            "Critique":"#E74C3C","Fin de vie":"#8E44AD","Arret":"#888"
        }
        fig_map = px.scatter_map(
            df_puits, lat="latitude", lon="longitude",
            color="statut", hover_name="nom_puits",
            hover_data=["champ","operateur","statut"],
            color_discrete_map=couleurs,
            zoom=6, center={"lat":4.2,"lon":-3.8}
        )
        # Ajouter blocs exploration
        blocs_data = []
        for nom, b in BLOCS_EXPLORATION.items():
            blocs_data.append({
                "nom": nom, "lat": b["lat"], "lon": b["lon"],
                "statut": b["statut"], "potentiel": b["potentiel"]
            })
        df_blocs = pd.DataFrame(blocs_data)
        fig_map.add_trace(go.Scattermap(
            lat=df_blocs["lat"], lon=df_blocs["lon"],
            mode="markers+text",
            marker=dict(size=12, color="#9B59B6", symbol="star"),
            text=df_blocs["nom"],
            textposition="top right",
            name="Blocs Exploration",
            hovertext=df_blocs["nom"] + "<br>" + df_blocs["statut"]
        ))
        fig_map.update_layout(
            map_style="open-street-map",
            height=480,
            paper_bgcolor="white",
            margin=dict(l=0,r=0,t=0,b=0),
            legend=dict(bgcolor="white",
                        bordercolor="rgba(224,123,0,0.3)",
                        font=dict(color="#333"))
        )
        st.plotly_chart(fig_map, use_container_width=True,
                        config={"displayModeBar": True,
                                "modeBarButtonsToRemove":
                                ["select2d","lasso2d"]})

# ════════════════════════════════════════════
# PAGE 2 — PUITS ET CHAMPS
# ════════════════════════════════════════════
elif page == "Puits et Champs":

    header("Puits et Champs Petroliers",
           "Actifs en production — Cote d'Ivoire Offshore")

    champ_q = None if champ_filtre=="Tous" else champ_filtre
    df      = lire_puits(champ=champ_q)

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: kpi("Total Puits", str(len(df)), "", "#2E86C1", "🛢️")
    with c2: kpi("Actifs",
                  str(int((df["statut"]=="Actif").sum()) if not df.empty else 0),
                  "", "#27AE60", "✅")
    with c3: kpi("Alertes",
                  str(int((df["statut"]=="Alerte").sum()) if not df.empty else 0),
                  "", "#F0A500", "⚠️")
    with c4: kpi("Critiques",
                  str(int((df["statut"]=="Critique").sum()) if not df.empty else 0),
                  "", "#E74C3C", "🔴")
    with c5: kpi("Fin de vie",
                  str(int((df["statut"]=="Fin de vie").sum()) if not df.empty else 0),
                  "", "#8E44AD", "📉")

    st.markdown("<br>", unsafe_allow_html=True)

    # Info champs
    if champ_filtre != "Tous" and champ_filtre in CHAMPS_PRODUCTION:
        info = CHAMPS_PRODUCTION[champ_filtre]
        st.markdown(f"""
        <div style="background:white;border-left:5px solid #E07B00;
                    border-radius:0 10px 10px 0;padding:14px 18px;
                    margin-bottom:16px;">
            <div style="color:#E07B00;font-weight:700;font-size:1rem;">
                Champ {champ_filtre}
            </div>
            <div style="color:#666;font-size:0.85rem;margin-top:4px;">
                {info.get('description','')}
            </div>
            <div style="display:flex;gap:20px;margin-top:8px;
                        font-size:0.8rem;color:#888;">
                <span>Operateur : <b>{info.get('operateur','')}</b></span>
                <span>Statut : <b>{info.get('statut','')}</b></span>
                <span>Prof. eau : <b>{info.get('profondeur_eau_m','')}m</b></span>
                <span>Reserves : <b>{info.get('reserves_MMbbl','')} MMbbl</b></span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    def style_statut(val):
        m = {"Critique":   "background:#FFE8E8;color:#CC0000;font-weight:700",
             "Alerte":     "background:#FFF8E8;color:#CC7700;font-weight:700",
             "Fin de vie": "background:#F5E8FF;color:#7D3C98;font-weight:700",
             "Arret":      "background:#F0F0F0;color:#555;font-weight:700"}
        return m.get(val, "background:#E8F8F0;color:#1A7A4A;font-weight:700")

    cols_aff = [c for c in
        ["nom_puits","champ","operateur","type_puits",
         "statut","date_forage","profondeur_totale_m"]
        if c in df.columns]
    df_aff = df[cols_aff].copy()
    if "date_forage" in df_aff.columns:
        df_aff["date_forage"] = df_aff["date_forage"].fillna("N/A")

    st.dataframe(
        df_aff.style.map(style_statut, subset=["statut"])
        if not df_aff.empty else df_aff,
        use_container_width=True, hide_index=True
    )

    if not df.empty:
        cg, cd = st.columns(2)
        with cg:
            fig = px.pie(df, names="champ",
                         title="Repartition par Champ",
                         color_discrete_sequence=COLORS["defaut"])
            fig.update_layout(**LAYOUT)
            st.plotly_chart(fig, use_container_width=True,
                            config=CFG_PLOTLY)
        with cd:
            cnt  = (df.groupby(["champ","statut"])
                    .size().reset_index(name="n"))
            fig2 = px.bar(cnt, x="champ", y="n", color="statut",
                          title="Statut par Champ",
                          color_discrete_map={
                              "Actif":"#27AE60","Alerte":"#F0A500",
                              "Critique":"#E74C3C","Fin de vie":"#8E44AD"
                          })
            fig2.update_layout(
                xaxis=dict(gridcolor="#EEE"),
                yaxis=dict(gridcolor="#EEE"), **LAYOUT
            )
            st.plotly_chart(fig2, use_container_width=True,
                            config=CFG_PLOTLY)

# ════════════════════════════════════════════
# PAGE 3 — EXPLORATION
# ════════════════════════════════════════════
elif page == "Exploration":

    header("Blocs en Exploration",
           "Nouveaux blocs et activite exploratoire CI 2024-2026")

    c1,c2,c3 = st.columns(3)
    with c1: kpi("Blocs Actifs", str(len(BLOCS_EXPLORATION)),
                  "", "#8E44AD", "🔍")
    with c2: kpi("En Appraisal",
                  str(sum(1 for b in BLOCS_EXPLORATION.values()
                          if b["statut"]=="Appraisal")),
                  "", "#E07B00", "📊")
    with c3: kpi("En Forage",
                  str(sum(1 for b in BLOCS_EXPLORATION.values()
                          if b["phase"]=="Forage exploratoire")),
                  "", "#27AE60", "⛏️")

    st.markdown("<br>", unsafe_allow_html=True)

    # Tableau blocs
    data_blocs = []
    for nom, b in BLOCS_EXPLORATION.items():
        data_blocs.append({
            "Bloc": nom,
            "Operateur": b["operateur"],
            "Statut": b["statut"],
            "Phase": b["phase"],
            "Potentiel": b["potentiel"],
            "Description": b["description"]
        })
    df_blocs = pd.DataFrame(data_blocs)
    st.dataframe(df_blocs, use_container_width=True, hide_index=True)

    # Carte des blocs
    st.markdown("<br>", unsafe_allow_html=True)
    lats = [b["lat"] for b in BLOCS_EXPLORATION.values()]
    lons = [b["lon"] for b in BLOCS_EXPLORATION.values()]
    noms = list(BLOCS_EXPLORATION.keys())
    stat = [b["statut"] for b in BLOCS_EXPLORATION.values()]

    fig_blocs = px.scatter_map(
        pd.DataFrame({"lat":lats,"lon":lons,
                      "nom":noms,"statut":stat}),
        lat="lat", lon="lon",
        color="statut", hover_name="nom",
        color_discrete_map={
            "Appraisal":"#E07B00",
            "Exploration":"#8E44AD"
        },
        zoom=6, center={"lat":4.2,"lon":-3.8},
        title="Blocs en Exploration CI"
    )
    fig_blocs.update_layout(
        map_style="open-street-map",
        height=400, paper_bgcolor="white",
        margin=dict(l=0,r=0,t=0,b=0)
    )
    st.plotly_chart(fig_blocs, use_container_width=True,
                    config=CFG_PLOTLY)

    # Focus Baleine Deep
    st.markdown("""
    <div style="background:linear-gradient(135deg,#FFF8F0,#FFFDF5);
                border:1px solid rgba(224,123,0,0.3);border-radius:10px;
                padding:18px 22px;margin-top:16px;">
        <div style="color:#E07B00;font-weight:800;font-size:1rem;
                    margin-bottom:8px;">
            Focus : Baleine Deep (CI-101 Deep)
        </div>
        <div style="color:#555;font-size:0.85rem;line-height:1.6;">
            La decouverte Baleine en 2021 par ENI est la plus grande
            decouverte petroliere africaine depuis des decennies.
            Le potentiel estime depasse <b>1.5 milliard de barils</b>.
            Les operations d'appraisal en cours sur CI-101 Deep
            visent a confirmer l'extension du reservoir.
            Premier petrole depuis janvier 2023. Production en rampe.
        </div>
        <div style="display:flex;gap:24px;margin-top:10px;
                    font-size:0.8rem;color:#888;">
            <span>Reserves confirmees : <b style="color:#E07B00;">
                2.5 Milliards bbl</b></span>
            <span>Operateur : <b>ENI / PETROCI</b></span>
            <span>Phase : <b>Production + Appraisal</b></span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ════════════════════════════════════════════
# PAGE 4 — ANALYSE PRODUCTION
# ════════════════════════════════════════════
elif page == "Analyse Production":

    header("Analyse de Production",
           f"Performance sur {periode_label}")

    rapport = production_par_champ(nb_jours)

    if not rapport.empty:
        c1,c2,c3,c4 = st.columns(4)
        with c1: kpi("Production Totale",
                      f"{rapport['Production_Totale'].sum():,.0f}",
                      "barils", "#E07B00", "🛢️")
        with c2: kpi("Revenus USD",
                      f"${rapport['Revenu_USD'].sum():,.0f}",
                      "", "#27AE60", "💵")
        with c3: kpi("Revenus FCFA",
                      f"{rapport['Revenu_FCFA'].sum()/1e9:.2f} Mds",
                      "FCFA", "#2E86C1", "💶")
        with c4: kpi("Marge Brute",
                      f"${rapport['Marge_USD'].sum():,.0f}",
                      f"soit {rapport['Marge_USD'].sum()/rapport['Revenu_USD'].sum()*100:.0f}%",
                      "#8E44AD", "📈")

        st.markdown("<br>", unsafe_allow_html=True)
        cg, cd = st.columns(2)

        with cg:
            fig = go.Figure(go.Bar(
                x=rapport["champ"],
                y=rapport["Revenu_FCFA"]/1e6,
                text=[f"{v/1e6:.0f}M" for v in rapport["Revenu_FCFA"]],
                textposition="outside",
                marker=dict(color=COLORS["defaut"])
            ))
            fig.update_layout(
                title="Revenus par Champ (M FCFA)",
                xaxis=dict(gridcolor="#EEE"),
                yaxis=dict(gridcolor="#EEE"), **LAYOUT
            )
            st.plotly_chart(fig, use_container_width=True,
                            config=CFG_PLOTLY)

        with cd:
            fig2 = px.pie(rapport, values="Production_Totale",
                          names="champ",
                          title="Part Production par Champ",
                          color_discrete_sequence=COLORS["defaut"],
                          hole=0.4)
            fig2.update_layout(**LAYOUT)
            st.plotly_chart(fig2, use_container_width=True,
                            config=CFG_PLOTLY)

        # Graphique marge vs revenus
        fig3 = go.Figure()
        fig3.add_trace(go.Bar(
            x=rapport["champ"], y=rapport["Revenu_USD"]/1e6,
            name="Revenus", marker_color="#27AE60", opacity=0.8
        ))
        fig3.add_trace(go.Bar(
            x=rapport["champ"], y=rapport["Cout_USD"]/1e6,
            name="Couts", marker_color="#E74C3C", opacity=0.8
        ))
        fig3.add_trace(go.Bar(
            x=rapport["champ"], y=rapport["Marge_USD"]/1e6,
            name="Marge", marker_color="#E07B00", opacity=0.9
        ))
        fig3.update_layout(
            title=f"Revenus / Couts / Marge par Champ (M USD) — {periode_label}",
            barmode="group",
            xaxis=dict(gridcolor="#EEE"),
            yaxis=dict(gridcolor="#EEE", title="Millions USD"),
            legend=dict(bgcolor="white",
                        bordercolor="rgba(224,123,0,0.3)"),
            **LAYOUT
        )
        st.plotly_chart(fig3, use_container_width=True,
                        config=CFG_PLOTLY)

        # Tableau détaillé
        st.markdown("""
        <div style="color:#999;font-size:0.7rem;letter-spacing:1.5px;
                    text-transform:uppercase;margin:12px 0 8px 0;
                    font-weight:600;">Detail par Champ</div>
        """, unsafe_allow_html=True)
        aff = rapport.copy()
        aff["WaterCut_Moyen"]    = aff["WaterCut_Moyen"].map("{:.1%}".format)
        aff["Uptime_Moyen"]      = aff["Uptime_Moyen"].map("{:.1f}%".format)
        aff["Production_Totale"] = aff["Production_Totale"].map("{:,.0f} bbl".format)
        aff["Revenu_USD"]        = aff["Revenu_USD"].map("${:,.0f}".format)
        aff["Revenu_FCFA"]       = aff["Revenu_FCFA"].map("{:,.0f}".format)
        aff["Marge_USD"]         = aff["Marge_USD"].map("${:,.0f}".format)
        st.dataframe(aff, use_container_width=True, hide_index=True)
    else:
        st.info("Aucune donnee disponible.")

# ════════════════════════════════════════════
# PAGE 5 — SAISIE DES DONNÉES
# ════════════════════════════════════════════
elif page == "Saisie des Donnees":

    header("Saisie des Donnees",
           "3 modes d'entree des donnees de production")

    tab1, tab2, tab3 = st.tabs([
        "  Saisie Manuelle  ",
        "  Import Excel/CSV  ",
        "  URL / API  "
    ])

    with tab1:
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            date_s  = st.date_input("Date", value=date.today())
            puits_s = st.selectbox("Puits", list(PROFILS_PUITS.keys()))
            champ_a = PROFILS_PUITS[puits_s]["champ"]
            st.markdown(
                f'<div style="background:#FFF0DC;border-radius:6px;'
                f'padding:8px 12px;color:#E07B00;font-weight:600;'
                f'margin:4px 0 12px 0;">Champ : {champ_a}</div>',
                unsafe_allow_html=True
            )
            prod   = st.number_input("Production huile (bbl/j)",
                                      min_value=0.0, value=5000.0, step=50.0)
            wc_pct = st.slider("Water Cut (%)", 0.0, 100.0, 35.0, 0.1)
            wc     = wc_pct / 100

        with col2:
            gor   = st.number_input("GOR (scf/stb)", min_value=0.0,
                                     value=800.0, step=10.0)
            press = st.number_input("Pression tete (psi)",
                                     min_value=0.0, value=380.0, step=5.0)
            temp  = st.number_input("Temperature (deg F)",
                                     min_value=0.0, value=175.0, step=1.0)
            heur  = st.slider("Heures de production", 0, 24, 24)
            st.text_area("Commentaire", placeholder="Observations...")

        prod_eau = prod * wc / max(1-wc, 0.01)
        prod_gaz = prod * gor / 1000
        statut   = ("Critique" if wc > SEUILS["water_cut_critique"] else
                    "Alerte"   if wc > SEUILS["water_cut_alerte"]   else "Actif")

        st.divider()
        c1,c2,c3,c4 = st.columns(4)
        c_s = ("#E74C3C" if statut=="Critique" else
               "#F0A500" if statut=="Alerte"   else "#27AE60")
        with c1: kpi("Huile",  f"{prod:,.0f}",   "bbl/j",  "#E07B00","🛢️")
        with c2: kpi("Eau",    f"{prod_eau:,.0f}","bbl/j",  "#2E86C1","💧")
        with c3: kpi("Gaz",    f"{prod_gaz:.1f}", "MMscf/j","#27AE60","⛽")
        with c4: kpi("Statut", statut, "", c_s, "📊")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Enregistrer la mesure", type="primary",
                     use_container_width=True):
            ok = sauvegarder_production(
                date_s, puits_s, champ_a,
                prod, prod_gaz, prod_eau,
                wc, gor, press, temp, heur, statut,
                user.get("nom","Systeme")
            )
            if ok:
                st.success(f"Mesure enregistree — {puits_s} | "
                           f"{prod:,.0f} bbl/j | WC:{wc_pct:.1f}%")
                st.balloons()

    with tab2:
        st.markdown("<br>", unsafe_allow_html=True)
        modele = pd.DataFrame({
            "date":["2026-04-26","2026-04-26"],
            "puits":["Baleine-A","Sankofa-1"],
            "champ":["Baleine","Sankofa"],
            "production_huile_bbl":[6500,8500],
            "production_gaz_mmscf":[5.2,7.0],
            "production_eau_bbl":[1430,4590],
            "water_cut":[0.18,0.35],
            "gor":[800,850],
            "pression_tete_psi":[580,420],
            "temperature_f":[185,182],
            "heures_production":[24,24],
            "statut":["Actif","Actif"],
        })
        st.download_button(
            "Telecharger le modele CSV",
            data=modele.to_csv(index=False).encode("utf-8"),
            file_name="modele_petro_africa.csv",
            mime="text/csv"
        )
        st.divider()
        fichier = st.file_uploader("Uploader fichier (.xlsx ou .csv)",
                                    type=["xlsx","csv"])
        if fichier:
            try:
                df_imp = (pd.read_csv(fichier)
                          if fichier.name.endswith(".csv")
                          else pd.read_excel(fichier))
                st.success(f"{len(df_imp)} lignes detectees")
                st.dataframe(df_imp.head(6), use_container_width=True)
                cols_req = ["date","puits","champ",
                            "production_huile_bbl","water_cut"]
                manq = [c for c in cols_req if c not in df_imp.columns]
                if manq:
                    st.error(f"Colonnes manquantes : {manq}")
                elif st.button("Importer", type="primary",
                               use_container_width=True):
                    conn   = sqlite3.connect(DB_PATH,
                                             check_same_thread=False)
                    succes = 0
                    for _, row in df_imp.iterrows():
                        try:
                            conn.cursor().execute("""
                                INSERT OR REPLACE INTO production_journaliere
                                (date,puits,champ,
                                 production_huile_bbl,
                                 production_gaz_mmscf,
                                 production_eau_bbl,water_cut,gor,
                                 pression_tete_psi,temperature_f,
                                 heures_production,statut,saisie_par)
                                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
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
                                str(row.get("statut","Actif")),
                                user.get("nom","Import")
                            ))
                            succes += 1
                        except Exception:
                            pass
                    conn.commit(); conn.close()
                    st.success(f"{succes} lignes importees")
                    st.balloons()
            except Exception as e:
                st.error(f"Erreur : {e}")

    with tab3:
        st.markdown("<br>", unsafe_allow_html=True)
        url = st.text_input("URL fichier CSV",
                             placeholder="https://...")
        if url and st.button("Charger depuis URL", type="primary"):
            try:
                df_url = pd.read_csv(url)
                st.success(f"{len(df_url)} lignes chargees")
                st.dataframe(df_url.head())
            except Exception as e:
                st.error(f"Erreur : {e}")

        st.divider()
        donnees = st.text_area("Ou coller les donnees CSV",
                                height=150,
                                placeholder="date,puits,champ,production_huile_bbl,water_cut,statut\n...")
        if donnees and st.button("Importer les donnees collees",
                                  type="primary"):
            try:
                from io import StringIO
                df_c   = pd.read_csv(StringIO(donnees))
                conn   = sqlite3.connect(DB_PATH, check_same_thread=False)
                succes = 0
                for _, row in df_c.iterrows():
                    try:
                        conn.cursor().execute("""
                            INSERT OR REPLACE INTO production_journaliere
                            (date,puits,champ,production_huile_bbl,
                             water_cut,statut,saisie_par)
                            VALUES (?,?,?,?,?,?,?)
                        """, (str(row.get("date","")),
                              str(row.get("puits","")),
                              str(row.get("champ","")),
                              float(row.get("production_huile_bbl",0)),
                              float(row.get("water_cut",0)),
                              str(row.get("statut","Actif")),
                              user.get("nom","Coller")))
                        succes += 1
                    except Exception:
                        pass
                conn.commit(); conn.close()
                st.success(f"{succes} lignes importees")
                st.balloons()
            except Exception as e:
                st.error(f"Erreur : {e}")

# ════════════════════════════════════════════
# PAGE 6 — PRÉVISIONS ML
# ════════════════════════════════════════════
elif page == "Previsions ML":

    header("Previsions ML — Decline Curve Analysis",
           "Modeles Arps + Random Forest + EUR")

    puits_liste  = list(PROFILS_PUITS.keys())
    puits_choisi = st.selectbox("Choisir un puits", puits_liste)

    df_hist = lire_production(
        date_debut=str(date_debut),
        date_fin=str(date_fin),
        puits=puits_choisi
    )

    if df_hist.empty or len(df_hist) < 10:
        st.warning("Donnees insuffisantes. Selectionnez 90+ jours.")
    else:
        from ml_forecast import (fitter_declin_arps, prevoir_production,
                                  calculer_eur, forecast_random_forest)

        df_hist = df_hist.sort_values("date")

        # Fitter le modèle Arps
        with st.spinner("Calcul du modele de declin..."):
            modele = fitter_declin_arps(df_hist)

        if modele:
            c1,c2,c3,c4 = st.columns(4)
            with c1: kpi("Type Declin",
                          modele["type"].capitalize(), "",
                          "#E07B00", "📊")
            with c2: kpi("R² Ajustement",
                          f"{modele['r2']:.3f}", "",
                          "#27AE60" if modele["r2"]>0.9 else "#F0A500",
                          "✅" if modele["r2"]>0.9 else "⚠️")
            with c3: kpi("Production Initiale",
                          f"{modele['qi']:,.0f}",
                          "bbl/j", "#2E86C1", "🛢️")
            with c4: kpi("Taux Declin",
                          f"{modele['d']*365*100:.1f}%",
                          "par an", "#E74C3C", "📉")

            # Prévisions 12 mois
            nb_mois = st.slider("Horizon de prevision (mois)", 3, 24, 12)
            df_prev = prevoir_production(modele, nb_jours_futur=nb_mois*30)

            # Calculer EUR
            eur = calculer_eur(modele)

            if eur:
                st.markdown("<br>", unsafe_allow_html=True)
                c1,c2,c3,c4 = st.columns(4)
                with c1: kpi("EUR (Reserves)",
                              f"{eur['eur_mmbl']:.2f}",
                              "MMbbl", "#E07B00", "🛢️")
                with c2: kpi("Duree de vie",
                              f"{eur['duree_vie_ans']:.1f}",
                              "annees", "#2E86C1", "📅")
                with c3: kpi("Revenu futur",
                              f"${eur['revenu_total_musd']:.1f}M",
                              "USD", "#27AE60", "💵")
                with c4: kpi("Marge future",
                              f"${eur['marge_totale_musd']:.1f}M",
                              "USD", "#8E44AD", "💰")

            # Graphique principal
            fig = go.Figure()
            # Historique
            df_plot = df_hist[df_hist["production_huile_bbl"]>0]
            fig.add_trace(go.Scatter(
                x=df_plot["date"], y=df_plot["production_huile_bbl"],
                mode="markers", name="Production reelle",
                marker=dict(color="#2E86C1", size=4, opacity=0.7)
            ))
            # Courbe fittée
            from ml_forecast import (declin_exponentiel,
                                      declin_hyperbolique)
            t_base  = modele["t_base"]
            if modele["type"] == "exponentiel":
                q_fit = declin_exponentiel(t_base, *modele["params"])
            else:
                q_fit = declin_hyperbolique(t_base, *modele["params"])
            fig.add_trace(go.Scatter(
                x=df_plot["date"].values[:len(t_base)],
                y=q_fit,
                mode="lines", name=f"Modele {modele['type']}",
                line=dict(color="#E07B00", width=2.5)
            ))
            # Prévisions avec intervalles
            if not df_prev.empty:
                fig.add_trace(go.Scatter(
                    x=df_prev["date"], y=df_prev["q_prevue"],
                    mode="lines", name="Prevision",
                    line=dict(color="#27AE60", width=2, dash="dash")
                ))
                fig.add_trace(go.Scatter(
                    x=list(df_prev["date"]) + list(df_prev["date"][::-1]),
                    y=list(df_prev["q_high"]) + list(df_prev["q_low"][::-1]),
                    fill="toself",
                    fillcolor="rgba(39,174,96,0.1)",
                    line=dict(color="rgba(0,0,0,0)"),
                    name="Intervalle de confiance 90%"
                ))

            # Ligne seuil économique
            fig.add_hline(
                y=500, line_dash="dot",
                line_color="red", opacity=0.5,
                annotation_text="Seuil economique (500 bbl/j)"
            )

            fig.update_layout(
                title=f"Prevision de Production — {puits_choisi}",
                xaxis=dict(gridcolor="#EEE", color="#888"),
                yaxis=dict(gridcolor="#EEE", color="#888",
                           title="Production (bbl/jour)"),
                legend=dict(bgcolor="white",
                            bordercolor="rgba(224,123,0,0.3)"),
                hovermode="x unified", **LAYOUT
            )
            st.plotly_chart(fig, use_container_width=True,
                            config=CFG_PLOTLY)

            # Random Forest en complément
            with st.expander("Prevision Random Forest (ML avance)"):
                with st.spinner("Entrainement modele RF..."):
                    df_rf = forecast_random_forest(df_hist, nb_jours=90)
                if not df_rf.empty:
                    st.metric("R² Random Forest",
                              f"{df_rf['r2_rf'].iloc[0]:.3f}")
                    fig_rf = px.line(df_rf, x="date", y="q_rf",
                                     title="Prevision Random Forest (90 jours)",
                                     color_discrete_sequence=["#8E44AD"])
                    fig_rf.update_layout(**LAYOUT)
                    st.plotly_chart(fig_rf, use_container_width=True,
                                    config=CFG_PLOTLY)
                else:
                    st.info("Donnees insuffisantes pour RF.")
        else:
            st.warning("Impossible de fitter le modele. "
                       "Verifiez les donnees.")

# ════════════════════════════════════════════
# PAGE 7 — FORAGE DDR
# ════════════════════════════════════════════
elif page == "Forage DDR":

    header("Forage — Daily Drilling Report",
           "Suivi des operations de forage — Blocs CI")

    blocs_forage = list(BLOCS_EXPLORATION.keys())
    bloc_choisi  = st.selectbox("Bloc", blocs_forage)
    df_drill     = lire_drilling(bloc=bloc_choisi)

    if df_drill.empty:
        st.info("Aucune donnee de forage pour ce bloc.")
    else:
        df_drill = df_drill.sort_values("date")
        derniere = df_drill.iloc[-1]

        c1,c2,c3,c4 = st.columns(4)
        with c1: kpi("Profondeur Actuelle",
                      f"{derniere['profondeur_actuelle_m']:,.0f}",
                      "metres", "#E07B00", "⛏️")
        with c2: kpi("Profondeur Cible",
                      f"{derniere['profondeur_cible_m']:,.0f}",
                      "metres", "#2E86C1", "🎯")
        with c3:
            pct = (derniere["profondeur_actuelle_m"] /
                   derniere["profondeur_cible_m"] * 100)
            kpi("Avancement", f"{pct:.1f}%", "", "#27AE60", "📊")
        with c4: kpi("ROP Moyen",
                      f"{df_drill['rop_m_heure'].mean():.1f}",
                      "m/heure", "#8E44AD", "⚡")

        # Courbe de forage (depth vs time)
        fig = px.line(df_drill, x="date",
                       y="profondeur_actuelle_m",
                       title=f"Courbe de Forage — {bloc_choisi}",
                       color_discrete_sequence=["#E07B00"])
        fig.update_yaxes(autorange="reversed",
                          title="Profondeur (m)")
        fig.add_hline(y=derniere["profondeur_cible_m"],
                       line_dash="dash", line_color="red",
                       annotation_text="TD Cible")
        fig.update_layout(**LAYOUT)
        st.plotly_chart(fig, use_container_width=True, config=CFG_PLOTLY)

        # ROP dans le temps
        fig_rop = px.bar(df_drill, x="date", y="rop_m_heure",
                          title="Taux de Penetration (ROP) m/h",
                          color_discrete_sequence=["#2E86C1"])
        fig_rop.update_layout(**LAYOUT)
        st.plotly_chart(fig_rop, use_container_width=True,
                         config=CFG_PLOTLY)

        # Tableau DDR
        st.markdown("""
        <div style="color:#999;font-size:0.7rem;letter-spacing:1.5px;
                    text-transform:uppercase;margin:8px 0;
                    font-weight:600;">Journal de Forage</div>
        """, unsafe_allow_html=True)
        st.dataframe(
            df_drill[["date","profondeur_actuelle_m","rop_m_heure",
                       "phase","type_operation","boue_type",
                       "commentaire"]].tail(20),
            use_container_width=True, hide_index=True
        )

    # Formulaire saisie DDR
    with st.expander("Ajouter une entree DDR"):
        c1, c2 = st.columns(2)
        with c1:
            date_d  = st.date_input("Date forage", value=date.today())
            puits_d = st.text_input("Nom du puits",
                                     placeholder="CI-401-EXP-1")
            prof_d  = st.number_input("Profondeur actuelle (m)",
                                       min_value=0.0, value=1000.0)
            cible_d = st.number_input("Profondeur cible (m)",
                                       min_value=0.0, value=3800.0)
        with c2:
            rop_d   = st.number_input("ROP (m/h)",
                                       min_value=0.0, value=10.0)
            phase_d = st.selectbox("Phase", [
                "Phase surface","Phase intermediaire",
                "Phase production","Diagraphies","Cimentation"
            ])
            op_d    = st.selectbox("Operation", [
                "Forage rotary","Carottage","Diagraphies",
                "Cimentation","BHA change","Test de pression"
            ])
            boue_d  = st.selectbox("Boue", [
                "Eau douce","Boue synthetique OBM","KCl/Polymere"
            ])
        comm_d = st.text_area("Commentaire DDR", height=80)

        if st.button("Enregistrer DDR", type="primary"):
            try:
                conn = sqlite3.connect(DB_PATH, check_same_thread=False)
                conn.cursor().execute("""
                    INSERT INTO drilling_log
                    (date,puits,bloc,profondeur_actuelle_m,
                     profondeur_cible_m,rop_m_heure,
                     type_operation,phase,boue_type,
                     commentaire,operateur)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """, (str(date_d), puits_d, bloc_choisi,
                      prof_d, cible_d, rop_d,
                      op_d, phase_d, boue_d,
                      comm_d, user.get("compagnie","")))
                conn.commit(); conn.close()
                st.success("Entree DDR enregistree")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur : {e}")

# ════════════════════════════════════════════
# PAGE 8 — BENCHMARKS
# ════════════════════════════════════════════
elif page == "Benchmarks":

    header("Benchmarks Industrie O&G",
           "Comparaison vs standards industrie — Cote d'Ivoire")

    df_prod = lire_production(
        date_debut=str(date_debut), date_fin=str(date_fin)
    )

    if df_prod.empty:
        st.info("Aucune donnee disponible.")
    else:
        bench = analyse_benchmark(df_prod)

        # Water Cut vs Benchmark
        wc_m     = bench.get("wc_moyen", 0)
        wc_bench = BENCHMARKS["water_cut_moyen_ci"]
        c_wc     = "#27AE60" if wc_m < wc_bench else "#E74C3C"

        c1,c2,c3,c4 = st.columns(4)
        with c1: kpi("Water Cut Actuel",
                      f"{wc_m:.1%}", "champs CI",
                      c_wc, "💧")
        with c2: kpi("Benchmark CI",
                      f"{wc_bench:.1%}", "moyenne industrie",
                      "#888", "📊")
        with c3: kpi("Uptime Moyen",
                      f"{bench.get('uptime_moyen',0):.1f}%",
                      f"cible : {BENCHMARKS['uptime_cible']*100:.0f}%",
                      "#27AE60" if bench.get("uptime_moyen",0) > 93
                      else "#E74C3C", "⏱️")
        with c4: kpi("Puits Rentables",
                      str(bench.get("nb_puits_rentables",0)),
                      f"sur {len(PROFILS_PUITS)} total",
                      "#2E86C1", "✅")

        st.markdown("<br>", unsafe_allow_html=True)

        # Graphique comparaison Water Cut par puits
        wc_par_puits = (df_prod.groupby("puits")["water_cut"]
                        .mean().reset_index()
                        .sort_values("water_cut", ascending=True))

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=wc_par_puits["puits"],
            y=wc_par_puits["water_cut"] * 100,
            name="Water Cut actuel (%)",
            marker=dict(
                color=[("#27AE60" if v < wc_bench
                        else "#F0A500" if v < BENCHMARKS["water_cut_alerte"]
                        else "#E74C3C")
                       for v in wc_par_puits["water_cut"]]
            )
        ))
        fig.add_hline(y=wc_bench*100, line_dash="dash",
                       line_color="#2E86C1",
                       annotation_text=f"Benchmark CI ({wc_bench:.0%})")
        fig.add_hline(y=BENCHMARKS["water_cut_alerte"]*100,
                       line_dash="dot", line_color="#F0A500",
                       annotation_text="Seuil alerte")
        fig.add_hline(y=BENCHMARKS["water_cut_critique"]*100,
                       line_dash="dot", line_color="#E74C3C",
                       annotation_text="Seuil critique")
        fig.update_layout(
            title="Water Cut par Puits vs Benchmarks Industrie CI",
            xaxis=dict(gridcolor="#EEE", tickangle=-45),
            yaxis=dict(gridcolor="#EEE", title="Water Cut (%)"),
            **LAYOUT
        )
        st.plotly_chart(fig, use_container_width=True, config=CFG_PLOTLY)

        # Tableau benchmarks référence
        st.markdown("""
        <div style="color:#999;font-size:0.7rem;letter-spacing:1.5px;
                    text-transform:uppercase;margin:12px 0 8px 0;
                    font-weight:600;">Reference Benchmarks Industrie</div>
        """, unsafe_allow_html=True)

        data_bench = [
            ["Water Cut moyen CI",
             f"{BENCHMARKS['water_cut_moyen_ci']:.0%}", "Industrie CI"],
            ["Seuil alerte water cut",
             f"{BENCHMARKS['water_cut_alerte']:.0%}", "PETRO AFRICA"],
            ["Seuil critique water cut",
             f"{BENCHMARKS['water_cut_critique']:.0%}", "PETRO AFRICA"],
            ["Declin annuel normal offshore",
             f"{BENCHMARKS['declin_annuel_normal']:.0%}", "SPE"],
            ["Declin annuel rapide",
             f"{BENCHMARKS['declin_annuel_rapide']:.0%}", "SPE"],
            ["Uptime cible",
             f"{BENCHMARKS['uptime_cible']:.0%}", "Industrie"],
            ["GOR normal min",
             f"{BENCHMARKS['gor_normal_min']} scf/stb", "Industrie CI"],
            ["GOR normal max",
             f"{BENCHMARKS['gor_normal_max']} scf/stb", "Industrie CI"],
            ["Production min economique",
             f"{BENCHMARKS['production_min_viable']:,} bbl/j", "PETRO AFRICA"],
            ["Cout production offshore CI",
             f"${BENCHMARKS['cout_prod_offshore_ci']}/bbl", "IHS Markit"],
        ]
        df_bench = pd.DataFrame(
            data_bench,
            columns=["Indicateur","Valeur","Source"]
        )
        st.dataframe(df_bench, use_container_width=True, hide_index=True)

# ════════════════════════════════════════════
# PAGE 9 — ALERTES
# ════════════════════════════════════════════
elif page == "Alertes":

    header("Systeme d'Alertes",
           "Surveillance temps reel — Notification automatique")

    col_btn1, col_btn2, col_btn3 = st.columns(3)
    with col_btn1:
        if st.button("Verifier les alertes",
                     use_container_width=True, type="primary"):
            alertes = verifier_alertes()
            nb = len(alertes)
            if nb > 0:
                ok, msg = envoyer_email_alerte(alertes)
                st.success(f"{nb} alertes — Email : {msg}")
            else:
                st.success("Aucune nouvelle alerte detectee")

    with col_btn2:
        kpis = kpis_journaliers()
        if st.button("Envoyer rapport email",
                     use_container_width=True):
            rapport = production_par_champ(7)
            ok, msg = envoyer_rapport_quotidien(kpis, rapport)
            (st.success(f"Rapport envoye : {msg}")
             if ok else st.warning(f"Email non configure : {msg}"))

    with col_btn3:
        if st.button("Marquer tout comme resolu",
                     use_container_width=True):
            try:
                conn = sqlite3.connect(DB_PATH,
                                        check_same_thread=False)
                conn.cursor().execute(
                    "UPDATE alertes SET resolue=1 WHERE resolue=0"
                )
                conn.commit(); conn.close()
                st.success("Toutes les alertes marquees resolues")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur : {e}")

    st.divider()
    df_al = lire_alertes(resolues=False)

    if not df_al.empty:
        c1,c2,c3 = st.columns(3)
        with c1: kpi("Total Alertes", str(len(df_al)),
                      "actives", "#F0A500", "⚠️")
        with c2: kpi("Critiques",
                      str(int((df_al["niveau"]=="CRITIQUE").sum())),
                      "intervention requise", "#E74C3C", "🔴")
        with c3: kpi("Alertes",
                      str(int((df_al["niveau"]=="ALERTE").sum())),
                      "surveillance", "#F0A500", "⚠️")

        st.markdown("<br>", unsafe_allow_html=True)

        for _, a in df_al[df_al["niveau"]=="CRITIQUE"].iterrows():
            st.markdown(f"""
            <div style="background:#FFF0F0;border-left:5px solid #CC0000;
                        border-radius:0 8px 8px 0;padding:12px 16px;
                        margin:6px 0;">
                <b style="color:#CC0000;">CRITIQUE</b>
                &nbsp;|&nbsp; <b>{a['puits']}</b> ({a['champ']})
                &nbsp;|&nbsp; {a.get('type_alerte','')}
                <br><span style="color:#666;font-size:0.85rem;">
                {a.get('message','')}</span>
                <br><span style="color:#AAA;font-size:0.75rem;">
                {a.get('date_alerte','')}</span>
            </div>""", unsafe_allow_html=True)

        for _, a in df_al[df_al["niveau"]=="ALERTE"].iterrows():
            st.markdown(f"""
            <div style="background:#FFFBF0;border-left:5px solid #CC7700;
                        border-radius:0 8px 8px 0;padding:12px 16px;
                        margin:6px 0;">
                <b style="color:#CC7700;">ALERTE</b>
                &nbsp;|&nbsp; <b>{a['puits']}</b> ({a['champ']})
                &nbsp;|&nbsp; {a.get('type_alerte','')}
                <br><span style="color:#666;font-size:0.85rem;">
                {a.get('message','')}</span>
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background:#E8F8F0;border-radius:10px;
                    padding:24px;text-align:center;
                    color:#1A7A4A;font-size:1rem;font-weight:600;">
            Aucune alerte active — Tous les puits sont nominaux
        </div>""", unsafe_allow_html=True)

    # Config email
    with st.expander("Configuration Email"):
        st.markdown("""
        Pour activer les alertes par email, ajoutez dans
        **Streamlit Cloud > Settings > Secrets** :

        ```toml
        [email]
        gmail_user = "votre@gmail.com"
        gmail_pass = "mot_de_passe_app_gmail"
        destinataires = "ing1@petroci.ci, ing2@petroci.ci"
        ```

        Utilisez un **mot de passe d'application Gmail**
        (pas votre mot de passe principal).
        Activez la verification en 2 etapes sur votre compte Gmail,
        puis allez dans Securite > Mots de passe d'application.
        """)

# ════════════════════════════════════════════
# PAGE 10 — RAPPORTS
# ════════════════════════════════════════════
elif page == "Rapports":

    header("Rapports", "Generation automatique — Export CSV et PDF")

    type_r = st.selectbox("Type de rapport", [
        "Rapport Production par Champ",
        "Rapport Performance Operateurs",
        "Rapport Alertes Actives",
        "Rapport Financier",
    ])

    if st.button("Generer le Rapport", type="primary",
                 use_container_width=True):
        with st.spinner("Generation..."):
            rapport = production_par_champ(nb_jours)
            kpis    = kpis_journaliers()

            st.markdown(f"""
            <div style="background:white;border-left:5px solid #E07B00;
                        border-radius:0 10px 10px 0;padding:14px 18px;
                        margin:16px 0;">
                <div style="color:#E07B00;font-weight:700;">{type_r}</div>
                <div style="color:#888;font-size:0.8rem;">
                    Periode : {date_debut} au {date_fin} &nbsp;|&nbsp;
                    Genere le : {date.today().strftime('%d/%m/%Y')} &nbsp;|&nbsp;
                    Par : {user.get('nom','')}
                </div>
            </div>""", unsafe_allow_html=True)

            if not rapport.empty:
                c1,c2,c3,c4 = st.columns(4)
                with c1: kpi("Production",
                              f"{rapport['Production_Totale'].sum():,.0f}",
                              "bbl", "#E07B00","🛢️")
                with c2: kpi("Revenus USD",
                              f"${rapport['Revenu_USD'].sum():,.0f}",
                              "", "#27AE60","💵")
                with c3: kpi("Revenus FCFA",
                              f"{rapport['Revenu_FCFA'].sum()/1e9:.2f} Mds",
                              "", "#2E86C1","💶")
                with c4: kpi("Marge",
                              f"${rapport['Marge_USD'].sum():,.0f}",
                              "", "#8E44AD","📈")

                st.markdown("<br>", unsafe_allow_html=True)

                if type_r == "Rapport Performance Operateurs":
                    from config import CHAMPS
                    df_op = lire_production(date_debut=str(date_debut),
                                             date_fin=str(date_fin))
                    if not df_op.empty:
                        df_op["operateur"] = df_op["champ"].map(
                            {k:v["operateur"] for k,v in CHAMPS.items()}
                        )
                        grp = df_op.groupby("operateur").agg(
                            Production=("production_huile_bbl","sum"),
                            WC_Moyen  =("water_cut","mean"),
                            Uptime    =("heures_production","mean"),
                            Nb_Puits  =("puits","nunique")
                        ).reset_index()
                        grp["Revenu_USD"] = grp["Production"] * PRIX_BARIL
                        st.dataframe(grp, use_container_width=True,
                                     hide_index=True)

                elif type_r == "Rapport Alertes Actives":
                    df_al = lire_alertes(resolues=False)
                    if not df_al.empty:
                        st.dataframe(df_al, use_container_width=True, hide_index=True)
                    else:
                        st.success("Aucune alerte active.")

                elif type_r == "Rapport Financier":
                    aff = rapport[["champ","Production_Totale",
                                   "Revenu_USD","Cout_USD",
                                   "Marge_USD","WaterCut_Moyen"]].copy()
                    aff["Production_Totale"] = aff["Production_Totale"].map("{:,.0f}".format)
                    aff["Revenu_USD"]  = aff["Revenu_USD"].map("${:,.0f}".format)
                    aff["Cout_USD"]    = aff["Cout_USD"].map("${:,.0f}".format)
                    aff["Marge_USD"]   = aff["Marge_USD"].map("${:,.0f}".format)
                    aff["WaterCut_Moyen"] = aff["WaterCut_Moyen"].map("{:.1%}".format)
                    st.dataframe(aff, use_container_width=True,
                                 hide_index=True)
                else:
                    aff = rapport.copy()
                    aff["WaterCut_Moyen"]    = aff["WaterCut_Moyen"].map("{:.1%}".format)
                    aff["Uptime_Moyen"]      = aff["Uptime_Moyen"].map("{:.1f}%".format)
                    aff["Production_Totale"] = aff["Production_Totale"].map("{:,.0f}".format)
                    aff["Revenu_USD"]        = aff["Revenu_USD"].map("${:,.0f}".format)
                    st.dataframe(aff, use_container_width=True,
                                 hide_index=True)

                fig = go.Figure(go.Bar(
                    x=rapport["champ"],
                    y=rapport["Production_Totale"],
                    text=[f"{v:,.0f}" for v in rapport["Production_Totale"]],
                    textposition="outside",
                    marker=dict(color=COLORS["defaut"])
                ))
                fig.update_layout(
                    title="Production par Champ (bbl)",
                    xaxis=dict(gridcolor="#EEE"),
                    yaxis=dict(gridcolor="#EEE"), **LAYOUT
                )
                st.plotly_chart(fig, use_container_width=True,
                                config=CFG_PLOTLY)

                st.divider()
                col_csv, col_pdf = st.columns(2)

                with col_csv:
                    st.download_button(
                        "Telecharger CSV",
                        data=rapport.to_csv(index=False).encode("utf-8"),
                        file_name=f"rapport_{date.today()}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

                with col_pdf:
                    from reports import generer_rapport_pdf
                    pdf = generer_rapport_pdf(
                        rapport, type_r,
                        date_debut, date_fin, nb_jours, kpis
                    )
                    if pdf:
                        st.download_button(
                            "Telecharger PDF",
                            data=pdf,
                            file_name=f"rapport_{date.today()}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    else:
                        st.info("PDF : verifiez que reportlab est installe")

                st.success(f"Rapport genere par {user.get('nom','')}")
            else:
                st.warning("Aucune donnee disponible.")

    # Mode impression
    st.divider()
    if st.button("Mode Impression (Ctrl+P)", use_container_width=True):
        st.markdown("""
        <script>window.print();</script>
        """, unsafe_allow_html=True)
        st.info("Utilisez Ctrl+P ou la fonction impression de votre navigateur.")
