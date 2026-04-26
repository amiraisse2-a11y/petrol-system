# dashboard.py
# PETROCI — Design Blanc/Orange — Version Finale

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta
import sqlite3
import io

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
# CSS — THEME BLANC / ORANGE
# ════════════════════════════════════════════
st.markdown("""
<style>
/* Fond global blanc cassé */
.stApp {
    background-color: #F4F6F9;
}

/* Sidebar blanc */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #FFFFFF 0%, #FFF8F0 100%);
    border-right: 2px solid #E07B0020;
    box-shadow: 2px 0 10px rgba(0,0,0,0.05);
}

/* Boutons orange */
.stButton > button {
    background: linear-gradient(135deg, #E07B00, #F0A500) !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    letter-spacing: 0.3px;
    box-shadow: 0 3px 10px rgba(224,123,0,0.3) !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 5px 15px rgba(224,123,0,0.4) !important;
}

/* Tabs */
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #E07B00 !important;
    border-bottom: 3px solid #E07B00 !important;
    font-weight: 700 !important;
}
[data-testid="stTabs"] button {
    color: #666 !important;
    font-weight: 500;
}

/* Radio */
[data-testid="stRadio"] label {
    color: #444 !important;
    font-size: 0.9rem;
    padding: 4px 0;
}

/* Selectbox */
[data-testid="stSelectbox"] > div > div {
    border: 1px solid #E07B0040 !important;
    border-radius: 8px !important;
}

/* Inputs */
[data-testid="stNumberInput"] input,
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    border: 1px solid #E07B0030 !important;
    border-radius: 8px !important;
}

/* Divider */
hr { border-color: #E07B0020 !important; }

/* Upload zone */
[data-testid="stFileUploader"] {
    border: 2px dashed #E07B0050 !important;
    border-radius: 12px !important;
    background: #FFF8F0 !important;
}

/* Download button */
[data-testid="stDownloadButton"] button {
    background: linear-gradient(135deg, #1A5276, #2E86C1) !important;
    color: white !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════
# COMPOSANTS UI
# ════════════════════════════════════════════
def afficher_header(titre, sous_titre=""):
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #E07B00, #F0A500);
        border-radius: 12px;
        padding: 20px 28px;
        margin-bottom: 24px;
        box-shadow: 0 4px 15px rgba(224,123,0,0.25);
    ">
        <h2 style="color:white;margin:0;font-size:1.6rem;
                   font-weight:800;letter-spacing:0.5px;">
            {titre}
        </h2>
        <p style="color:rgba(255,255,255,0.85);margin:4px 0 0 0;
                  font-size:0.82rem;">
            {sous_titre}
        </p>
    </div>
    """, unsafe_allow_html=True)


def kpi_card(label, valeur, sous_valeur="", couleur="#E07B00", icone=""):
    st.markdown(f"""
    <div style="
        background: white;
        border: 1px solid #F0F0F0;
        border-top: 4px solid {couleur};
        border-radius: 12px;
        padding: 18px 16px;
        text-align: center;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        margin-bottom: 8px;
        transition: all 0.2s ease;
    ">
        <div style="font-size:1.6rem;margin-bottom:6px;">{icone}</div>
        <div style="color:#888;font-size:0.68rem;letter-spacing:1.5px;
                    text-transform:uppercase;margin-bottom:6px;
                    font-weight:600;">{label}</div>
        <div style="color:{couleur};font-size:1.5rem;font-weight:800;
                    line-height:1.1;">{valeur}</div>
        <div style="color:#AAA;font-size:0.72rem;margin-top:4px;">
            {sous_valeur}
        </div>
    </div>
    """, unsafe_allow_html=True)


def alerte_box(niveau, puits, champ, type_alerte, message):
    if niveau == "CRITIQUE":
        bg, border, couleur = "#FFF0F0", "#FF4B4B", "#CC0000"
        icone = "🔴"
    else:
        bg, border, couleur = "#FFFBF0", "#F0A500", "#CC7700"
        icone = "⚠️"
    st.markdown(f"""
    <div style="background:{bg};border:1px solid {border}40;
                border-left:5px solid {border};border-radius:8px;
                padding:12px 16px;margin:6px 0;">
        <span style="color:{couleur};font-weight:700;">
            {icone} {niveau}
        </span>
        &nbsp;|&nbsp;
        <strong>{puits}</strong> ({champ})
        &nbsp;|&nbsp; {type_alerte}
        <br>
        <span style="color:#666;font-size:0.85rem;">{message}</span>
    </div>
    """, unsafe_allow_html=True)


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


def generer_pdf_rapport(rapport, titre, date_debut, date_fin, nb_jours):
    """Génère un rapport PDF en mémoire"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import (SimpleDocTemplate, Table,
                                         TableStyle, Paragraph,
                                         Spacer, HRFlowable)
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm

        buffer = io.BytesIO()
        doc    = SimpleDocTemplate(buffer, pagesize=A4,
                                    rightMargin=2*cm, leftMargin=2*cm,
                                    topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        elems  = []

        # Style titre
        style_titre = ParagraphStyle(
            "titre", parent=styles["Title"],
            textColor=colors.HexColor("#E07B00"),
            fontSize=20, spaceAfter=6
        )
        style_sous  = ParagraphStyle(
            "sous", parent=styles["Normal"],
            textColor=colors.HexColor("#666666"),
            fontSize=10, spaceAfter=20
        )
        style_section = ParagraphStyle(
            "section", parent=styles["Heading2"],
            textColor=colors.HexColor("#1A1A2E"),
            fontSize=12, spaceBefore=14, spaceAfter=8
        )

        # En-tête
        elems.append(Paragraph("PETROCI — Rapport de Production", style_titre))
        elems.append(Paragraph(
            f"{titre} &nbsp;|&nbsp; Periode : {date_debut} au {date_fin} "
            f"&nbsp;|&nbsp; Genere le : {date.today().strftime('%d/%m/%Y')}",
            style_sous
        ))
        elems.append(HRFlowable(width="100%", thickness=2,
                                 color=colors.HexColor("#E07B00")))
        elems.append(Spacer(1, 0.4*cm))

        # Résumé
        if not rapport.empty:
            prod_tot = rapport["Production_Totale"].sum()
            rev_usd  = rapport["Revenu_USD"].sum()
            rev_xof  = rapport["Revenu_FCFA"].sum()

            elems.append(Paragraph("Résumé Exécutif", style_section))
            resume_data = [
                ["Indicateur", "Valeur"],
                ["Production totale", f"{prod_tot:,.0f} bbl"],
                ["Revenus USD", f"${rev_usd:,.0f}"],
                ["Revenus FCFA", f"{rev_xof/1e6:,.1f} Millions FCFA"],
                ["Nombre de champs", str(len(rapport))],
                ["Periode analyse", f"{nb_jours} jours"],
            ]
            tbl = Table(resume_data, colWidths=[8*cm, 8*cm])
            tbl.setStyle(TableStyle([
                ("BACKGROUND",   (0,0), (-1,0),
                 colors.HexColor("#E07B00")),
                ("TEXTCOLOR",    (0,0), (-1,0), colors.white),
                ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
                ("FONTSIZE",     (0,0), (-1,0), 10),
                ("ALIGN",        (0,0), (-1,-1), "CENTER"),
                ("ROWBACKGROUNDS",(0,1),(-1,-1),
                 [colors.white, colors.HexColor("#FFF8F0")]),
                ("GRID",         (0,0), (-1,-1), 0.5,
                 colors.HexColor("#DDDDDD")),
                ("TOPPADDING",   (0,0), (-1,-1), 7),
                ("BOTTOMPADDING",(0,0), (-1,-1), 7),
                ("FONTNAME",     (0,1), (0,-1), "Helvetica-Bold"),
            ]))
            elems.append(tbl)
            elems.append(Spacer(1, 0.5*cm))

            # Tableau détail par champ
            elems.append(Paragraph("Detail par Champ", style_section))
            headers = ["Champ","Production (bbl)",
                       "Water Cut","Revenus USD","Revenus FCFA"]
            data    = [headers]
            for _, row in rapport.iterrows():
                data.append([
                    row["champ"],
                    f"{row['Production_Totale']:,.0f}",
                    f"{row['WaterCut_Moyen']:.1%}",
                    f"${row['Revenu_USD']:,.0f}",
                    f"{row['Revenu_FCFA']/1e6:.1f}M",
                ])
            # Ligne total
            data.append([
                "TOTAL",
                f"{prod_tot:,.0f}",
                f"{rapport['WaterCut_Moyen'].mean():.1%}",
                f"${rev_usd:,.0f}",
                f"{rev_xof/1e6:.1f}M",
            ])

            tbl2 = Table(data, colWidths=[3.5*cm,3.5*cm,2.5*cm,3*cm,3.5*cm])
            tbl2.setStyle(TableStyle([
                ("BACKGROUND",   (0,0), (-1,0),
                 colors.HexColor("#1A1A2E")),
                ("TEXTCOLOR",    (0,0), (-1,0), colors.white),
                ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
                ("FONTSIZE",     (0,0), (-1,-1), 9),
                ("ALIGN",        (0,0), (-1,-1), "CENTER"),
                ("ROWBACKGROUNDS",(0,1),(-1,-2),
                 [colors.white, colors.HexColor("#F9F9F9")]),
                ("BACKGROUND",   (0,-1),(-1,-1),
                 colors.HexColor("#FFF0DC")),
                ("FONTNAME",     (0,-1),(-1,-1), "Helvetica-Bold"),
                ("GRID",         (0,0), (-1,-1), 0.4,
                 colors.HexColor("#DDDDDD")),
                ("TOPPADDING",   (0,0), (-1,-1), 6),
                ("BOTTOMPADDING",(0,0), (-1,-1), 6),
            ]))
            elems.append(tbl2)

        # Pied de page
        elems.append(Spacer(1, 1*cm))
        elems.append(HRFlowable(width="100%", thickness=1,
                                 color=colors.HexColor("#DDDDDD")))
        elems.append(Paragraph(
            "Document confidentiel — PETROCI — Systeme de Gestion de Production",
            ParagraphStyle("footer", parent=styles["Normal"],
                           textColor=colors.HexColor("#999999"),
                           fontSize=8, alignment=1)
        ))

        doc.build(elems)
        buffer.seek(0)
        return buffer.read()

    except ImportError:
        return None


# ════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════
st.sidebar.markdown("""
<div style="text-align:center;padding:20px 0 12px 0;">
    <div style="font-size:2.8rem;margin-bottom:6px;">🛢️</div>
    <div style="color:#E07B00;font-size:1.3rem;font-weight:800;
                letter-spacing:3px;">PETROCI</div>
    <div style="color:#AAA;font-size:0.68rem;letter-spacing:2px;
                margin-top:2px;">PRODUCTION DASHBOARD</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown(
    '<hr style="border-color:#E07B0030;margin:4px 0 12px 0;">',
    unsafe_allow_html=True
)

page = st.sidebar.radio("Navigation", [
    "Tableau de Bord",
    "Puits et Champs",
    "Analyse Production",
    "Saisie des Donnees",
    "Alertes",
    "Declin et Previsions",
    "Rapports",
])

st.sidebar.markdown(
    '<hr style="border-color:#E07B0030;margin:12px 0 8px 0;">',
    unsafe_allow_html=True
)
st.sidebar.markdown(
    '<div style="color:#AAA;font-size:0.68rem;letter-spacing:1.5px;'
    'text-transform:uppercase;margin-bottom:8px;">Filtres</div>',
    unsafe_allow_html=True
)

champ_filtre  = st.sidebar.selectbox(
    "Champ", ["Tous","Baleine","Sankofa","Foxtrot","Baobab"],
    label_visibility="collapsed"
)
periode_label = st.sidebar.selectbox(
    "Periode", ["7 jours","30 jours","90 jours","365 jours"],
    label_visibility="collapsed"
)
nb_jours   = int(periode_label.split()[0])
date_fin   = date.today()
date_debut = date_fin - timedelta(days=nb_jours)

if st.sidebar.button("Actualiser", use_container_width=True):
    verifier_alertes()
    st.rerun()

resume = resume_alertes()
if resume["critiques"] > 0:
    st.sidebar.markdown(
        f'<div style="background:#FFF0F0;border:1px solid #FF4B4B60;'
        f'border-radius:8px;padding:8px 12px;margin:6px 0;'
        f'color:#CC0000;font-size:0.82rem;font-weight:600;">'
        f'🔴 {resume["critiques"]} critique(s) active(s)</div>',
        unsafe_allow_html=True
    )
if resume["alertes"] > 0:
    st.sidebar.markdown(
        f'<div style="background:#FFFBF0;border:1px solid #F0A50060;'
        f'border-radius:8px;padding:8px 12px;margin:6px 0;'
        f'color:#CC7700;font-size:0.82rem;font-weight:600;">'
        f'⚠️ {resume["alertes"]} alerte(s) active(s)</div>',
        unsafe_allow_html=True
    )

st.sidebar.markdown("""
<div style="text-align:center;color:#CCC;font-size:0.65rem;
            letter-spacing:1px;margin-top:40px;">
    PETROCI © 2026 — Cote d'Ivoire
</div>
""", unsafe_allow_html=True)

# Couleurs des graphiques (cohérentes)
COLORS = {
    "Baleine": "#E07B00",
    "Sankofa": "#27AE60",
    "Foxtrot": "#E74C3C",
    "Baobab":  "#2E86C1",
    "defaut":  ["#E07B00","#27AE60","#E74C3C","#2E86C1"]
}
LAYOUT = dict(
    paper_bgcolor="white",
    plot_bgcolor="#FAFAFA",
    font=dict(color="#333"),
    margin=dict(l=10, r=10, t=60, b=10)
)

# Config modebar (barre icônes Plotly) — masquer les icônes inutiles
MODEBAR = dict(
    remove=["zoom","pan","select","lasso2d",
            "zoomIn2d","zoomOut2d","autoScale2d",
            "toImage","resetScale2d"],
    orientation="v"
)

# ════════════════════════════════════════════
# PAGE 1 — TABLEAU DE BORD
# ════════════════════════════════════════════
if page == "Tableau de Bord":

    afficher_header(
        "🛢️ Tableau de Bord Production",
        f"Donnees au {date.today().strftime('%d/%m/%Y')} — Champs offshore Cote d'Ivoire"
    )

    kpis = kpis_journaliers()
    if kpis:
        c1,c2,c3,c4,c5 = st.columns(5)
        with c1:
            kpi_card("Production Totale",
                     f"{kpis['production_totale_bbl']:,.0f}",
                     "bbl/jour", "#E07B00", "🛢️")
        with c2:
            kpi_card("Revenu Journalier",
                     f"${kpis['revenu_journalier_usd']:,.0f}",
                     f"{kpis['revenu_journalier_xof']/1e6:.0f}M FCFA",
                     "#27AE60", "💰")
        with c3:
            kpi_card("Puits Actifs",
                     str(kpis["nb_puits_actifs"]),
                     "en production", "#27AE60", "✅")
        with c4:
            kpi_card("Alertes",
                     str(kpis["nb_puits_alerte"]),
                     "surveillance", "#F0A500", "⚠️")
        with c5:
            kpi_card("Critiques",
                     str(kpis["nb_puits_critiques"]),
                     "intervention", "#E74C3C", "🔴")

    st.markdown("<br>", unsafe_allow_html=True)

    df_hist = historique_champs(nb_jours)
    if not df_hist.empty:
        cg, cd = st.columns(2)
        with cg:
            df_total = (df_hist.groupby("date")["production_huile_bbl"]
                        .sum().reset_index())
            fig = go.Figure(go.Scatter(
                x=df_total["date"], y=df_total["production_huile_bbl"],
                fill="tozeroy", fillcolor="rgba(224,123,0,0.1)",
                line=dict(color="#E07B00", width=2.5), name="Production"
            ))
            fig.update_layout(
                title=f"Production Totale CI — {periode_label}",
                xaxis=dict(gridcolor="#EEE", color="#666"),
                yaxis=dict(gridcolor="#EEE", color="#666",
                           title="bbl/jour"),
                hovermode="x unified", **LAYOUT
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        with cd:
            fig2 = go.Figure()
            for champ in df_hist["champ"].unique():
                df_c = df_hist[df_hist["champ"]==champ]
                fig2.add_trace(go.Scatter(
                    x=df_c["date"], y=df_c["production_huile_bbl"],
                    name=champ, mode="lines",
                    line=dict(color=COLORS.get(champ,"#666"), width=2)
                ))
            fig2.update_layout(
                title=f"Production par Champ — {periode_label}",
                xaxis=dict(gridcolor="#EEE", color="#666"),
                yaxis=dict(gridcolor="#EEE", color="#666"),
                legend=dict(bgcolor="white",
                            bordercolor="rgba(224,123,0,0.2)"),
                hovermode="x unified", **LAYOUT
            )
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    # Carte — style clair OpenStreetMap
    st.markdown("""
    <div style="color:#888;font-size:0.72rem;letter-spacing:1.5px;
                text-transform:uppercase;margin:8px 0 10px 0;
                font-weight:600;">
        Localisation des Puits Offshore CI
    </div>
    """, unsafe_allow_html=True)

    df_puits = lire_puits()
    if not df_puits.empty and "latitude" in df_puits.columns:
        couleurs = {"Actif":"#27AE60","Alerte":"#F0A500","Critique":"#E74C3C"}
        fig_map  = px.scatter_map(
            df_puits, lat="latitude", lon="longitude",
            color="statut", hover_name="nom_puits",
            hover_data=["champ","operateur","statut"],
            color_discrete_map=couleurs,
            zoom=7, center={"lat":4.3,"lon":-3.7}
        )
        fig_map.update_layout(
            map_style="open-street-map",
            height=420,
            paper_bgcolor="white",
            margin=dict(l=0,r=0,t=0,b=0),
            legend=dict(bgcolor="white",
                        bordercolor="rgba(224,123,0,0.3)",
                        font=dict(color="#333"))
        )
        st.plotly_chart(fig_map, use_container_width=True, config={"displayModeBar": False})

# ════════════════════════════════════════════
# PAGE 2 — PUITS & CHAMPS
# ════════════════════════════════════════════
elif page == "Puits et Champs":

    afficher_header("🛢️ Puits et Champs Petroliers",
                    "Vue d'ensemble des actifs offshore Cote d'Ivoire")

    champ_q = None if champ_filtre=="Tous" else champ_filtre
    df      = lire_puits(champ=champ_q)

    c1,c2,c3,c4 = st.columns(4)
    with c1: kpi_card("Total Puits", str(len(df)), "", "#2E86C1", "🛢️")
    with c2: kpi_card("Actifs",
                       str(int((df["statut"]=="Actif").sum()) if not df.empty else 0),
                       "", "#27AE60", "✅")
    with c3: kpi_card("Alertes",
                       str(int((df["statut"]=="Alerte").sum()) if not df.empty else 0),
                       "", "#F0A500", "⚠️")
    with c4: kpi_card("Critiques",
                       str(int((df["statut"]=="Critique").sum()) if not df.empty else 0),
                       "", "#E74C3C", "🔴")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="color:#888;font-size:0.72rem;letter-spacing:1.5px;
                text-transform:uppercase;margin-bottom:10px;font-weight:600;">
        Liste des Puits
    </div>
    """, unsafe_allow_html=True)

    def style_statut(val):
        if val=="Critique":
            return "background-color:#FFE8E8;color:#CC0000;font-weight:700"
        if val=="Alerte":
            return "background-color:#FFF8E8;color:#CC7700;font-weight:700"
        return "background-color:#E8F8F0;color:#1A7A4A;font-weight:700"

    cols_aff = [c for c in
        ["nom_puits","champ","operateur","type_puits","statut","date_forage"]
        if c in df.columns]

    df_aff = df[cols_aff].copy()
    if "date_forage" in df_aff.columns:
        df_aff["date_forage"] = df_aff["date_forage"].fillna("Non renseignee")

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
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        with cd:
            cnt  = df.groupby(["champ","statut"]).size().reset_index(name="n")
            fig2 = px.bar(cnt, x="champ", y="n", color="statut",
                          title="Statut par Champ",
                          color_discrete_map={"Actif":"#27AE60",
                                              "Alerte":"#F0A500",
                                              "Critique":"#E74C3C"})
            fig2.update_layout(xaxis=dict(gridcolor="#EEE"),
                               yaxis=dict(gridcolor="#EEE"), **LAYOUT)
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

# ════════════════════════════════════════════
# PAGE 3 — ANALYSE PRODUCTION
# ════════════════════════════════════════════
elif page == "Analyse Production":

    afficher_header("📊 Analyse de Production",
                    f"Performance sur les {nb_jours} derniers jours")

    rapport = production_par_champ(nb_jours)

    if not rapport.empty:
        c1,c2,c3 = st.columns(3)
        with c1:
            kpi_card("Production Totale",
                     f"{rapport['Production_Totale'].sum():,.0f}",
                     "barils", "#E07B00", "🛢️")
        with c2:
            kpi_card("Revenus USD",
                     f"${rapport['Revenu_USD'].sum():,.0f}",
                     "", "#27AE60", "💵")
        with c3:
            kpi_card("Revenus FCFA",
                     f"{rapport['Revenu_FCFA'].sum()/1e9:.2f} Mds",
                     "francs CFA", "#2E86C1", "💶")

        st.markdown("<br>", unsafe_allow_html=True)
        cg, cd = st.columns(2)

        with cg:
            fig = go.Figure(go.Bar(
                x=rapport["champ"],
                y=rapport["Revenu_FCFA"]/1e6,
                text=[f"{v/1e6:.0f}M" for v in rapport["Revenu_FCFA"]],
                textposition="outside",
                marker=dict(color=COLORS["defaut"], line=dict(width=0))
            ))
            fig.update_layout(
                title="Revenus par Champ (Millions FCFA)",
                xaxis=dict(gridcolor="#EEE"),
                yaxis=dict(gridcolor="#EEE"), **LAYOUT
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        with cd:
            fig2 = px.pie(
                rapport, values="Production_Totale", names="champ",
                title="Part de Production par Champ",
                color_discrete_sequence=COLORS["defaut"], hole=0.4
            )
            fig2.update_layout(**LAYOUT)
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

        st.markdown("""
        <div style="color:#888;font-size:0.72rem;letter-spacing:1.5px;
                    text-transform:uppercase;margin:12px 0 8px 0;
                    font-weight:600;">Detail par Champ</div>
        """, unsafe_allow_html=True)

        aff = rapport.copy()
        aff["WaterCut_Moyen"]    = aff["WaterCut_Moyen"].map("{:.1%}".format)
        aff["Production_Totale"] = aff["Production_Totale"].map("{:,.0f} bbl".format)
        aff["Revenu_USD"]        = aff["Revenu_USD"].map("${:,.0f}".format)
        aff["Revenu_FCFA"]       = aff["Revenu_FCFA"].map("{:,.0f} FCFA".format)
        st.dataframe(aff, use_container_width=True, hide_index=True)
    else:
        st.info("Aucune donnee disponible pour cette periode.")

# ════════════════════════════════════════════
# PAGE 4 — SAISIE DES DONNÉES
# ════════════════════════════════════════════
elif page == "Saisie des Donnees":

    afficher_header("📝 Saisie des Donnees de Production",
                    "3 modes pour entrer vos donnees dans le systeme")

    tab1, tab2, tab3 = st.tabs([
        "  Saisie Manuelle  ",
        "  Import Excel/CSV  ",
        "  URL / API / Coller  "
    ])

    # ── ONGLET 1 — SAISIE MANUELLE ──
    with tab1:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="background:#FFF8F0;border:1px solid #E07B0030;
                    border-radius:10px;padding:14px 18px;margin-bottom:20px;
                    color:#666;font-size:0.85rem;">
            L'ingenieur terrain remplit ce formulaire chaque matin
            depuis son telephone apres releve des compteurs.
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            date_saisie = st.date_input("Date de production",
                                         value=date.today())
            puits_saisi = st.selectbox("Puits",
                                        list(PROFILS_PUITS.keys()))
            champ_auto  = PROFILS_PUITS[puits_saisi]["champ"]
            st.markdown(
                f'<div style="background:#FFF0DC;border:1px solid #E07B0030;'
                f'border-radius:8px;padding:8px 14px;margin:4px 0 12px 0;'
                f'color:#E07B00;font-size:0.85rem;font-weight:600;">'
                f'Champ : {champ_auto}</div>',
                unsafe_allow_html=True
            )
            production  = st.number_input("Production huile (bbl/j)",
                                           min_value=0.0, value=5000.0,
                                           step=50.0)
            wc_pct      = st.slider("Water Cut (%)", 0.0, 100.0,
                                     35.0, 0.1)
            wc          = wc_pct / 100

        with col2:
            gor         = st.number_input("GOR (scf/stb)",
                                           min_value=0.0, value=800.0,
                                           step=10.0)
            pression    = st.number_input("Pression tete (psi)",
                                           min_value=0.0, value=380.0,
                                           step=5.0)
            temperature = st.number_input("Temperature (deg F)",
                                           min_value=0.0, value=175.0,
                                           step=1.0)
            heures      = st.slider("Heures de production", 0, 24, 24)
            st.text_area("Commentaire terrain",
                          placeholder="Observations, incidents...")

        prod_eau = production * wc / max(1-wc, 0.01)
        prod_gaz = production * gor / 1000
        statut   = ("Critique" if wc>0.65 else
                    "Alerte"   if wc>0.50 else "Actif")

        st.divider()
        c1,c2,c3,c4 = st.columns(4)
        with c1: kpi_card("Huile",  f"{production:,.0f}", "bbl/j",
                           "#E07B00", "🛢️")
        with c2: kpi_card("Eau",    f"{prod_eau:,.0f}",   "bbl/j",
                           "#2E86C1", "💧")
        with c3: kpi_card("Gaz",    f"{prod_gaz:.1f}",    "MMscf/j",
                           "#27AE60", "⛽")
        with c4:
            col_statut = ("#E74C3C" if statut=="Critique" else
                          "#F0A500" if statut=="Alerte" else "#27AE60")
            kpi_card("Statut", statut, "", col_statut, "📊")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Enregistrer la mesure", type="primary",
                     use_container_width=True):
            sauvegarder_mesure(
                date_saisie, puits_saisi, champ_auto,
                production, prod_gaz, prod_eau,
                wc, gor, pression, temperature, heures, statut
            )
            st.success(
                f"Mesure enregistree — {puits_saisi} | "
                f"{production:,.0f} bbl/j | WC: {wc_pct:.1f}% | "
                f"{date_saisie.strftime('%d/%m/%Y')}"
            )
            st.balloons()

    # ── ONGLET 2 — IMPORT EXCEL / CSV ──
    with tab2:
        st.markdown("<br>", unsafe_allow_html=True)

        # Modele
        st.subheader("1. Telecharger le modele")
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
        st.download_button(
            "Telecharger le modele CSV",
            data=modele.to_csv(index=False).encode("utf-8"),
            file_name="modele_petroci.csv",
            mime="text/csv"
        )

        st.divider()
        st.subheader("2. Uploader votre fichier")
        fichier = st.file_uploader("Fichier .xlsx ou .csv",
                                    type=["xlsx","csv"])

        if fichier:
            try:
                df_import = (pd.read_csv(fichier)
                             if fichier.name.endswith(".csv")
                             else pd.read_excel(fichier))
                st.success(f"{len(df_import)} lignes detectees")
                st.dataframe(df_import.head(8), use_container_width=True)

                cols_req  = ["date","puits","champ",
                             "production_huile_bbl","water_cut"]
                manquants = [c for c in cols_req
                             if c not in df_import.columns]
                if manquants:
                    st.error(f"Colonnes manquantes : {manquants}")
                else:
                    c1,c2,c3 = st.columns(3)
                    c1.metric("Lignes", len(df_import))
                    c2.metric("Puits", df_import["puits"].nunique())
                    c3.metric("Periode",
                              f"{df_import['date'].min()} a "
                              f"{df_import['date'].max()}")

                    if st.button("Importer toutes les donnees",
                                 type="primary",
                                 use_container_width=True):
                        conn   = sqlite3.connect(DB_PATH,
                                                  check_same_thread=False)
                        succes = 0
                        for _, row in df_import.iterrows():
                            try:
                                conn.cursor().execute("""
                                    INSERT OR REPLACE INTO production_journaliere
                                    (date,puits,champ,
                                     production_huile_bbl,
                                     production_gaz_mmscf,
                                     production_eau_bbl,
                                     water_cut,gor,
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
                        st.success(f"{succes} lignes importees avec succes")
                        st.balloons()
            except Exception as e:
                st.error(f"Erreur : {e}")

    # ── ONGLET 3 — URL / API / COLLER ──
    with tab3:
        st.markdown("<br>", unsafe_allow_html=True)
        source = st.radio("Type de source", [
            "Coller les donnees (CSV)",
            "URL fichier CSV",
            "API JSON"
        ])

        if source == "Coller les donnees (CSV)":
            st.caption("Format : date,puits,champ,"
                       "production_huile_bbl,water_cut,statut")
            donnees = st.text_area("Donnees CSV", height=180,
                placeholder=(
                    "date,puits,champ,production_huile_bbl,water_cut,statut\n"
                    "2026-04-26,Baleine-1,Baleine,8500,0.35,Actif\n"
                    "2026-04-26,Sankofa-1,Sankofa,5200,0.20,Actif"
                ))
            if donnees and st.button("Importer", type="primary",
                                      use_container_width=True):
                try:
                    from io import StringIO
                    df_c   = pd.read_csv(StringIO(donnees))
                    conn   = sqlite3.connect(DB_PATH, check_same_thread=False)
                    succes = 0
                    for _, row in df_c.iterrows():
                        try:
                            conn.cursor().execute("""
                                INSERT OR REPLACE INTO production_journaliere
                                (date,puits,champ,
                                 production_huile_bbl,water_cut,statut)
                                VALUES (?,?,?,?,?,?)
                            """, (str(row.get("date","")),
                                  str(row.get("puits","")),
                                  str(row.get("champ","")),
                                  float(row.get("production_huile_bbl",0)),
                                  float(row.get("water_cut",0)),
                                  str(row.get("statut","Actif"))))
                            succes += 1
                        except Exception:
                            pass
                    conn.commit(); conn.close()
                    st.success(f"{succes} lignes importees")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erreur : {e}")

        elif source == "URL fichier CSV":
            url = st.text_input("URL", placeholder="https://...")
            if url and st.button("Charger", type="primary"):
                try:
                    df_url = pd.read_csv(url)
                    st.success(f"{len(df_url)} lignes chargees")
                    st.dataframe(df_url.head())
                except Exception as e:
                    st.error(f"Impossible de charger : {e}")
        else:
            url_api = st.text_input("URL API",
                                     placeholder="https://api...")
            token   = st.text_input("Token", type="password")
            if url_api and st.button("Appeler l'API", type="primary"):
                try:
                    import urllib.request, json
                    h   = ({"Authorization": f"Bearer {token}"}
                            if token else {})
                    req = urllib.request.Request(url_api, headers=h)
                    with urllib.request.urlopen(req, timeout=10) as r:
                        data = json.loads(r.read())
                    df_api = pd.DataFrame(
                        data if isinstance(data, list)
                        else data.get("data",[data])
                    )
                    st.success(f"{len(df_api)} enregistrements recus")
                    st.dataframe(df_api.head())
                except Exception as e:
                    st.error(f"Erreur API : {e}")

# ════════════════════════════════════════════
# PAGE 5 — ALERTES
# ════════════════════════════════════════════
elif page == "Alertes":

    afficher_header("⚠️ Systeme d'Alertes",
                    "Surveillance en temps reel des seuils critiques")

    if st.button("Verifier toutes les alertes",
                 use_container_width=True):
        nb = len(verifier_alertes())
        st.success(f"Verification terminee — {nb} alertes generees")

    df_al = lire_alertes(resolues=False)

    if not df_al.empty:
        c1,c2,c3 = st.columns(3)
        with c1: kpi_card("Total Alertes", str(len(df_al)),
                           "actives", "#F0A500", "⚠️")
        with c2: kpi_card("Critiques",
                           str(int((df_al["niveau"]=="CRITIQUE").sum())),
                           "intervention requise", "#E74C3C", "🔴")
        with c3: kpi_card("Alertes",
                           str(int((df_al["niveau"]=="ALERTE").sum())),
                           "surveillance", "#F0A500", "⚠️")
        st.markdown("<br>", unsafe_allow_html=True)

        for _, a in df_al[df_al["niveau"]=="CRITIQUE"].iterrows():
            alerte_box("CRITIQUE", a["puits"], a["champ"],
                       a["type_alerte"], a["message"])
        for _, a in df_al[df_al["niveau"]=="ALERTE"].iterrows():
            alerte_box("ALERTE", a["puits"], a["champ"],
                       a["type_alerte"], a["message"])
    else:
        st.markdown("""
        <div style="background:#E8F8F0;border:1px solid #27AE6040;
                    border-radius:10px;padding:24px;text-align:center;
                    color:#1A7A4A;font-size:1rem;margin-top:20px;
                    font-weight:600;">
            Aucune alerte active — Tous les puits fonctionnent normalement
        </div>
        """, unsafe_allow_html=True)

# ════════════════════════════════════════════
# PAGE 6 — DÉCLIN & PRÉVISIONS
# ════════════════════════════════════════════
elif page == "Declin et Previsions":

    afficher_header("📈 Declin et Previsions",
                    "Analyse de performance et tendances de production")

    puits_choisi = st.selectbox("Choisir un puits",
                                 list(PROFILS_PUITS.keys()))
    declin       = calculer_declin(puits_choisi, nb_jours)

    if declin:
        c1,c2,c3,c4 = st.columns(4)
        with c1: kpi_card("Production Debut",
                           f"{declin['production_debut']:,.0f}",
                           "bbl/j", "#2E86C1", "📅")
        with c2: kpi_card("Production Actuelle",
                           f"{declin['production_actuelle']:,.0f}",
                           "bbl/j", "#E07B00", "🛢️")
        with c3: kpi_card("Declin Total",
                           f"{declin['declin_total_pct']:.1f}%",
                           "", "#E74C3C", "📉")
        with c4: kpi_card("Declin Mensuel",
                           f"{declin['declin_mensuel_pct']:.1f}%",
                           "par mois", "#E74C3C", "📊")

    df_p = lire_production(date_debut=str(date_debut),
                            date_fin=str(date_fin),
                            puits=puits_choisi)

    if not df_p.empty:
        df_p = df_p.sort_values("date")
        fig  = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_p["date"], y=df_p["production_huile_bbl"],
            name="Production Huile", mode="lines",
            fill="tozeroy", fillcolor="rgba(224,123,0,0.1)",
            line=dict(color="#E07B00", width=2.5)
        ))
        fig.add_trace(go.Scatter(
            x=df_p["date"],
            y=df_p["water_cut"].astype(float) *
              df_p["production_huile_bbl"].astype(float).max(),
            name="Water Cut (normalise)", mode="lines",
            line=dict(color="#E74C3C", width=1.5, dash="dash")
        ))
        fig.update_layout(
            title=f"Courbe de Declin — {puits_choisi}",
            xaxis=dict(gridcolor="#EEE", color="#666"),
            yaxis=dict(gridcolor="#EEE", color="#666",
                       title="Production (bbl/jour)"),
            legend=dict(bgcolor="white",
                        bordercolor="rgba(224,123,0,0.3)"),
            hovermode="x unified", **LAYOUT
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Aucune donnee pour ce puits sur la periode.")

# ════════════════════════════════════════════
# PAGE 7 — RAPPORTS (CSV + PDF)
# ════════════════════════════════════════════
elif page == "Rapports":

    afficher_header("📋 Generation de Rapports",
                    "Rapports automatiques — Export CSV et PDF")

    type_r = st.selectbox("Type de rapport", [
        "Rapport Production par Champ",
        "Rapport Performance Operateurs",
        "Rapport Alertes Actives",
    ])

    if st.button("Generer le Rapport", type="primary",
                 use_container_width=True):
        with st.spinner("Generation en cours..."):
            rapport = production_par_champ(nb_jours)

            st.markdown(f"""
            <div style="background:white;border:1px solid #EEE;
                        border-left:5px solid #E07B00;border-radius:10px;
                        padding:16px 20px;margin:16px 0;">
                <div style="color:#E07B00;font-size:1rem;font-weight:700;
                            margin-bottom:6px;">{type_r}</div>
                <div style="color:#888;font-size:0.8rem;">
                    Periode : {date_debut} a {date_fin} &nbsp;|&nbsp;
                    Genere le : {date.today().strftime('%d/%m/%Y')}
                </div>
            </div>
            """, unsafe_allow_html=True)

            if not rapport.empty:
                prod_tot = rapport["Production_Totale"].sum()
                rev_tot  = rapport["Revenu_USD"].sum()

                c1,c2,c3 = st.columns(3)
                with c1: kpi_card("Production",
                                   f"{prod_tot:,.0f}", "bbl",
                                   "#E07B00","🛢️")
                with c2: kpi_card("Revenus USD",
                                   f"${rev_tot:,.0f}", "",
                                   "#27AE60","💵")
                with c3: kpi_card("Revenus FCFA",
                                   f"{rev_tot*TAUX/1e9:.2f} Mds", "",
                                   "#2E86C1","💶")

                st.markdown("<br>", unsafe_allow_html=True)

                if type_r == "Rapport Performance Operateurs":
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
                        st.dataframe(grp, use_container_width=True,
                                     hide_index=True)

                elif type_r == "Rapport Alertes Actives":
                    df_al = lire_alertes(resolues=False)
                    (st.dataframe(df_al, use_container_width=True,
                                  hide_index=True)
                     if not df_al.empty
                     else st.success("Aucune alerte active."))
                else:
                    aff = rapport.copy()
                    aff["WaterCut_Moyen"]    = aff["WaterCut_Moyen"].map("{:.1%}".format)
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
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

                st.divider()
                st.subheader("Exporter le rapport")
                col_csv, col_pdf = st.columns(2)

                # Export CSV
                with col_csv:
                    st.download_button(
                        "Telecharger en CSV",
                        data=rapport.to_csv(index=False).encode("utf-8"),
                        file_name=f"rapport_petroci_{date.today()}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

                # Export PDF
                with col_pdf:
                    pdf_bytes = generer_pdf_rapport(
                        rapport, type_r, date_debut, date_fin, nb_jours
                    )
                    if pdf_bytes:
                        st.download_button(
                            "Telecharger en PDF",
                            data=pdf_bytes,
                            file_name=f"rapport_petroci_{date.today()}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    else:
                        st.info("PDF : ajouter 'reportlab' au requirements.txt")

                st.success("Rapport genere avec succes")
            else:
                st.warning("Aucune donnee disponible.")
