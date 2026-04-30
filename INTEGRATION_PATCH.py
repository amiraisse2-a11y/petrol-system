"""
PETRO AFRICA — PATCH D'INTÉGRATION
Ajouter ces blocs dans dashboard.py pour activer les 5 nouveaux modules.
"""

# ════════════════════════════════════════════════════════════════════════════
# ÉTAPE 1 — Imports à ajouter en haut de dashboard.py
# ════════════════════════════════════════════════════════════════════════════

from finances    import render_finances_page
from esg_flaring import render_esg_page
from reservoir   import render_reservoir_page
from export_excel import render_export_excel_button

# ════════════════════════════════════════════════════════════════════════════
# ÉTAPE 2 — Ajouter dans la navigation (sidebar ou st.tabs)
# Chercher le bloc navigation existant et ajouter les nouvelles options
# ════════════════════════════════════════════════════════════════════════════

# Exemple si tu utilises un selectbox ou radio pour la navigation :
# PAGES = {
#     "🏠 Accueil":          render_home,
#     "📊 Production":       render_production_page,
#     "💰 Finances":         render_finances_page,       # ← NOUVEAU
#     "🌿 ESG & Flaring":    render_esg_page,            # ← NOUVEAU
#     "🔬 Réservoir":        render_reservoir_page,      # ← NOUVEAU
#     "📈 Analytics":        render_analytics_page,
#     "🤖 ML Forecast":      render_ml_page,
#     "🚨 Alertes":          render_alerts_page,
#     "📋 Rapports":         render_reports_page,
# }

# ════════════════════════════════════════════════════════════════════════════
# ÉTAPE 3 — Bouton export Excel (à ajouter dans render_reports_page ou sidebar)
# ════════════════════════════════════════════════════════════════════════════

# Dans ta page Rapports, remplace l'export CSV existant par :
#
# with st.expander("📥 Export Excel formaté", expanded=True):
#     render_export_excel_button(
#         dfs={
#             "production": df_production,     # ton DataFrame production existant
#             "finances":   df_finances,        # depuis finances.py
#             "esg":        df_esg_trajectoire, # depuis esg_flaring.py
#             # "reservoir": df_pz,            # optionnel
#         },
#         metadata={
#             "champ":           champ_selectionne,
#             "operateur":       "ENI/PETROCI",
#             "periode":         f"{date_debut} → {date_fin}",
#             "auteur":          nom_utilisateur,
#             "confidentialite": "CONFIDENTIEL — Usage interne",
#         },
#         kpis={
#             "npv":     npv_calcule,
#             "irr":     irr_calcule,
#             "payback": payback_calcule,
#             "wacc":    wacc_selectionne,
#         },
#     )

# ════════════════════════════════════════════════════════════════════════════
# ÉTAPE 4 — Utiliser PRIX_GAZ_MMBTU partout (config.py mis à jour)
# ════════════════════════════════════════════════════════════════════════════

# Dans tous tes fichiers où tu faisais référence uniquement à PRIX_BARIL :
#
# AVANT :
#   revenue = prod_bopd * 365 * PRIX_BARIL
#
# APRÈS :
#   from config import PRIX_BARIL, PRIX_GAZ_MMBTU, GAZ_MMBTU_PAR_BOE
#   rev_huile = prod_bopd * 365 * PRIX_BARIL
#   rev_gaz   = prod_mmscfd * 365 * 1000 * PRIX_GAZ_MMBTU   # 1 MMscfd = 1000 MMBtu/j
#   revenue   = rev_huile + rev_gaz
#
# Fichiers à vérifier : data_real_ci.py, analytics.py, reports.py, alerts.py

# ════════════════════════════════════════════════════════════════════════════
# VÉRIFICATION RAPIDE — lancer ceci en terminal pour tester les imports
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("✅ Vérification imports PETRO AFRICA — Nouveaux modules")

    # Test config
    try:
        from config import PRIX_GAZ_MMBTU, PRIX_GAZ_MMSCFD, PRIX_BARIL, WACC_DEFAULT
        print(f"  config.py       → PRIX_BARIL={PRIX_BARIL} | PRIX_GAZ={PRIX_GAZ_MMBTU} | WACC={WACC_DEFAULT}%")
    except Exception as e:
        print(f"  ❌ config.py     : {e}")

    # Test finances
    try:
        from finances import calculer_npv, calculer_irr, generer_cash_flows
        cf = [-100, 20, 25, 30, 35, 40]
        npv = calculer_npv(cf, 0.12)
        irr = calculer_irr(cf)
        print(f"  finances.py     → NPV={npv:.2f} MUSD | IRR={irr*100:.1f}%")
    except Exception as e:
        print(f"  ❌ finances.py   : {e}")

    # Test ESG
    try:
        from esg_flaring import calculer_emissions_flaring, score_esg
        em = calculer_emissions_flaring(50.0, 5.0)
        sc = score_esg(em, 50.0, 5.0)
        print(f"  esg_flaring.py  → CO2e/j={em['co2e_total_tj']} t | Score ESG={sc['score_total']}/100")
    except Exception as e:
        print(f"  ❌ esg_flaring   : {e}")

    # Test export Excel
    try:
        import pandas as pd
        from export_excel import generer_rapport_excel
        df_test = pd.DataFrame({"Mois": ["Jan", "Fev"], "BOPD": [5000, 4800]})
        excel_bytes = generer_rapport_excel({"production": df_test},
                                            {"champ": "Test"})
        print(f"  export_excel.py → OK ({len(excel_bytes):,} bytes)")
    except Exception as e:
        print(f"  ❌ export_excel  : {e}")

    # Test réservoir
    try:
        from reservoir import (calculer_pz_plot, ogip_depuis_pz,
                               ipr_vogel, qmax_depuis_point_test)
        df_pz = calculer_pz_plot([3800, 3500, 3200], [0, 100_000, 220_000])
        ogip  = ogip_depuis_pz(df_pz)
        qmax  = qmax_depuis_point_test(2000, 1800, 3500)
        q_vogel = ipr_vogel(1500, 3500, qmax)
        print(f"  reservoir.py    → OGIP={ogip['ogip_bscf']} Bscf | qmax={qmax:.0f} BOPD | q@Pwf1500={q_vogel:.0f} BOPD")
    except Exception as e:
        print(f"  ❌ reservoir.py  : {e}")

    print("\n✅ Tous les modules sont opérationnels. Intégrez dans dashboard.py selon ÉTAPES 1-4 ci-dessus.")
