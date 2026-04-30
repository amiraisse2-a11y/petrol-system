"""
PETRO AFRICA — Module Finances
NPV, IRR, Break-even, CAPEX/OPEX, Cash Flow
Destiné aux décideurs et investisseurs institutionnels.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# ─── Palette PETRO AFRICA ───────────────────────────────────────────────────
COLORS = {
    "primary":   "#1B4F72",   # bleu pétrole
    "accent":    "#F39C12",   # or/orange
    "success":   "#27AE60",
    "danger":    "#E74C3C",
    "neutral":   "#2C3E50",
    "bg_card":   "#1A2332",
    "text_light":"#ECF0F1",
}


# ═══════════════════════════════════════════════════════════════════════════════
#  CALCULS FINANCIERS
# ═══════════════════════════════════════════════════════════════════════════════

def calculer_npv(cash_flows: list[float], taux_actualisation: float) -> float:
    """Valeur Actuelle Nette (USD)."""
    npv = 0.0
    for t, cf in enumerate(cash_flows):
        npv += cf / ((1 + taux_actualisation) ** t)
    return npv


def calculer_irr(cash_flows: list[float], precision: float = 1e-6) -> float | None:
    """Taux de Rendement Interne (bisection)."""
    lo, hi = -0.999, 10.0
    for _ in range(1000):
        mid = (lo + hi) / 2
        npv = calculer_npv(cash_flows, mid)
        if abs(npv) < precision:
            return mid
        if npv > 0:
            lo = mid
        else:
            hi = mid
    return None


def calculer_payback(cash_flows: list[float]) -> float | None:
    """Délai de récupération (années)."""
    cumul = 0.0
    for i, cf in enumerate(cash_flows):
        prev = cumul
        cumul += cf
        if cumul >= 0 and prev < 0:
            frac = -prev / cf if cf != 0 else 0
            return i + frac
    return None


def generer_cash_flows(
    prix_baril: float,
    prix_gaz: float,
    production_huile_bopd: float,
    production_gaz_mmscfd: float,
    capex_m: float,          # MUSD
    opex_boe: float,         # USD/BOE
    royalties_pct: float,    # %
    impot_pct: float,        # %
    duree_ans: int,
    decline_rate: float,     # % annuel
    capex_schedule: dict,    # {annee: fraction_capex}
) -> pd.DataFrame:
    """
    Génère le tableau de flux de trésorerie projet sur duree_ans.
    Retourne un DataFrame avec toutes les lignes P&L.
    """
    rows = []
    prod_huile = production_huile_bopd
    prod_gaz   = production_gaz_mmscfd

    for annee in range(1, duree_ans + 1):
        # Production avec déclin exponentiel (sauf année 1)
        if annee > 1:
            prod_huile *= (1 - decline_rate / 100)
            prod_gaz   *= (1 - decline_rate / 100)

        # Revenus bruts annuels
        rev_huile = prod_huile * 365 * prix_baril          # USD
        # Conversion gaz : 1 MMscfd × 365 j = 365 MMBtu/j → ×365 = MMBtu/an
        rev_gaz   = prod_gaz * 365 * 1_000 * prix_gaz      # USD (1 MMscfd = 1000 MMBtu/j)
        revenus   = rev_huile + rev_gaz

        # CAPEX (engagé selon schedule)
        frac_capex = capex_schedule.get(annee, 0.0)
        capex_annee = frac_capex * capex_m * 1_000_000      # USD

        # BOE total pour OPEX
        boe_huile = prod_huile * 365
        boe_gaz   = prod_gaz * 365 * 1_000 / 5.8            # MMBtu→BOE
        opex_annee = (boe_huile + boe_gaz) * opex_boe

        # Royalties & Impôts
        royalties = revenus * (royalties_pct / 100)
        ebit      = revenus - opex_annee - royalties - capex_annee
        impots    = max(0, ebit * (impot_pct / 100))
        net_cf    = ebit - impots

        rows.append({
            "Année":         annee,
            "Prod. Huile (BOPD)": round(prod_huile),
            "Prod. Gaz (MMscfd)": round(prod_gaz, 2),
            "Revenus (MUSD)":     round(revenus / 1e6, 2),
            "CAPEX (MUSD)":       round(capex_annee / 1e6, 2),
            "OPEX (MUSD)":        round(opex_annee / 1e6, 2),
            "Royalties (MUSD)":   round(royalties / 1e6, 2),
            "EBIT (MUSD)":        round(ebit / 1e6, 2),
            "Impôts (MUSD)":      round(impots / 1e6, 2),
            "Cash Flow Net (MUSD)": round(net_cf / 1e6, 2),
        })

    df = pd.DataFrame(rows)
    df["Cash Flow Cumulé (MUSD)"] = df["Cash Flow Net (MUSD)"].cumsum()
    return df


# ═══════════════════════════════════════════════════════════════════════════════
#  GRAPHIQUES
# ═══════════════════════════════════════════════════════════════════════════════

def fig_waterfall(df: pd.DataFrame) -> go.Figure:
    """Waterfall Cash Flow cumulé + annuel."""
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("Cash Flow Annuel Net (MUSD)", "Cash Flow Cumulé (MUSD)"),
        vertical_spacing=0.12,
    )
    colors_bar = [COLORS["success"] if v >= 0 else COLORS["danger"]
                  for v in df["Cash Flow Net (MUSD)"]]

    fig.add_trace(go.Bar(
        x=df["Année"], y=df["Cash Flow Net (MUSD)"],
        marker_color=colors_bar, name="CF Annuel",
        text=[f"{v:.1f}" for v in df["Cash Flow Net (MUSD)"]],
        textposition="outside",
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df["Année"], y=df["Cash Flow Cumulé (MUSD)"],
        mode="lines+markers", name="CF Cumulé",
        line=dict(color=COLORS["accent"], width=3),
        marker=dict(size=6),
    ), row=2, col=1)

    # Ligne zéro
    fig.add_hline(y=0, line_dash="dash", line_color="#AAAAAA", row=2, col=1)

    fig.update_layout(
        height=520, template="plotly_dark",
        paper_bgcolor=COLORS["bg_card"],
        plot_bgcolor=COLORS["bg_card"],
        font=dict(color=COLORS["text_light"]),
        showlegend=False,
        margin=dict(t=60, b=20, l=10, r=10),
    )
    return fig


def fig_revenus_breakdown(df: pd.DataFrame) -> go.Figure:
    """Stacked bar — décomposition des coûts vs revenus."""
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Revenus", x=df["Année"], y=df["Revenus (MUSD)"],
                         marker_color=COLORS["success"]))
    fig.add_trace(go.Bar(name="CAPEX",   x=df["Année"], y=-df["CAPEX (MUSD)"],
                         marker_color=COLORS["danger"]))
    fig.add_trace(go.Bar(name="OPEX",    x=df["Année"], y=-df["OPEX (MUSD)"],
                         marker_color="#E67E22"))
    fig.add_trace(go.Bar(name="Royalties+Impôts",
                         x=df["Année"],
                         y=-(df["Royalties (MUSD)"] + df["Impôts (MUSD)"]),
                         marker_color="#8E44AD"))
    fig.update_layout(
        barmode="relative",
        height=380, template="plotly_dark",
        paper_bgcolor=COLORS["bg_card"],
        plot_bgcolor=COLORS["bg_card"],
        font=dict(color=COLORS["text_light"]),
        title="Structure Économique du Projet (MUSD/an)",
        margin=dict(t=50, b=20, l=10, r=10),
    )
    return fig


def fig_sensitivity_npv(
    base_params: dict,
    variables: list[str],
    plage_pct: float = 20.0,
) -> go.Figure:
    """Tornado chart — sensibilité NPV aux variables clés."""
    results = []
    npv_base = base_params["npv_base"]

    for var in variables:
        npv_lo = base_params.get(f"npv_{var}_lo", npv_base * 0.75)
        npv_hi = base_params.get(f"npv_{var}_hi", npv_base * 1.25)
        results.append({"Variable": var, "NPV Lo": npv_lo, "NPV Hi": npv_hi,
                         "Spread": npv_hi - npv_lo})

    results.sort(key=lambda x: x["Spread"])
    df_s = pd.DataFrame(results)

    fig = go.Figure()
    for _, row in df_s.iterrows():
        fig.add_trace(go.Bar(
            y=[row["Variable"]],
            x=[row["NPV Lo"] - npv_base],
            orientation="h",
            marker_color=COLORS["danger"],
            showlegend=False,
            base=npv_base,
        ))
        fig.add_trace(go.Bar(
            y=[row["Variable"]],
            x=[row["NPV Hi"] - npv_base],
            orientation="h",
            marker_color=COLORS["success"],
            showlegend=False,
            base=npv_base,
        ))

    fig.add_vline(x=npv_base, line_dash="solid",
                  line_color=COLORS["accent"], line_width=2)
    fig.update_layout(
        barmode="overlay",
        height=350, template="plotly_dark",
        paper_bgcolor=COLORS["bg_card"],
        plot_bgcolor=COLORS["bg_card"],
        font=dict(color=COLORS["text_light"]),
        title=f"Analyse de Sensibilité — NPV (MUSD) | Base: {npv_base:.1f} MUSD",
        xaxis_title="NPV (MUSD)",
        margin=dict(t=50, b=20, l=160, r=20),
    )
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE STREAMLIT
# ═══════════════════════════════════════════════════════════════════════════════

def render_finances_page():
    """
    Appeler depuis dashboard.py :
        from finances import render_finances_page
        render_finances_page()
    """
    st.markdown("""
    <style>
    .fin-metric-card {
        background: #1A2332;
        border: 1px solid #2C3E50;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        text-align: center;
    }
    .fin-metric-value { font-size: 1.8rem; font-weight: 700; margin: 0; }
    .fin-metric-label { font-size: 0.78rem; color: #95A5A6; margin: 0; }
    .positive { color: #27AE60; }
    .negative { color: #E74C3C; }
    .neutral  { color: #F39C12; }
    </style>
    """, unsafe_allow_html=True)

    st.title("💰 Module Finances — Analyse Économique Projet")
    st.caption("NPV · IRR · Payback · CAPEX/OPEX · Sensibilité")

    # ── Sidebar paramètres ──────────────────────────────────────────────────
    with st.sidebar:
        st.header("⚙️ Paramètres Projet")

        st.subheader("📦 Production")
        prod_huile = st.number_input("Débit huile initial (BOPD)", 100, 50_000, 5_000, 100)
        prod_gaz   = st.number_input("Débit gaz initial (MMscfd)", 0.0, 500.0, 20.0, 0.5)
        decline    = st.slider("Taux de déclin annuel (%)", 0.0, 30.0, 10.0, 0.5)
        duree      = st.slider("Durée de vie du projet (ans)", 5, 30, 20)

        st.subheader("💲 Prix")
        prix_baril = st.number_input("Prix baril (USD/bbl)", 20.0, 200.0, 75.0, 1.0)
        prix_gaz   = st.number_input("Prix gaz (USD/MMBtu)", 1.0, 20.0, 4.5, 0.1,
                                      help="Référence Afrique de l'Ouest ≈ 4.5 USD/MMBtu")

        st.subheader("🏗️ CAPEX / OPEX")
        capex_total = st.number_input("CAPEX total (MUSD)", 1.0, 5_000.0, 500.0, 10.0)
        opex_boe    = st.number_input("OPEX (USD/BOE)", 1.0, 50.0, 12.0, 0.5)

        st.subheader("🏛️ Fiscal")
        royalties = st.slider("Royalties (%)", 0.0, 25.0, 12.5, 0.5)
        impot     = st.slider("Impôt sur bénéfices (%)", 0.0, 50.0, 30.0, 1.0)
        wacc      = st.slider("Taux d'actualisation / WACC (%)", 5.0, 25.0, 12.0, 0.5)

        st.subheader("📅 Planning CAPEX")
        capex_y1 = st.slider("CAPEX Année 1 (%)", 0, 100, 40)
        capex_y2 = st.slider("CAPEX Année 2 (%)", 0, 100 - capex_y1, 40)
        capex_y3 = 100 - capex_y1 - capex_y2
        st.info(f"CAPEX Année 3 : {capex_y3}%")

    # ── Calcul cash flows ───────────────────────────────────────────────────
    schedule = {
        1: capex_y1 / 100,
        2: capex_y2 / 100,
        3: capex_y3 / 100,
    }

    df = generer_cash_flows(
        prix_baril=prix_baril,
        prix_gaz=prix_gaz,
        production_huile_bopd=prod_huile,
        production_gaz_mmscfd=prod_gaz,
        capex_m=capex_total,
        opex_boe=opex_boe,
        royalties_pct=royalties,
        impot_pct=impot,
        duree_ans=duree,
        decline_rate=decline,
        capex_schedule=schedule,
    )

    cf_list = df["Cash Flow Net (MUSD)"].tolist()
    npv  = calculer_npv(cf_list, wacc / 100)
    irr  = calculer_irr(cf_list)
    payback = calculer_payback(df["Cash Flow Cumulé (MUSD)"].tolist())
    total_rev = df["Revenus (MUSD)"].sum()
    total_opex = df["OPEX (MUSD)"].sum()
    profit_margin = (npv / total_rev * 100) if total_rev else 0

    # ── KPI Cards ───────────────────────────────────────────────────────────
    st.subheader("📊 Indicateurs Clés")
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        color = "positive" if npv >= 0 else "negative"
        st.markdown(f"""
        <div class="fin-metric-card">
          <p class="fin-metric-value {color}">{npv:+.1f} M$</p>
          <p class="fin-metric-label">NPV @ {wacc}%</p>
        </div>""", unsafe_allow_html=True)

    with c2:
        irr_str  = f"{irr*100:.1f}%" if irr else "N/A"
        color_irr = "positive" if irr and irr * 100 > wacc else "negative"
        st.markdown(f"""
        <div class="fin-metric-card">
          <p class="fin-metric-value {color_irr}">{irr_str}</p>
          <p class="fin-metric-label">IRR (TRI)</p>
        </div>""", unsafe_allow_html=True)

    with c3:
        pb_str = f"{payback:.1f} ans" if payback else "Non atteint"
        color_pb = "positive" if payback and payback < duree * 0.6 else "neutral"
        st.markdown(f"""
        <div class="fin-metric-card">
          <p class="fin-metric-value {color_pb}">{pb_str}</p>
          <p class="fin-metric-label">Délai de récupération</p>
        </div>""", unsafe_allow_html=True)

    with c4:
        color_m = "positive" if profit_margin > 20 else "neutral"
        st.markdown(f"""
        <div class="fin-metric-card">
          <p class="fin-metric-value {color_m}">{profit_margin:.1f}%</p>
          <p class="fin-metric-label">Marge NPV/Revenus</p>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Graphiques ──────────────────────────────────────────────────────────
    col_a, col_b = st.columns([3, 2])
    with col_a:
        st.plotly_chart(fig_waterfall(df), use_container_width=True)
    with col_b:
        st.plotly_chart(fig_revenus_breakdown(df), use_container_width=True)

    # ── Analyse de sensibilité (Tornado) ────────────────────────────────────
    st.subheader("🌪️ Analyse de Sensibilité NPV")
    pct = 0.20  # ±20%

    def npv_scenario(prix_b=prix_baril, prix_g=prix_gaz, prod_h=prod_huile,
                     prod_gz=prod_gaz, cap=capex_total, op=opex_boe):
        df_s = generer_cash_flows(prix_b, prix_g, prod_h, prod_gz, cap, op,
                                   royalties, impot, duree, decline, schedule)
        return calculer_npv(df_s["Cash Flow Net (MUSD)"].tolist(), wacc / 100)

    tornado_params = {
        "npv_base": npv,
        "npv_Prix Baril_lo":   npv_scenario(prix_b=prix_baril * (1 - pct)),
        "npv_Prix Baril_hi":   npv_scenario(prix_b=prix_baril * (1 + pct)),
        "npv_Prix Gaz_lo":     npv_scenario(prix_g=prix_gaz * (1 - pct)),
        "npv_Prix Gaz_hi":     npv_scenario(prix_g=prix_gaz * (1 + pct)),
        "npv_Production Huile_lo": npv_scenario(prod_h=prod_huile * (1 - pct)),
        "npv_Production Huile_hi": npv_scenario(prod_h=prod_huile * (1 + pct)),
        "npv_CAPEX_lo":        npv_scenario(cap=capex_total * (1 - pct)),
        "npv_CAPEX_hi":        npv_scenario(cap=capex_total * (1 + pct)),
        "npv_OPEX_lo":         npv_scenario(op=opex_boe * (1 - pct)),
        "npv_OPEX_hi":         npv_scenario(op=opex_boe * (1 + pct)),
    }
    st.plotly_chart(
        fig_sensitivity_npv(tornado_params,
                            ["Prix Baril", "Prix Gaz", "Production Huile", "CAPEX", "OPEX"]),
        use_container_width=True,
    )
    st.caption("±20% variation sur chaque paramètre, toutes choses égales par ailleurs.")

    # ── Tableau détaillé ────────────────────────────────────────────────────
    st.subheader("📋 Tableau de Flux de Trésorerie Détaillé")
    st.dataframe(
        df.style
          .format({col: "{:.2f}" for col in df.columns if "MUSD" in col or "BOPD" in col or "MMscfd" in col})
          .applymap(lambda v: "color: #27AE60" if isinstance(v, (int, float)) and v > 0
                    else ("color: #E74C3C" if isinstance(v, (int, float)) and v < 0 else ""),
                    subset=["Cash Flow Net (MUSD)", "EBIT (MUSD)", "Cash Flow Cumulé (MUSD)"])
          .set_properties(**{"background-color": "#1A2332", "color": "#ECF0F1"}),
        use_container_width=True,
        height=350,
    )

    # ── Break-even Price ────────────────────────────────────────────────────
    st.subheader("⚖️ Prix de Break-even")
    prix_range = np.linspace(10, 150, 50)
    npv_range  = [
        calculer_npv(
            generer_cash_flows(p, prix_gaz, prod_huile, prod_gaz, capex_total,
                               opex_boe, royalties, impot, duree, decline, schedule
                               )["Cash Flow Net (MUSD)"].tolist(),
            wacc / 100,
        )
        for p in prix_range
    ]
    df_be = pd.DataFrame({"Prix Baril (USD)": prix_range, "NPV (MUSD)": npv_range})
    breakeven_price = None
    for i in range(len(npv_range) - 1):
        if npv_range[i] < 0 < npv_range[i + 1] or npv_range[i] > 0 > npv_range[i + 1]:
            breakeven_price = prix_range[i] + (prix_range[i+1]-prix_range[i]) * (
                -npv_range[i] / (npv_range[i+1] - npv_range[i]))
            break

    fig_be = go.Figure()
    fig_be.add_trace(go.Scatter(
        x=df_be["Prix Baril (USD)"], y=df_be["NPV (MUSD)"],
        line=dict(color=COLORS["accent"], width=3), fill="tozeroy",
        fillcolor="rgba(243,156,18,0.15)", name="NPV",
    ))
    fig_be.add_hline(y=0, line_dash="dash", line_color="white")
    if breakeven_price:
        fig_be.add_vline(x=breakeven_price, line_dash="dot",
                         line_color=COLORS["success"],
                         annotation_text=f"Break-even: {breakeven_price:.1f} $/bbl",
                         annotation_font_color=COLORS["success"])
    fig_be.add_vline(x=prix_baril, line_dash="solid", line_color=COLORS["primary"],
                     annotation_text=f"Prix actuel: {prix_baril} $/bbl",
                     annotation_font_color=COLORS["text_light"])
    fig_be.update_layout(
        height=320, template="plotly_dark",
        paper_bgcolor=COLORS["bg_card"],
        plot_bgcolor=COLORS["bg_card"],
        font=dict(color=COLORS["text_light"]),
        title="NPV en fonction du Prix du Baril",
        xaxis_title="Prix Baril (USD/bbl)",
        yaxis_title="NPV (MUSD)",
        margin=dict(t=50, b=20, l=10, r=10),
    )
    st.plotly_chart(fig_be, use_container_width=True)

    if breakeven_price:
        delta = prix_baril - breakeven_price
        upside = "▲ au-dessus" if delta > 0 else "▼ en-dessous"
        color = "🟢" if delta > 0 else "🔴"
        st.info(f"{color} Prix de break-even : **{breakeven_price:.1f} USD/bbl** — "
                f"Prix actuel {upside} du break-even de **{abs(delta):.1f} USD/bbl**")


# ── Point d'entrée standalone ────────────────────────────────────────────────
if __name__ == "__main__":
    render_finances_page()
