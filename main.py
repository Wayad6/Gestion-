# main.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta, datetime

import db
import utils

st.set_page_config(page_title="Gestionnaire Ventes & Stocks", layout="wide")
st.title("Gestionnaire de ventes & stocks — dh")

# Init DB
db.init_db()
LOW_STOCK_THRESHOLD = 5  # seuil fixe

# helpers
def rows_to_df(rows):
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame([dict(r) for r in rows])

# Sidebar navigation
page = st.sidebar.radio("Navigation", ["Tableau de bord", "Produits", "Ventes", "Achats", "Dépenses"])

# ---------- PRODUITS ----------
if page == "Produits":
    st.header("📦 Produits")
    col1, col2 = st.columns([2,1])
    with col1:
        st.subheader("Ajouter / Mettre à jour un produit")
        nom = st.text_input("Nom du produit")
        categorie = st.text_input("Catégorie (optionnel)")
        stock = st.number_input("Stock à ajouter (unités)", min_value=0, value=0, step=1)
        prix_achat = st.number_input("Prix d'achat unitaire (dh)", min_value=0.0, value=0.0, format="%.2f")
        prix_vente = st.number_input("Prix de vente unitaire (dh)", min_value=0.0, value=0.0, format="%.2f")
        if st.button("Enregistrer produit"):
            if not nom.strip():
                st.error("Le nom du produit est requis.")
            else:
                db.add_or_update_produit(nom.strip(), categorie.strip(), int(stock), float(prix_achat), float(prix_vente))
                st.success(f"Produit '{nom}' enregistré.")
                
                st.rerun()
    with col2:
        st.subheader("Catalogue")
        prods = db.get_produits()
        dfp = rows_to_df(prods)
        if dfp.empty:
            st.info("Aucun produit enregistré.")
        else:
            dfp["alerte_stock"] = dfp["stock"] <= LOW_STOCK_THRESHOLD
            st.dataframe(dfp[["id","nom","categorie","stock","prix_achat","prix_vente","total_vendu","total_revenu","alerte_stock"]], height=420)

        st.markdown("**Actions rapides**")
        if not prods:
            st.info("Aucun produit pour actions rapides.")
        else:
            prod_ids = [p["id"] for p in prods]
            sel = st.selectbox("Sélectionner produit (id)", options=prod_ids, format_func=lambda x: f"{x} — {db.get_produit_by_id(x)['nom']}")
            if st.button("Supprimer le produit"):
                if st.confirm(f"Supprimer le produit id={sel} ?"):
                    db.delete_produit(sel)
                    st.success("Produit supprimé.")
                    st.rerun()

# ---------- VENTES ----------
elif page == "Ventes":
    st.header("💰 Enregistrer une vente")
    prods = db.get_produits()
    if not prods:
        st.info("Pas de produit disponible, ajoutez d'abord.")
    else:
        prod_map = {p["nom"]: p["id"] for p in prods}
        choix = st.selectbox("Produit", list(prod_map.keys()))
        qte = st.number_input("Quantité vendue", min_value=1, value=1, step=1)
        prix = st.number_input("Prix unitaire (dh)", min_value=0.0, value=0.0, format="%.2f")
        date_input = st.date_input("Date de vente", value=date.today())
        if st.button("Ajouter la vente"):
            pid = prod_map[choix]
            db.add_vente(pid, int(qte), float(prix), date_input.strftime("%Y-%m-%d"))
            st.success(f"Vente : {qte} × {choix} enregistrée.")
            st.rerun()
    st.markdown("---")
    st.subheader("Ventes récentes")
    ventes = db.get_ventes(limit=200)
    st.dataframe(rows_to_df(ventes))

# ---------- ACHATS ----------
elif page == "Achats":
    st.header("📥 Enregistrer un achat / approvisionnement")
    prods = db.get_produits()
    if not prods:
        st.info("Pas de produit disponible, ajoutez d'abord.")
    else:
        prod_map = {p["nom"]: p["id"] for p in prods}
        choix = st.selectbox("Produit", list(prod_map.keys()))
        qte = st.number_input("Quantité achetée", min_value=1, value=1, step=1)
        prix = st.number_input("Prix d'achat unitaire (dh)", min_value=0.0, value=0.0, format="%.2f")
        date_input = st.date_input("Date d'achat", value=date.today())
        if st.button("Ajouter l'achat"):
            pid = prod_map[choix]
            db.add_achat(pid, int(qte), float(prix), date_input.strftime("%Y-%m-%d"))
            st.success(f"Achat : {qte} × {choix} ajouté.")
            st.rerun()
    st.markdown("---")
    st.subheader("Achats récents")
    achats = db.get_achats(limit=200)
    st.dataframe(rows_to_df(achats))

# ---------- DEPENSES ----------
elif page == "Dépenses":
    st.header("🚚 Dépenses")
    typ = st.selectbox("Type", ["transport", "livraison", "autre"])
    desc = st.text_input("Description (optionnel)")
    montant = st.number_input("Montant (dh)", min_value=0.0, value=0.0, format="%.2f")
    date_input = st.date_input("Date dépense", value=date.today())
    if st.button("Ajouter dépense"):
        db.add_depense(typ, float(montant), desc, date_input.strftime("%Y-%m-%d"))
        st.success("Dépense ajoutée.")
        st.rerun()
    st.markdown("---")
    st.subheader("Dépenses récentes")
    deps = db.get_depenses(limit=200)
    st.dataframe(rows_to_df(deps))

# ---------- TABLEAU DE BORD ----------
elif page == "Tableau de bord":
    st.header("📊 Tableau de bord")
    view = st.radio("Période", ["Jour", "Semaine", "Mois", "Personnalisée"], horizontal=True)
    today = date.today()
    if view == "Jour":
        d = st.date_input("Date", value=today)
        from_date = to_date = d
    elif view == "Semaine":
        start_of_week = today - timedelta(days=today.weekday())
        from_date = st.date_input("Début semaine", value=start_of_week)
        to_date = st.date_input("Fin semaine", value=start_of_week + timedelta(days=6))
    elif view == "Mois":
        first = today.replace(day=1)
        from_date = st.date_input("Début mois", value=first)
        # dernier jour du mois
        next_month = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
        last = next_month - timedelta(days=1)
        to_date = st.date_input("Fin mois", value=last)
    else:
        from_date = st.date_input("De", value=today - timedelta(days=7))
        to_date = st.date_input("À", value=today)

    if from_date > to_date:
        st.error("La date de début doit être inférieure ou égale à la date de fin.")
    else:
        rpt = utils.compute_report(from_date.strftime("%Y-%m-%d"), to_date.strftime("%Y-%m-%d"))
        c1, c2, c3 = st.columns(3)
        c1.metric("📈 CA", f"{rpt['ca']:.2f} dh")
        c2.metric("📉 Coût achats", f"{rpt['cout_achat']:.2f} dh")
        c3.metric("💸 Dépenses", f"{rpt['depenses']:.2f} dh")
        st.metric("🟢 Bénéfice net", f"{rpt['profit']:.2f} dh")

        st.subheader("Top produits (par quantité vendue)")
        df_top = pd.DataFrame(rpt["top"])
        if df_top.empty:
            st.info("Aucune vente dans la période.")
        else:
            st.dataframe(df_top.head(10))

        st.subheader("CA par jour")
        df_ca = pd.DataFrame(rpt["ca_by_day"])
        if not df_ca.empty:
            fig = px.bar(df_ca, x="date", y="ca", labels={"ca": "CA (dh)", "date": "Date"})
            st.plotly_chart(fig, use_container_width=True)

        st.subheader(f"Alerte stock faible (≤ {LOW_STOCK_THRESHOLD} unités)")
        low = db.get_produits_stock_below(LOW_STOCK_THRESHOLD)
        st.dataframe(rows_to_df(low))