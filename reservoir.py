"""
PETRO AFRICA — Module Réservoir
P/z Plot (champs gaz : Sankofa, Foxtrot)
IPR Vogel (puits huile : Baleine, Espoir, Baobab)
Calcul OGIP / OOIP simplifié.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# ─── Palette ─────────────────────────────────────────────────────────────────
COLORS = {
    "primary":  "#1B4F72",
    "accent":   "#F39C12",
    "success":  "#27AE60",
    "danger":   "#E74C3C",
    "gaz":      "#3498DB",   # bleu gaz
    "huile":    "#8B4513",   # brun pétrole
    "water":    "#1ABC9C",   # teal eau
    "bg_card":  "#1A2332",
    "text":     "#ECF0F1",
}


# ═══════════════════════════════════════════════════════════════════════════════
#  FACTEUR Z — ÉQUATION D'ÉTAT (Papay simplifié, Afrique de l'Ouest)
# ═══════════════════════════════════════════════════════════════════════════════

def facteur_z_papay(ppr: float, tpr: float) -> float:
    """
    Facteur de compressibilité z — corrélation Papay (1968).
    Valable pour gaz naturel sec, précision ±3%.
    ppr = P/Pc (pression pseudo-réduite)
    tpr = T/Tc (température pseudo-réduite)
    """
    return 1 - (3.52 * ppr) / (10 ** (0.9813 * tpr)) + (0.274 * ppr**2) / (10 ** (0.8157 * tpr))


def proprietes_pseudocritiques_gaz(gravite: float) -> tuple[float, float]:
    """
    Pression et température pseudo-critiques — corrélation Standing.
    gravite : gravité spécifique du gaz (air = 1.0), typique gaz CI ~ 0.65
    Retourne (Pc psia, Tc °R)
    """
    ppc = 677 + 15.0 * gravite - 37.5 * gravite**2
    tpc = 168 + 325 * gravite - 12.5 * gravite**2
    return ppc, tpc


# ═══════════════════════════════════════════════════════════════════════════════
#  P/z PLOT — CHAMPS GAZ
# ═══════════════════════════════════════════════════════════════════════════════

def calculer_pz_plot(
    pressions_psia: list[float],
    gp_mmscf: list[float],
    gravite_gaz: float = 0.65,
    temperature_f: float = 200.0,
) -> pd.DataFrame:
    """
    Calcule P/z en fonction de la production cumulée Gp.

    Paramètres
    ----------
    pressions_psia : liste de pressions mesurées (psia)
    gp_mmscf       : production cumulée correspondante (MMscf)
    gravite_gaz    : gravité spécifique du gaz
    temperature_f  : température réservoir (°F)

    Retourne un DataFrame avec P, z, P/z, Gp.
    """
    ppc, tpc = proprietes_pseudocritiques_gaz(gravite_gaz)
    T_R = temperature_f + 459.67   # °Rankine

    rows = []
    for p, gp in zip(pressions_psia, gp_mmscf):
        ppr = p / ppc
        tpr = T_R / tpc
        z   = facteur_z_papay(ppr, tpr)
        z   = max(z, 0.01)  # éviter division par zéro
        pz  = p / z
        rows.append({"P (psia)": p, "z": round(z, 4),
                      "P/z (psia)": round(pz, 1),
                      "Gp (MMscf)": gp})

    return pd.DataFrame(rows)


def ogip_depuis_pz(df_pz: pd.DataFrame) -> dict:
    """
    Régression linéaire P/z = Pi/zi × (1 - Gp/OGIP).
    Retourne OGIP (MMscf), Pi/zi, et qualité du fit.
    """
    x = df_pz["Gp (MMscf)"].values
    y = df_pz["P/z (psia)"].values

    if len(x) < 2:
        return {"ogip": None, "pizi": None, "r2": None}

    # Régression linéaire y = a + b*x
    coeffs = np.polyfit(x, y, 1)
    b, a = coeffs[0], coeffs[1]   # P/z = a + b*Gp

    # P/z = Pi/zi * (1 - Gp/OGIP) ⟹ OGIP = -Pi/zi / b
    pizi = a
    ogip = -pizi / b if b != 0 else None

    # R²
    y_pred = np.polyval(coeffs, x)
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot != 0 else 0

    return {
        "ogip":      round(ogip) if ogip else None,
        "pizi":      round(pizi, 1),
        "slope":     round(b, 4),
        "r2":        round(r2, 4),
        "coeffs":    coeffs,
        "ogip_bscf": round(ogip / 1000, 2) if ogip else None,
    }


def fig_pz_plot(df_pz: pd.DataFrame, ogip_result: dict, champ: str = "Champ gaz") -> go.Figure:
    """P/z Plot avec droite de régression et extrapolation jusqu'à P/z=0."""
    fig = go.Figure()

    # Points mesurés
    fig.add_trace(go.Scatter(
        x=df_pz["Gp (MMscf)"], y=df_pz["P/z (psia)"],
        mode="markers",
        marker=dict(size=10, color=COLORS["gaz"],
                    symbol="circle", line=dict(color="white", width=1.5)),
        name="P/z mesuré",
        text=[f"P={row['P (psia)']:.0f} psia<br>z={row['z']:.4f}"
              for _, row in df_pz.iterrows()],
        hovertemplate="%{text}<br>Gp=%{x:.0f} MMscf<br>P/z=%{y:.0f} psia<extra></extra>",
    ))

    # Droite de régression
    if ogip_result.get("ogip") and ogip_result.get("coeffs") is not None:
        ogip = ogip_result["ogip"]
        gp_ext = np.linspace(0, ogip * 1.05, 200)
        pz_ext = np.polyval(ogip_result["coeffs"], gp_ext)

        # Séparer partie observée (gp ≤ max mesuré) et extrapolée
        gp_max = df_pz["Gp (MMscf)"].max()
        mask_obs = gp_ext <= gp_max
        mask_ext = gp_ext > gp_max

        fig.add_trace(go.Scatter(
            x=gp_ext[mask_obs], y=pz_ext[mask_obs],
            mode="lines", line=dict(color=COLORS["accent"], width=2),
            name="Régression linéaire", showlegend=True,
        ))
        fig.add_trace(go.Scatter(
            x=gp_ext[mask_ext], y=np.maximum(pz_ext[mask_ext], 0),
            mode="lines", line=dict(color=COLORS["accent"], width=2, dash="dash"),
            name="Extrapolation → OGIP", showlegend=True,
        ))

        # Point OGIP
        fig.add_trace(go.Scatter(
            x=[ogip], y=[0],
            mode="markers+text",
            marker=dict(size=14, color=COLORS["danger"], symbol="x"),
            text=[f"OGIP = {ogip_result['ogip_bscf']} Bscf"],
            textposition="top right",
            name="OGIP estimé",
        ))

    fig.add_hline(y=0, line_dash="dash", line_color="#555555")
    fig.update_layout(
        height=430, template="plotly_dark",
        paper_bgcolor=COLORS["bg_card"],
        plot_bgcolor=COLORS["bg_card"],
        font=dict(color=COLORS["text"]),
        title=f"P/z Plot — {champ}",
        xaxis_title="Production Cumulée Gp (MMscf)",
        yaxis_title="P/z (psia)",
        legend=dict(x=0.01, y=0.99),
        margin=dict(t=50, b=30, l=10, r=10),
    )
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
#  IPR VOGEL — PUITS HUILE
# ═══════════════════════════════════════════════════════════════════════════════

def ipr_vogel(
    pwf: float,
    pr: float,
    qmax: float,
) -> float:
    """
    Équation IPR Vogel (1968) pour puits huile sous-saturé / saturé.
    q/qmax = 1 - 0.2*(Pwf/Pr) - 0.8*(Pwf/Pr)²

    Paramètres
    ----------
    pwf  : pression fond de puits (psia)
    pr   : pression réservoir (psia)
    qmax : débit maximum (AOF, Absolute Open Flow), BOPD

    Retourne débit (BOPD).
    """
    ratio = pwf / pr
    ratio = min(max(ratio, 0), 1)
    return qmax * (1 - 0.2 * ratio - 0.8 * ratio**2)


def qmax_depuis_point_test(
    q_test: float,
    pwf_test: float,
    pr: float,
) -> float:
    """
    Calcule qmax à partir d'un point test (q, Pwf).
    """
    ratio = pwf_test / pr
    ratio = min(max(ratio, 0), 1)
    denom = 1 - 0.2 * ratio - 0.8 * ratio**2
    return q_test / denom if denom > 0 else 0


def generer_courbe_ipr(pr: float, qmax: float, n_points: int = 50) -> pd.DataFrame:
    """Génère la courbe IPR complète (de Pr à 0)."""
    pwf_vals = np.linspace(0, pr, n_points)
    q_vals   = [ipr_vogel(pwf, pr, qmax) for pwf in pwf_vals]
    return pd.DataFrame({"Pwf (psia)": pwf_vals, "Débit (BOPD)": q_vals})


def point_fonctionnement(
    df_ipr: pd.DataFrame,
    wh_pressure: float,
    gradient_fluide: float = 0.35,   # psi/ft
    profondeur_ft: float  = 5000.0,
) -> tuple[float, float]:
    """
    Intersection IPR / VLP (Vertical Lift Performance) simplifiée.
    VLP : Pwf = Pwh + gradient × profondeur (approximation linéaire).

    Retourne (Pwf_op, q_op) au point de fonctionnement.
    """
    pwf_vlp = wh_pressure + gradient_fluide * profondeur_ft

    # Interpolation sur la courbe IPR
    idx = (df_ipr["Pwf (psia)"] - pwf_vlp).abs().idxmin()
    return (round(df_ipr.loc[idx, "Pwf (psia)"], 0),
            round(df_ipr.loc[idx, "Débit (BOPD)"], 0))


def fig_ipr(
    df_ipr: pd.DataFrame,
    pr: float,
    qmax: float,
    point_test: tuple = None,   # (q, Pwf)
    point_op: tuple   = None,   # (Pwf_op, q_op)
    puit_nom: str = "Puits",
) -> go.Figure:
    """Courbe IPR Vogel avec annotations."""
    fig = go.Figure()

    # Courbe IPR
    fig.add_trace(go.Scatter(
        x=df_ipr["Débit (BOPD)"], y=df_ipr["Pwf (psia)"],
        mode="lines",
        line=dict(color=COLORS["huile"], width=3),
        name="IPR Vogel",
        fill="tozerox",
        fillcolor="rgba(139,69,19,0.10)",
    ))

    # Point Pr (débit = 0)
    fig.add_trace(go.Scatter(
        x=[0], y=[pr],
        mode="markers+text",
        marker=dict(size=10, color=COLORS["primary"]),
        text=[f"Pr = {pr:.0f} psia"],
        textposition="middle right",
        name="Pression réservoir",
    ))

    # AOF (Pwf = 0)
    fig.add_trace(go.Scatter(
        x=[qmax], y=[0],
        mode="markers+text",
        marker=dict(size=10, color=COLORS["danger"]),
        text=[f"AOF = {qmax:.0f} BOPD"],
        textposition="top left",
        name="AOF (Débit max)",
    ))

    # Point test
    if point_test:
        fig.add_trace(go.Scatter(
            x=[point_test[0]], y=[point_test[1]],
            mode="markers",
            marker=dict(size=14, color=COLORS["accent"],
                        symbol="star", line=dict(color="white", width=1)),
            name=f"Point test ({point_test[0]:.0f} BOPD, {point_test[1]:.0f} psia)",
        ))

    # Point de fonctionnement
    if point_op:
        q_op, pwf_op = point_op[1], point_op[0]
        fig.add_trace(go.Scatter(
            x=[q_op], y=[pwf_op],
            mode="markers+text",
            marker=dict(size=14, color=COLORS["success"],
                        symbol="diamond", line=dict(color="white", width=1.5)),
            text=[f"  Q={q_op:.0f} BOPD<br>  Pwf={pwf_op:.0f} psia"],
            textposition="middle right",
            name="Point de fonctionnement",
        ))
        # Lignes de construction
        fig.add_shape(type="line",
                      x0=0, y0=pwf_op, x1=q_op, y1=pwf_op,
                      line=dict(color=COLORS["success"], dash="dot", width=1.5))
        fig.add_shape(type="line",
                      x0=q_op, y0=0, x1=q_op, y1=pwf_op,
                      line=dict(color=COLORS["success"], dash="dot", width=1.5))

    fig.update_layout(
        height=420, template="plotly_dark",
        paper_bgcolor=COLORS["bg_card"],
        plot_bgcolor=COLORS["bg_card"],
        font=dict(color=COLORS["text"]),
        title=f"IPR Vogel — {puit_nom}",
        xaxis_title="Débit (BOPD)",
        yaxis_title="Pression Fond de Puits, Pwf (psia)",
        legend=dict(x=0.5, y=0.99),
        margin=dict(t=50, b=30, l=10, r=10),
    )
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE STREAMLIT
# ═══════════════════════════════════════════════════════════════════════════════

def render_reservoir_page():
    """
    Appeler depuis dashboard.py :
        from reservoir import render_reservoir_page
        render_reservoir_page()
    """
    st.markdown("""
    <style>
    .res-card {
        background: #1A2332; border: 1px solid #2C3E50;
        border-radius: 10px; padding: 1rem 1.2rem; text-align: center;
    }
    .res-val { font-size: 1.7rem; font-weight: 700; margin: 0; }
    .res-lbl { font-size: 0.76rem; color: #95A5A6; margin: 0; }
    </style>
    """, unsafe_allow_html=True)

    st.title("🔬 Module Réservoir")
    st.caption("P/z Plot (champs gaz) · IPR Vogel (puits huile) · OGIP · AOF")

    tab_gaz, tab_huile = st.tabs(["⛽ P/z Plot — Champs Gaz", "🛢️ IPR Vogel — Puits Huile"])

    # ══════════════════════════════════════════════════════════════════════════
    #  ONGLET 1 : P/z Plot
    # ══════════════════════════════════════════════════════════════════════════
    with tab_gaz:
        st.subheader("P/z Plot — Estimation OGIP")
        st.caption("Champs gaz Côte d'Ivoire : Sankofa (ENI/PETROCI), Foxtrot (Foxtrot International)")

        col_params, col_data = st.columns([1, 2])

        with col_params:
            champ_gaz = st.selectbox("Champ gaz",
                                     ["Sankofa", "Foxtrot", "Nouveau champ"])
            gravite   = st.slider("Gravité spécifique gaz", 0.55, 0.80, 0.65, 0.01,
                                   help="Air = 1.0 | Gaz naturel CI : 0.60–0.70")
            temp_f    = st.number_input("Température réservoir (°F)", 100, 350, 200)

            st.markdown("---")
            st.markdown("**Points de mesure P/z (historique)**")
            st.caption("Entrez les données pression / production cumulée")

            # Données par défaut selon le champ
            DEFAULTS = {
                "Sankofa": {
                    "P":  [3800, 3650, 3480, 3300, 3100, 2900],
                    "Gp": [0, 50_000, 120_000, 210_000, 320_000, 450_000],
                },
                "Foxtrot": {
                    "P":  [2950, 2820, 2680, 2510, 2340],
                    "Gp": [0, 80_000, 180_000, 310_000, 460_000],
                },
                "Nouveau champ": {
                    "P":  [4500, 4200, 3900],
                    "Gp": [0, 30_000, 70_000],
                },
            }
            default = DEFAULTS.get(champ_gaz, DEFAULTS["Nouveau champ"])
            n_points_pz = st.slider("Nombre de points", 2, 10, len(default["P"]))

            pressions, gp_vals = [], []
            for i in range(n_points_pz):
                c1, c2 = st.columns(2)
                p_def = default["P"][i] if i < len(default["P"]) else 3000 - i * 200
                g_def = default["Gp"][i] if i < len(default["Gp"]) else i * 50_000
                with c1:
                    pressions.append(st.number_input(f"P{i+1} (psia)",
                                     100, 10_000, p_def, key=f"p_{i}"))
                with c2:
                    gp_vals.append(st.number_input(f"Gp{i+1} (MMscf)",
                                   0, 10_000_000, g_def, key=f"gp_{i}"))

        with col_data:
            df_pz = calculer_pz_plot(pressions, gp_vals, gravite, temp_f)
            ogip  = ogip_depuis_pz(df_pz)

            # KPIs
            c1, c2, c3 = st.columns(3)
            with c1:
                val = f"{ogip['ogip_bscf']} Bscf" if ogip['ogip_bscf'] else "N/A"
                st.markdown(f"""<div class="res-card">
                  <p class="res-val" style="color:#3498DB">{val}</p>
                  <p class="res-lbl">OGIP Estimé</p></div>""", unsafe_allow_html=True)
            with c2:
                val = f"{ogip['pizi']:.0f}" if ogip['pizi'] else "N/A"
                st.markdown(f"""<div class="res-card">
                  <p class="res-val" style="color:#F39C12">{val} psia</p>
                  <p class="res-lbl">Pi/zi (initial)</p></div>""", unsafe_allow_html=True)
            with c3:
                r2_val = f"{ogip['r2']:.4f}" if ogip['r2'] is not None else "N/A"
                color_r2 = "#27AE60" if ogip.get("r2", 0) and ogip["r2"] > 0.99 else "#F39C12"
                st.markdown(f"""<div class="res-card">
                  <p class="res-val" style="color:{color_r2}">{r2_val}</p>
                  <p class="res-lbl">R² Régression</p></div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.plotly_chart(fig_pz_plot(df_pz, ogip, champ_gaz),
                            use_container_width=True)

            # Tableau P/z
            st.dataframe(
                df_pz.style
                     .format({"z": "{:.4f}", "P/z (psia)": "{:.1f}",
                               "Gp (MMscf)": "{:,.0f}"})
                     .set_properties(**{"background-color": "#1A2332",
                                        "color": "#ECF0F1"}),
                use_container_width=True,
                hide_index=True,
            )

        # Pct recovery
        if ogip["ogip"] and max(gp_vals) > 0:
            rf = max(gp_vals) / ogip["ogip"] * 100
            st.info(
                f"📊 **Facteur de récupération actuel** : {rf:.1f}%  "
                f"({max(gp_vals):,.0f} / {ogip['ogip']:,.0f} MMscf)"
            )

    # ══════════════════════════════════════════════════════════════════════════
    #  ONGLET 2 : IPR Vogel
    # ══════════════════════════════════════════════════════════════════════════
    with tab_huile:
        st.subheader("IPR Vogel — Puits Huile")
        st.caption("Deliverability · AOF · Point de fonctionnement — Champs Baleine, Espoir, Baobab")

        col_ipr_params, col_ipr_graph = st.columns([1, 2])

        with col_ipr_params:
            champ_h = st.selectbox("Champ huile",
                                    ["Baleine", "Espoir", "Baobab", "Autre"])
            puit_id = st.text_input("Identifiant puits", "PA-01")
            pr_val  = st.number_input("Pression réservoir Pr (psia)",
                                       500, 10_000, 3_500)

            st.markdown("---")
            st.markdown("**Données de test de puits**")
            q_test   = st.number_input("Débit test (BOPD)", 10, 20_000, 2_000)
            pwf_test = st.number_input("Pwf test (psia)", 100,
                                        pr_val - 10, min(1_800, pr_val - 100))
            qmax_calc = qmax_depuis_point_test(q_test, pwf_test, pr_val)

            st.markdown("---")
            st.markdown("**Point de fonctionnement (VLP)**")
            use_vlp   = st.checkbox("Calculer point de fonctionnement", True)
            wh_press  = st.number_input("Pression tête de puits (psia)", 50, 2_000, 250,
                                         disabled=not use_vlp)
            gradient  = st.number_input("Gradient fluide (psi/ft)", 0.10, 0.60, 0.35, 0.01,
                                         disabled=not use_vlp,
                                         help="Eau: 0.433 | Huile: 0.30–0.40 | Émulsion: 0.35")
            depth_ft  = st.number_input("Profondeur (ft)", 1000, 20_000, 6_000,
                                         disabled=not use_vlp)

        with col_ipr_graph:
            df_ipr_curve = generer_courbe_ipr(pr_val, qmax_calc)
            pt_op = None
            if use_vlp:
                pt_op = point_fonctionnement(df_ipr_curve, wh_press, gradient, depth_ft)

            # KPIs
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"""<div class="res-card">
                  <p class="res-val" style="color:#8B4513">{qmax_calc:,.0f}</p>
                  <p class="res-lbl">AOF (BOPD)</p></div>""", unsafe_allow_html=True)
            with c2:
                q_op_val = pt_op[1] if pt_op else "—"
                st.markdown(f"""<div class="res-card">
                  <p class="res-val" style="color:#27AE60">{q_op_val}</p>
                  <p class="res-lbl">Débit optimal (BOPD)</p></div>""",
                            unsafe_allow_html=True)
            with c3:
                pwf_op_val = pt_op[0] if pt_op else "—"
                st.markdown(f"""<div class="res-card">
                  <p class="res-val" style="color:#F39C12">{pwf_op_val}</p>
                  <p class="res-lbl">Pwf optimal (psia)</p></div>""",
                            unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.plotly_chart(
                fig_ipr(df_ipr_curve, pr_val, qmax_calc,
                        point_test=(q_test, pwf_test),
                        point_op=pt_op,
                        puit_nom=f"{champ_h} — {puit_id}"),
                use_container_width=True,
            )

            # Analyse sensibilité Pr déclinant
            st.subheader("📉 IPR — Sensibilité à la Déplétion")
            fractions_pr = [1.0, 0.85, 0.70, 0.55]
            fig_depletion = go.Figure()
            for frac in fractions_pr:
                pr_sim = pr_val * frac
                qmax_sim = qmax_depuis_point_test(q_test, min(pwf_test, pr_sim - 100), pr_sim)
                df_sim = generer_courbe_ipr(pr_sim, qmax_sim)
                fig_depletion.add_trace(go.Scatter(
                    x=df_sim["Débit (BOPD)"], y=df_sim["Pwf (psia)"],
                    mode="lines",
                    name=f"Pr = {pr_sim:.0f} psia ({frac*100:.0f}%)",
                    line=dict(width=2),
                ))
            fig_depletion.update_layout(
                height=320, template="plotly_dark",
                paper_bgcolor=COLORS["bg_card"],
                plot_bgcolor=COLORS["bg_card"],
                font=dict(color=COLORS["text"]),
                title=f"IPR Vogel — Évolution avec déplétion ({champ_h})",
                xaxis_title="Débit (BOPD)",
                yaxis_title="Pwf (psia)",
                legend=dict(x=0.5, y=0.99),
                margin=dict(t=50, b=30, l=10, r=10),
            )
            st.plotly_chart(fig_depletion, use_container_width=True)

        st.markdown("---")
        st.caption(
            "**Références** : Vogel J.V. (1968) — *Inflow Performance Relationships for "
            "Solution-Gas Drive Wells*, JPT. | Papay J. (1968) — corrélation z. | "
            "Standing M.B. (1977) — propriétés pseudo-critiques gaz."
        )


if __name__ == "__main__":
    render_reservoir_page()
