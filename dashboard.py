# dashboard.py
# Interface principale PETROCI — Version Cloud (Streamlit)

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta

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
from config import PRIX_BARIL, TAUX

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
# INITIALISATION (1 seule fois)
# ════════════════════════════════════════════
@st.cache_resource
def setup():
    initialiser_sqlite()
    peupler_puits()
    generer_production_historique(365)
    return True

setup()

# ════════════════════════════════════════════
# SIDEBAR — NAVIGATION
# ════════════════════════════════════════════
st.sidebar.title("🛢️ PETROCI")
st.sidebar.caption("Système de Production Offshore CI")

page = st.sidebar.radio("Navigation", [
    "🏠 Tableau de Bord",
    "🛢️ Puits & Champs",
    "📊 Analyse Production",
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

    # KPIs
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

    # Graphiques
    df_hist = historique_champs(nb_jours)
    df_prod = lire_production(
        date_debut=str(date_debut), date_fin=str(date_fin)
    )

    if not df_hist.empty:
        cg, cd = st.columns(2)

        with cg:
            df_total = (
                df_hist.groupby("date")["production_huile_bbl"]
                .sum().reset_index()
            )
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

    # Carte des puits
    st.subheader("🗺️ Carte des Puits Offshore CI")
    df_puits = lire_puits()
    if not df_puits.empty and "latitude" in df_puits.columns:
        couleurs = {"Actif": "#00CC96", "Alerte": "#FFA500", "Critique": "#FF0000"}
        fig_map = px.scatter_mapbox(
            df_puits,
            lat="latitude", lon="longitude",
            color="statut",
            hover_name="nom_puits",
            hover_data=["champ", "operateur", "statut"],
            color_discrete_map=couleurs,
            title="Localisation des puits offshore Côte d'Ivoire",
            zoom=7,
            center={"lat": 4.3, "lon": -3.7}
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

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Puits", len(df))
    c2.metric("Actifs",    int((df["statut"] == "Actif").sum())    if not df.empty else 0)
    c3.metric("Alertes",   int((df["statut"] == "Alerte").sum())   if not df.empty else 0)
    c4.metric("Critiques", int((df["statut"] == "Critique").sum()) if not df.empty else 0)

    st.subheader("Liste des Puits")

    def style_statut(val):
        if val == "Critique": return "background-color:#FF000033;color:red"
        if val == "Alerte":   return "background-color:#FFA50033;color:orange"
        return "background-color:#00CC9633;color:green"

    cols_afficher = [c for c in
        ["nom_puits","champ","operateur","type_puits","statut","date_forage"]
        if c in df.columns]

    st.dataframe(
        df[cols_afficher].style.applymap(style_statut, subset=["statut"])
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
        c1, c2, c3 = st.columns(3)
        c1.metric("Production Période",
                  f"{rapport['Production_Totale'].sum():,.0f} bbl")
        c2.metric("Revenus Totaux",
                  f"${rapport['Revenu_USD'].sum():,.0f}")
        c3.metric("Revenus FCFA",
                  f"{rapport['Revenu_FCFA'].sum()/1e9:.2f} Mds FCFA")

        st.divider()
        st.subheader("Performance par Champ")

        aff = rapport.copy()
        aff["WaterCut_Moyen"]     = aff["WaterCut_Moyen"].map("{:.1%}".format)
        aff["Production_Totale"]  = aff["Production_Totale"].map("{:,.0f}".format)
        aff["Revenu_USD"]         = aff["Revenu_USD"].map("${:,.0f}".format)
        aff["Revenu_FCFA"]        = aff["Revenu_FCFA"].map("{:,.0f}".format)
        st.dataframe(aff, use_container_width=True, hide_index=True)

        fig = go.Figure(go.Bar(
            x=rapport["champ"],
            y=rapport["Revenu_FCFA"] / 1e6,
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
# PAGE 4 — ALERTES
# ════════════════════════════════════════════
elif page == "⚠️ Alertes":

    st.title("⚠️ Système d'Alertes")

    if st.button("🔍 Vérifier toutes les alertes maintenant"):
        nb = len(verifier_alertes())
        st.success(f"✅ Vérification terminée — {nb} alertes générées")

    df_al = lire_alertes(resolues=False)

    if not df_al.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total alertes actives", len(df_al))
        c2.metric("Critiques", int((df_al["niveau"]=="CRITIQUE").sum()))
        c3.metric("Alertes",   int((df_al["niveau"]=="ALERTE").sum()))
        st.divider()

        for _, a in df_al[df_al["niveau"]=="CRITIQUE"].iterrows():
            st.error(f"🔴 **CRITIQUE** | {a['puits']} ({a['champ']}) | "
                     f"{a['type_alerte']} | {a['message']}")

        for _, a in df_al[df_al["niveau"]=="ALERTE"].iterrows():
            st.warning(f"⚠️ **ALERTE** | {a['puits']} ({a['champ']}) | "
                       f"{a['type_alerte']} | {a['message']}")
    else:
        st.success("✅ Aucune alerte active — Tous les puits sont OK")

# ════════════════════════════════════════════
# PAGE 5 — DÉCLIN & PRÉVISIONS
# ════════════════════════════════════════════
elif page == "📈 Déclin & Prévisions":

    st.title("📈 Analyse de Déclin & Prévisions")

    from config import PROFILS_PUITS
    puits_liste = list(PROFILS_PUITS.keys())
    puits_choisi = st.selectbox("Choisir un puits", puits_liste)

    declin = calculer_declin(puits_choisi, nb_jours)

    if declin:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Production Début", f"{declin['production_debut']:,.0f} bbl/j")
        c2.metric("Production Actuelle", f"{declin['production_actuelle']:,.0f} bbl/j")
        c3.metric("Déclin Total",   f"{declin['declin_total_pct']:.1f}%",
                  delta_color="inverse")
        c4.metric("Déclin Mensuel", f"{declin['declin_mensuel_pct']:.1f}%/mois",
                  delta_color="inverse")

    df_p = lire_production(
        date_debut=str(date_debut), date_fin=str(date_fin),
        puits=puits_choisi
    )

    if not df_p.empty:
        df_p = df_p.sort_values("date")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_p["date"], y=df_p["production_huile_bbl"],
            name="Production Huile", mode="lines",
            line=dict(color="#00CC96", width=2)
        ))
        fig.add_trace(go.Scatter(
            x=df_p["date"],
            y=df_p["water_cut"].astype(float) * df_p["production_huile_bbl"].astype(float).max(),
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
        st.info("Aucune donnée pour ce puits sur la période sélectionnée.")

# ════════════════════════════════════════════
# PAGE 6 — RAPPORTS
# ════════════════════════════════════════════
elif page == "📋 Rapports":

    st.title("📋 Génération de Rapports")

    type_r = st.selectbox("Type de rapport", [
        "Rapport Production par Champ",
        "Rapport Performance Opérateurs",
        "Rapport Alertes Actives",
    ])

    if st.button("📄 Générer le Rapport"):
        with st.spinner("Génération en cours..."):
            rapport = production_par_champ(nb_jours)

            st.subheader(f"📊 {type_r}")
            st.caption(f"Période : {date_debut} → {date_fin} | "
                       f"Généré le : {date.today().strftime('%d/%m/%Y')}")

            if not rapport.empty:
                prod_tot = rapport["Production_Totale"].sum()
                rev_tot  = rapport["Revenu_USD"].sum()
                st.info(
                    f"**Résumé exécutif :** Production totale {prod_tot:,.0f} bbl "
                    f"sur {nb_jours} jours | "
                    f"Revenus : ${rev_tot:,.0f} USD | "
                    f"{rev_tot * TAUX / 1e9:.2f} Mds FCFA"
                )

                if type_r == "Rapport Performance Opérateurs":
                    df_op = lire_production(
                        date_debut=str(date_debut), date_fin=str(date_fin)
                    )
                    if not df_op.empty and "champ" in df_op.columns:
                        from config import CHAMPS
                        df_op["operateur"] = df_op["champ"].map(
                            {k: v["operateur"] for k, v in CHAMPS.items()}
                        )
                        grp = df_op.groupby("operateur").agg(
                            Production=("production_huile_bbl","sum"),
                            WC_Moyen  =("water_cut","mean"),
                            Nb_Puits  =("puits","nunique")
                        ).reset_index()
                        st.dataframe(grp, use_container_width=True, hide_index=True)

                elif type_r == "Rapport Alertes Actives":
                    df_al = lire_alertes(resolues=False)
                    if not df_al.empty:
                        st.dataframe(df_al, use_container_width=True, hide_index=True)
                    else:
                        st.success("Aucune alerte active.")
                else:
                    st.dataframe(rapport, use_container_width=True, hide_index=True)

                fig = px.bar(
                    rapport, x="champ", y="Production_Totale",
                    color="champ", title="Production par champ",
                    text="Production_Totale"
                )
                fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
                st.plotly_chart(fig, use_container_width=True)

                # Export CSV
                csv = rapport.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇️ Télécharger CSV",
                    data=csv,
                    file_name=f"rapport_petroci_{date.today()}.csv",
                    mime="text/csv"
                )

                st.success("✅ Rapport généré avec succès")
            else:
                st.warning("Aucune donnée disponible pour cette période.")
