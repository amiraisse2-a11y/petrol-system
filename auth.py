# auth.py — Authentification PETROCI PRO
# Login par compagnie avec Supabase Auth

import streamlit as st

# ─────────────────────────────────────────
# UTILISATEURS PAR DÉFAUT (fallback sans Supabase)
# En production → utiliser Supabase Auth
# ─────────────────────────────────────────
UTILISATEURS_DEMO = {
    "admin@petroci.ci": {
        "mdp":      "petroci2026",
        "nom":      "Administrateur PETROCI",
        "role":     "admin",
        "compagnie":"PETROCI",
        "acces":    ["Baleine","Sankofa","Foxtrot",
                     "Baobab","Lion","Panthere"]
    },
    "eni@baleine.ci": {
        "mdp":      "baleine2026",
        "nom":      "Ingenieur ENI",
        "role":     "operateur",
        "compagnie":"ENI",
        "acces":    ["Baleine"]
    },
    "total@sankofa.ci": {
        "mdp":      "sankofa2026",
        "nom":      "Ingenieur TotalEnergies",
        "role":     "operateur",
        "compagnie":"TotalEnergies",
        "acces":    ["Sankofa","Foxtrot","Lion","Panthere"]
    },
    "cnr@baobab.ci": {
        "mdp":      "baobab2026",
        "nom":      "Ingenieur CNR",
        "role":     "operateur",
        "compagnie":"CNR International",
        "acces":    ["Baobab"]
    },
    "demo@petroci.ci": {
        "mdp":      "demo2026",
        "nom":      "Utilisateur Demo",
        "role":     "viewer",
        "compagnie":"Demo",
        "acces":    ["Baleine","Sankofa"]
    },
}

def verifier_login(email, mdp):
    """Vérifie les credentials et retourne l'utilisateur"""
    email = email.strip().lower()
    user  = UTILISATEURS_DEMO.get(email)
    if user and user["mdp"] == mdp:
        return {
            "email":    email,
            "nom":      user["nom"],
            "role":     user["role"],
            "compagnie":user["compagnie"],
            "acces":    user["acces"],
        }
    return None

def afficher_page_login():
    """Affiche la page de connexion"""
    st.markdown("""
    <div style="
        max-width: 420px;
        margin: 40px auto;
        background: white;
        border-radius: 16px;
        padding: 40px;
        box-shadow: 0 8px 30px rgba(0,0,0,0.10);
        border-top: 5px solid #E07B00;
    ">
        <div style="text-align:center;margin-bottom:28px;">
            <div style="font-size:3rem;">🛢️</div>
            <div style="color:#E07B00;font-size:1.5rem;
                        font-weight:800;letter-spacing:3px;
                        margin:8px 0 4px 0;">PETROCI PRO</div>
            <div style="color:#AAA;font-size:0.78rem;
                        letter-spacing:2px;">
                SYSTEME DE GESTION DE PRODUCTION
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        st.markdown("### Connexion")
        email = st.text_input(
            "Email professionnel",
            placeholder="votre.nom@compagnie.ci"
        )
        mdp = st.text_input(
            "Mot de passe",
            type="password",
            placeholder="••••••••"
        )
        col1, col2 = st.columns([2, 1])
        with col1:
            connecter = st.form_submit_button(
                "Se connecter",
                use_container_width=True,
                type="primary"
            )
        with col2:
            st.form_submit_button(
                "Demo",
                use_container_width=True
            )

    if connecter:
        if not email or not mdp:
            st.error("Veuillez remplir tous les champs.")
            return False
        user = verifier_login(email, mdp)
        if user:
            st.session_state["connecte"]  = True
            st.session_state["user"]      = user
            st.session_state["email"]     = email
            st.success(f"Bienvenue {user['nom']} !")
            st.rerun()
        else:
            st.error("Email ou mot de passe incorrect.")
            return False

    # Compte demo
    st.markdown("---")
    st.markdown("""
    <div style="background:#FFF8F0;border-radius:8px;
                padding:12px 16px;font-size:0.82rem;color:#888;">
        <b>Comptes de demonstration :</b><br>
        admin@petroci.ci / petroci2026 (Acces complet)<br>
        eni@baleine.ci / baleine2026 (Champ Baleine)<br>
        demo@petroci.ci / demo2026 (Vue limitee)
    </div>
    """, unsafe_allow_html=True)
    return False

def verifier_session():
    """Vérifie si l'utilisateur est connecté"""
    return st.session_state.get("connecte", False)

def get_user():
    """Retourne l'utilisateur connecté"""
    return st.session_state.get("user", {})

def deconnecter():
    """Déconnecte l'utilisateur"""
    for key in ["connecte","user","email"]:
        st.session_state.pop(key, None)
    st.rerun()

def verifier_acces_champ(champ):
    """Vérifie si l'utilisateur a accès à un champ"""
    user = get_user()
    if user.get("role") == "admin":
        return True
    return champ in user.get("acces", [])
