"""
PETRO AFRICA — Module ESG & Flaring
Suivi torchage, émissions CO2, conformité réglementaire PETROCI.
Objectif zéro torchage systématique Côte d'Ivoire 2030.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from config import (
    CO2_PAR_TONNE_GAZ_TORCHE,
    GAZ_DENSITÉ_KG_M3,
    METHANE_GWP100,
    FLARING_FRACTION_DEFAULT,
    PETROCI_FLARING_TARGET_PCT,
    PRIX_GAZ_MMBTU,
    GAZ_MMBTU_PAR_BOE,
)

# ─── Palette ─────────────────────────────────────────────────────────────────
COLORS = {
    "primary": "#1B4F72",
    "accent":  "#F39C12",
    "success": "#27AE60",
    "danger":  "#E74C3C",
    "warning": "#E67E22",
    "esg":     "#16A085",   # teal ESG
    "bg_card": "#1A2332",
    "text":    "#ECF0F1",
}


# ═══════════════════════════════════════════════════════════════════════════════
#  CALCULS ESG
# ═══════════════════════════════════════════════════════════════════════════════

def calculer_emissions_flaring(
    prod_gaz_mmscfd: float,
    flaring_pct: float,
) -> dict:
    """
    Calcule les émissions liées au torchage.

    Paramètres
    ----------
    prod_gaz_mmscfd : Production gaz totale en MMscfd
    flaring_pct     : Fraction torchée (%)

    Retourne un dict avec toutes les métriques ESG.
    """
    # Volume torché par jour (MMscfd)
    vol_torche_mmscfd = prod_gaz_mmscfd * (flaring_pct / 100)

    # Conversion en m³/j (1 MMscfd ≈ 28 316 m³/j)
    vol_torche_m3j = vol_torche_mmscfd * 28_316.85

    # Masse gaz torché (tonnes/j)
    masse_torche_tj = vol_torche_m3j * GAZ_DENSITÉ_KG_M3 / 1000

    # CO2 équivalent direct combustion (tCO2/j)
    co2_combustion_tj = masse_torche_tj * CO2_PAR_TONNE_GAZ_TORCHE

    # CH4 non brûlé (efficacité flare ~ 98%)
    efficacite_flare = 0.98
    ch4_non_brule_tj = masse_torche_tj * (1 - efficacite_flare) * 0.85  # 85% CH4

    # CO2e méthane (GWP100)
    co2e_ch4_tj = ch4_non_brule_tj * METHANE_GWP100

    # CO2 total équivalent (tCO2e/j)
    co2e_total_tj = co2_combustion_tj + co2e_ch4_tj

    # Annuel
    co2e_total_an  = co2e_total_tj * 365
    vol_torche_mman = vol_torche_mmscfd * 365  # MMscf/an

    # Valeur économique perdue (revenu gaz non vendu)
    # 1 MMscfd = 1000 MMBtu/j
    valeur_perdue_j  = vol_torche_mmscfd * 1_000 * PRIX_GAZ_MMBTU  # USD/j
    valeur_perdue_an = valeur_perdue_j * 365  # USD/an

    # Intensité carbone (kgCO2e/BOE produit)
    boe_total_j = prod_gaz_mmscfd * 1_000 / GAZ_MMBTU_PAR_BOE
    intensite_carbone = (co2e_total_tj * 1000 / boe_total_j) if boe_total_j > 0 else 0

    return {
        "vol_torche_mmscfd":    round(vol_torche_mmscfd, 3),
        "vol_torche_mman":      round(vol_torche_mman, 1),
        "co2_combustion_tj":    round(co2_combustion_tj, 2),
        "co2e_ch4_tj":          round(co2e_ch4_tj, 2),
        "co2e_total_tj":        round(co2e_total_tj, 2),
        "co2e_total_an":        round(co2e_total_an),
        "valeur_perdue_j":      round(valeur_perdue_j),
        "valeur_perdue_an":     round(valeur_perdue_an),
        "intensite_carbone":    round(intensite_carbone, 2),
        "conformite_petroci":   flaring_pct <= PETROCI_FLARING_TARGET_PCT,
        "statut":               "✅ Conforme" if flaring_pct <= PETROCI_FLARING_TARGET_PCT
                                else ("⚠️ Surveillance" if flaring_pct <= 5.0 else "🔴 Non conforme"),
    }


def generer_serie_temporelle_esg(
    prod_gaz_mmscfd: float,
    flaring_pct_actuel: float,
    annees: int = 10,
    objectif_reduction_pct: float = 0.15,   # 15% réduction par an du flaring
) -> pd.DataFrame:
    """
    Simule la trajectoire ESG sur N années avec plan de réduction du torchage.
    """
    rows = []
    fp = flaring_pct_actuel
    for a in range(1, annees + 1):
        # Plan de réduction du torchage
        fp = max(PETROCI_FLARING_TARGET_PCT, fp * (1 - objectif_reduction_pct))
        prod = prod_gaz_mmscfd * ((1 - 0.05) ** a)  # déclin 5% gaz/an

        em = calculer_emissions_flaring(prod, fp)
        rows.append({
            "Année":               datetime.now().year + a,
            "Flaring (%)":         round(fp, 2),
            "Prod. Gaz (MMscfd)":  round(prod, 2),
            "CO2e Annuel (ktCO2)": round(em["co2e_total_an"] / 1000, 1),
            "Valeur Perdue (kUSD)":round(em["valeur_perdue_an"] / 1000, 1),
            "Statut":              em["statut"],
        })
    return pd.DataFrame(rows)


def score_esg(emissions: dict, prod_gaz: float, flaring_pct: float) -> dict:
    """
    Score ESG simplifié sur 100 points, axe Afrique de l'Ouest.
    """
    score_flaring   = max(0, 40 - flaring_pct * 4)          # /40
    score_intensite = max(0, 30 - emissions["intensite_carbone"] * 1.5)  # /30
    score_valeur    = min(30, 30 * (1 - flaring_pct / 20))  # /30

    total = score_flaring + score_intensite + score_valeur
    grade = ("A" if total >= 85 else "B" if total >= 70 else
             "C" if total >= 55 else "D" if total >= 40 else "F")
    return {
        "score_total":   round(total),
        "score_flaring": round(score_flaring),
        "score_intensite": round(score_intensite),
        "score_valeur":  round(score_valeur),
        "grade":         grade,
        "grade_color":   ("#27AE60" if grade in ("A", "B") else
                          "#F39C12" if grade == "C" else "#E74C3C"),
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  GRAPHIQUES
# ═══════════════════════════════════════════════════════════════════════════════

def fig_gauge_flaring(flaring_pct: float) -> go.Figure:
    """Jauge de torchage avec seuils réglementaires."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=flaring_pct,
        delta={"reference": PETROCI_FLARING_TARGET_PCT, "suffix": "%"},
        number={"suffix": "%", "font": {"size": 36}},
        title={"text": "Taux de Torchage", "font": {"size": 16}},
        gauge={
            "axis": {"range": [0, 20], "ticksuffix": "%"},
            "bar":  {"color": COLORS["accent"]},
            "steps": [
                {"range": [0, 2],  "color": "#27AE60"},
                {"range": [2, 5],  "color": "#F39C12"},
                {"range": [5, 10], "color": "#E67E22"},
                {"range": [10, 20],"color": "#E74C3C"},
            ],
            "threshold": {
                "line": {"color": "white", "width": 3},
                "thickness": 0.75,
                "value": PETROCI_FLARING_TARGET_PCT,
            },
        },
    ))
    fig.update_layout(
        height=280, template="plotly_dark",
        paper_bgcolor=COLORS["bg_card"],
        font=dict(color=COLORS["text"]),
        margin=dict(t=40, b=10, l=10, r=10),
    )
    return fig


def fig_co2_trajectory(df_traj: pd.DataFrame) -> go.Figure:
    """Trajectoire CO2e et flaring sur N années."""
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df_traj["Année"], y=df_traj["CO2e Annuel (ktCO2)"],
        name="CO2e Annuel (ktCO2)",
        marker_color=[COLORS["success"] if s == "✅ Conforme" else
                      COLORS["warning"] if "Surveillance" in s else COLORS["danger"]
                      for s in df_traj["Statut"]],
    ))
    fig.add_trace(go.Scatter(
        x=df_traj["Année"], y=df_traj["Flaring (%)"],
        name="Flaring (%)",
        yaxis="y2",
        line=dict(color=COLORS["accent"], width=3, dash="dot"),
        mode="lines+markers",
    ))

    fig.update_layout(
        height=360, template="plotly_dark",
        paper_bgcolor=COLORS["bg_card"],
        plot_bgcolor=COLORS["bg_card"],
        font=dict(color=COLORS["text"]),
        title="Trajectoire Émissions & Torchage — Plan Réduction",
        yaxis=dict(title="CO2e (ktCO2/an)"),
        yaxis2=dict(title="Flaring (%)", overlaying="y", side="right",
                    ticksuffix="%", range=[0, 12]),
        legend=dict(x=0.01, y=0.99),
        margin=dict(t=50, b=20, l=10, r=50),
    )
    return fig


def fig_emissions_breakdown(emissions: dict) -> go.Figure:
    """Pie chart décomposition CO2e."""
    fig = go.Figure(go.Pie(
        labels=["CO2 combustion", "CH4 non brûlé (CO2e)"],
        values=[emissions["co2_combustion_tj"], emissions["co2e_ch4_tj"]],
        marker=dict(colors=[COLORS["warning"], COLORS["danger"]]),
        hole=0.5,
        textfont_size=13,
    ))
    fig.update_layout(
        height=260, template="plotly_dark",
        paper_bgcolor=COLORS["bg_card"],
        font=dict(color=COLORS["text"]),
        title="Décomposition CO2e/jour",
        margin=dict(t=40, b=10, l=10, r=10),
        showlegend=True,
    )
    return fig


def fig_score_radar(score: dict) -> go.Figure:
    """Radar chart score ESG."""
    categories = ["Flaring", "Intensité Carbone", "Valeur Récupérée"]
    values = [score["score_flaring"], score["score_intensite"], score["score_valeur"]]
    max_vals = [40, 30, 30]
    norm = [v / m * 100 for v, m in zip(values, max_vals)]

    fig = go.Figure(go.Scatterpolar(
        r=norm + [norm[0]],
        theta=categories + [categories[0]],
        fill="toself",
        fillcolor=f"rgba(22,160,133,0.3)",
        line=dict(color=COLORS["esg"], width=2),
        name="Score ESG",
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], ticksuffix="%"),
            bgcolor=COLORS["bg_card"],
        ),
        height=280, template="plotly_dark",
        paper_bgcolor=COLORS["bg_card"],
        font=dict(color=COLORS["text"]),
        title="Score ESG par Axe",
        margin=dict(t=50, b=10, l=10, r=10),
        showlegend=False,
    )
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE STREAMLIT
# ═══════════════════════════════════════════════════════════════════════════════

def render_esg_page():
    """
    Appeler depuis dashboard.py :
        from esg_flaring import render_esg_page
        render_esg_page()
    """
    st.markdown("""
    <style>
    .esg-card {
        background: #1A2332; border: 1px solid #16A085;
        border-radius: 10px; padding: 1rem 1.2rem; text-align: center;
    }
    .esg-val  { font-size: 1.7rem; font-weight: 700; margin: 0; }
    .esg-lbl  { font-size: 0.76rem; color: #95A5A6; margin: 0; }
    .grade-badge {
        font-size: 3rem; font-weight: 900; text-align: center;
        padding: 0.5rem; border-radius: 12px; display: inline-block;
        min-width: 70px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("🌿 Module ESG & Flaring")
    st.caption(
        "Suivi torchage · Émissions CO2 équivalent · Conformité PETROCI · Score ESG"
    )

    # ── Paramètres sidebar ──────────────────────────────────────────────────
    with st.sidebar:
        st.header("⚙️ Paramètres ESG")
        prod_gaz  = st.number_input("Production gaz totale (MMscfd)", 1.0, 500.0, 50.0, 1.0)
        flaring   = st.slider("Taux de torchage actuel (%)", 0.0, 20.0,
                               FLARING_FRACTION_DEFAULT * 100, 0.1)
        horizon   = st.slider("Horizon de projection (ans)", 3, 20, 10)
        red_plan  = st.slider("Réduction annuelle flaring prévue (%)", 0, 50, 15)

        st.markdown("---")
        st.info(
            f"🎯 Objectif PETROCI 2030 : **{PETROCI_FLARING_TARGET_PCT}%** max\n\n"
            f"📋 Référence : Code Pétrolier CI + Engagement GGFR (World Bank)"
        )

    # ── Calculs ─────────────────────────────────────────────────────────────
    em = calculer_emissions_flaring(prod_gaz, flaring)
    sc = score_esg(em, prod_gaz, flaring)
    df_traj = generer_serie_temporelle_esg(prod_gaz, flaring, horizon, red_plan / 100)

    # ── Header statut ───────────────────────────────────────────────────────
    st.subheader(f"Statut Réglementaire : {em['statut']}")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f"""<div class="esg-card">
          <p class="esg-val" style="color:#E74C3C">{em['vol_torche_mmscfd']}</p>
          <p class="esg-lbl">MMscfd torchés/jour</p></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="esg-card">
          <p class="esg-val" style="color:#E67E22">{em['co2e_total_tj']:,}</p>
          <p class="esg-lbl">tCO2e/jour</p></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="esg-card">
          <p class="esg-val" style="color:#F39C12">{em['co2e_total_an']:,}</p>
          <p class="esg-lbl">tCO2e/an</p></div>""", unsafe_allow_html=True)
    with c4:
        vp = em['valeur_perdue_an'] / 1_000_000
        st.markdown(f"""<div class="esg-card">
          <p class="esg-val" style="color:#E74C3C">{vp:.2f} M$</p>
          <p class="esg-lbl">Valeur perdue/an</p></div>""", unsafe_allow_html=True)
    with c5:
        st.markdown(f"""<div class="esg-card">
          <p class="esg-val" style="color:#16A085">{em['intensite_carbone']}</p>
          <p class="esg-lbl">kgCO2e/BOE</p></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Score ESG ───────────────────────────────────────────────────────────
    col_grade, col_radar, col_gauge = st.columns([1, 2, 2])
    with col_grade:
        st.markdown("**Score ESG Global**")
        st.markdown(
            f'<div class="grade-badge" style="background:{sc["grade_color"]}20;'
            f'color:{sc["grade_color"]};border:2px solid {sc["grade_color"]}">'
            f'{sc["grade"]}</div>', unsafe_allow_html=True
        )
        st.metric("Score / 100", sc["score_total"])
        st.caption("A≥85 · B≥70 · C≥55 · D≥40 · F<40")
    with col_radar:
        st.plotly_chart(fig_score_radar(sc), use_container_width=True)
    with col_gauge:
        st.plotly_chart(fig_gauge_flaring(flaring), use_container_width=True)

    # ── Décomposition émissions & trajectoire ───────────────────────────────
    col_l, col_r = st.columns([1, 3])
    with col_l:
        st.plotly_chart(fig_emissions_breakdown(em), use_container_width=True)
    with col_r:
        st.plotly_chart(fig_co2_trajectory(df_traj), use_container_width=True)

    # ── Tableau de projection ────────────────────────────────────────────────
    st.subheader("📋 Plan de Réduction — Projection Annuelle")

    def color_statut(val):
        if "Conforme" in val:   return "color: #27AE60"
        if "Surveillance" in val: return "color: #F39C12"
        return "color: #E74C3C"

    st.dataframe(
        df_traj.style
               .applymap(color_statut, subset=["Statut"])
               .format({"Flaring (%)": "{:.2f}", "CO2e Annuel (ktCO2)": "{:.1f}",
                         "Valeur Perdue (kUSD)": "{:,.0f}"})
               .set_properties(**{"background-color": "#1A2332", "color": "#ECF0F1"}),
        use_container_width=True,
        hide_index=True,
    )

    # ── Recommandations ──────────────────────────────────────────────────────
    st.subheader("📌 Recommandations Réglementaires")
    recs = []
    if flaring > PETROCI_FLARING_TARGET_PCT:
        recs.append(f"🔴 Taux actuel **{flaring:.1f}%** dépasse l'objectif PETROCI "
                    f"(**{PETROCI_FLARING_TARGET_PCT}%**). Plan de réduction requis.")
    if em["valeur_perdue_an"] > 1_000_000:
        recs.append(f"💰 **{em['valeur_perdue_an']/1e6:.2f} M$/an** de gaz perdu. "
                    f"Étude de valorisation (injection/GPL/électricité) recommandée.")
    if em["intensite_carbone"] > 20:
        recs.append("⚠️ Intensité carbone élevée. Audit équipements de torche "
                    "et programme LDAR (Leak Detection And Repair) suggéré.")
    if not recs:
        recs.append("✅ Performances dans les normes. Maintenir le suivi mensuel.")

    for r in recs:
        st.markdown(f"- {r}")

    st.caption(
        "Sources : PETROCI Code Pétrolier 1996 (amdt 2012) · GIEC AR6 · "
        "World Bank GGFR · API RP 521 · Engagement CI ZéroTorchage 2030"
    )


if __name__ == "__main__":
    render_esg_page()
