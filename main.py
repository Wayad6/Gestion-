
# app.py
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from fpdf import FPDF
import base64
import io

# === CONFIGURATION ===
st.set_page_config(page_title="BijouStock", page_icon="jewel", layout="wide")

DB_NAME = "bijoustock.db"

# === INITIALISATION BASE ===
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS produits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        categorie TEXT,
        prix_achat REAL,
        prix_vente REAL,
        stock INTEGER DEFAULT 0,
        alerte INTEGER DEFAULT 5
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS ventes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produit_id INTEGER,
        quantite INTEGER,
        date TEXT,
        prix_vente REAL,
        FOREIGN KEY (produit_id) REFERENCES produits (id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS achats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produit_id INTEGER,
        quantite INTEGER,
        date TEXT,
        prix_achat REAL,
        FOREIGN KEY (produit_id) REFERENCES produits (id)
    )''')
    conn.commit()
    conn.close()

init_db()

# === FONCTIONS BASE ===
def ajouter_produit(nom, cat, pa, pv, stock, alerte):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO produits (nom, categorie, prix_achat, prix_vente, stock, alerte) VALUES (?, ?, ?, ?, ?, ?)",
              (nom, cat, pa, pv, stock, alerte))
    conn.commit()
    conn.close()

def vendre(produit_id, qty):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT stock, prix_vente FROM produits WHERE id = ?", (produit_id,))
    res = c.fetchone()
    if res and res[0] >= qty:
        c.execute("UPDATE produits SET stock = stock - ? WHERE id = ?", (qty, produit_id))
        c.execute("INSERT INTO ventes (produit_id, quantite, date, prix_vente) VALUES (?, ?, ?, ?)",
                  (produit_id, qty, datetime.now().isoformat(), res[1]))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def reappro(produit_id, qty, pa):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE produits SET stock = stock + ? WHERE id = ?", (qty, produit_id))
    c.execute("INSERT INTO achats (produit_id, quantite, date, prix_achat) VALUES (?, ?, ?, ?)",
              (produit_id, qty, datetime.now().isoformat(), pa))
    conn.commit()
    conn.close()

# === PAGE PRINCIPALE ===
st.title("BijouStock - Gestion Commerçant")
st.markdown("**Lunettes • Montres • Bijoux • Stocks • Rapports**")

menu = ["Accueil", "Produits", "Vendre", "Réappro", "Rapports", "Export"]
choix = st.sidebar.selectbox("Menu", menu)

# =================== ACCUEIL ===================
if choix == "Accueil":
    col1, col2, col3 = st.columns(3)
    conn = sqlite3.connect(DB_NAME)
    total_produits = pd.read_sql("SELECT COUNT(*) FROM produits", conn).iloc[0,0]
    total_stock = pd.read_sql("SELECT SUM(stock) FROM produits", conn).iloc[0,0]
    ca_semaine = pd.read_sql(f"""
        SELECT SUM(quantite * prix_vente) FROM ventes 
        WHERE date >= '{(datetime.now() - timedelta(days=7)).isoformat()}'
    """, conn).iloc[0,0] or 0
    conn.close()

    col1.metric("Produits", total_produits)
    col2.metric("En stock", total_stock)
    col3.metric("CA 7 jours", f"{ca_semaine:,.2f} €")

    st.markdown("---")
    alertes = pd.read_sql("SELECT nom, stock FROM produits WHERE stock <= alerte", sqlite3.connect(DB_NAME))
    if not alertes.empty:
        st.error("STOCK BAS !")
        st.dataframe(alertes, use_container_width=True)

# =================== PRODUITS ===================
elif choix == "Produits":
    st.subheader("Ajouter un produit")
    with st.form("add_prod"):
        col1, col2 = st.columns(2)
        with col1:
            nom = st.text_input("Nom du produit")
            cat = st.selectbox("Catégorie", ["Lunettes", "Montres", "Bijoux", "Accessoires"])
            pa = st.number_input("Prix d'achat (€)", min_value=0.0)
        with col2:
            pv = st.number_input("Prix de vente (€)", min_value=0.0)
            stock = st.number_input("Stock initial", min_value=0)
            alerte = st.number_input("Alerte si ≤", value=5)
        if st.form_submit_button("Ajouter"):
            ajouter_produit(nom, cat, pa, pv, stock, alerte)
            st.success("Produit ajouté !")

    st.subheader("Tous les produits")
    df = pd.read_sql("SELECT * FROM produits", sqlite3.connect(DB_NAME))
    st.dataframe(df, use_container_width=True)

# =================== VENDRE ===================
elif choix == "Vendre":
    st.subheader("Enregistrer une vente")
    produits = pd.read_sql("SELECT id, nom, stock, prix_vente FROM produits WHERE stock > 0", sqlite3.connect(DB_NAME))
    if not produits.empty:
        produit = st.selectbox("Produit", produits["nom"])
        pid = produits[produits["nom"] == produit]["id"].iloc[0]
        max_qty = produits[produits["nom"] == produit]["stock"].iloc[0]
        qty = st.number_input("Quantité", min_value=1, max_value=int(max_qty))
        if st.button("Vendre"):
            if vendre(pid, qty):
                st.success(f"Vendu : {qty} × {produit}")
            else:
                st.error("Stock insuffisant")
    else:
        st.info("Aucun produit en stock")

# =================== RÉAPPRO ===================
elif choix == "Réappro":
    st.subheader("Réapprovisionner")
    produits = pd.read_sql("SELECT id, nom FROM produits", sqlite3.connect(DB_NAME))
    produit = st.selectbox("Produit", produits["nom"])
    pid = produits[produits["nom"] == produit]["id"].iloc[0]
    qty = st.number_input("Quantité à ajouter", min_value=1)
    pa = st.number_input("Prix d'achat unitaire (€)", min_value=0.0)
    if st.button("Réapprovisionner"):
        reappro(pid, qty, pa)
        st.success("Réappro fait !")

# =================== RAPPORTS ===================
elif choix == "Rapports":
    st.subheader("Rapports & Analyses")

    # Top 5 vendus
    debut = (datetime.now() - timedelta(days=7)).isoformat()
    ventes = pd.read_sql(f"""
        SELECT p.nom, SUM(v.quantite) as vendu 
        FROM ventes v JOIN produits p ON v.produit_id = p.id 
        WHERE v.date >= '{debut}' 
        GROUP BY p.nom ORDER BY vendu DESC LIMIT 5
    """, sqlite3.connect(DB_NAME))
    if not ventes.empty:
        fig = px.bar(ventes, x="nom", y="vendu", title="Top 5 vendus (7 jours)")
        st.plotly_chart(fig, use_container_width=True)

    # Rentabilité
    rent = pd.read_sql("""
        SELECT p.nom, p.prix_achat, p.prix_vente, 
               COALESCE(SUM(v.quantite),0) as vendu,
               (p.prix_vente - p.prix_achat) * COALESCE(SUM(v.quantite),0) as marge
        FROM produits p LEFT JOIN ventes v ON p.id = v.produit_id
        GROUP BY p.id ORDER BY marge DESC
    """, sqlite3.connect(DB_NAME))
    st.write("**Rentabilité**")
    st.dataframe(rent, use_container_width=True)

# =================== EXPORT ===================
elif choix == "Export":
    st.subheader("Exporter les données")
    
    # Export Excel
    conn = sqlite3.connect(DB_NAME)
    produits_df = pd.read_sql("SELECT * FROM produits", conn)
    ventes_df = pd.read_sql("SELECT * FROM ventes", conn)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        produits_df.to_excel(writer, sheet_name='Produits', index=False)
        ventes_df.to_excel(writer, sheet_name='Ventes', index=False)
    output.seek(0)
    
    b64 = base64.b64encode(output.read()).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="bijoustock_export.xlsx">Télécharger Excel</a>'
    st.markdown(href, unsafe_allow_html=True)
