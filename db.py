# db.py
import sqlite3
from datetime import datetime

DB_FILE = "data.db"

def _get_conn():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    c = _get_conn()
    cur = c.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS produits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT UNIQUE NOT NULL,
        categorie TEXT DEFAULT '',
        prix_achat REAL DEFAULT 0,
        prix_vente REAL DEFAULT 0,
        stock INTEGER DEFAULT 0,
        total_vendu INTEGER DEFAULT 0,
        total_revenu REAL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS ventes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produit_id INTEGER,
        quantite INTEGER,
        prix_vente_unitaire REAL,
        date TEXT,
        FOREIGN KEY(produit_id) REFERENCES produits(id)
    );

    CREATE TABLE IF NOT EXISTS achats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produit_id INTEGER,
        quantite INTEGER,
        prix_achat_unitaire REAL,
        date TEXT,
        FOREIGN KEY(produit_id) REFERENCES produits(id)
    );

    CREATE TABLE IF NOT EXISTS depenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT,
        description TEXT,
        montant REAL,
        date TEXT
    );
    """)
    c.commit()
    c.close()

# ----------------- Produits -----------------
def add_or_update_produit(nom, categorie="", stock=0, prix_achat=0.0, prix_vente=0.0):
    """
    Si le produit existe, on met à jour : stock += stock, prix_achat moyen pondéré si stock>0 fourni.
    Sinon on l'insère.
    """
    c = _get_conn()
    cur = c.cursor()
    cur.execute("SELECT * FROM produits WHERE nom = ?", (nom.strip(),))
    row = cur.fetchone()
    if row:
        # calcul prix achat moyen pondéré si on fournit une quantité > 0
        ancien_stock = row["stock"] or 0
        ancien_prix = row["prix_achat"] or 0.0
        new_stock = ancien_stock + int(stock)
        if int(stock) > 0 and new_stock > 0:
            prix_moy = (ancien_prix * ancien_stock + float(prix_achat) * int(stock)) / new_stock
        else:
            prix_moy = ancien_prix
        prix_vente_final = float(prix_vente) if float(prix_vente) > 0 else row["prix_vente"]
        cur.execute("""
            UPDATE produits
            SET stock = ?, prix_achat = ?, prix_vente = ?, categorie = ?
            WHERE id = ?
        """, (new_stock, prix_moy, prix_vente_final, categorie, row["id"]))
    else:
        cur.execute("""
            INSERT INTO produits (nom, categorie, stock, prix_achat, prix_vente)
            VALUES (?, ?, ?, ?, ?)
        """, (nom.strip(), categorie, int(stock), float(prix_achat), float(prix_vente)))
    c.commit()
    c.close()

def get_produits():
    c = _get_conn()
    rows = c.execute("SELECT * FROM produits ORDER BY nom").fetchall()
    c.close()
    return rows

def get_produit_by_id(pid):
    c = _get_conn()
    row = c.execute("SELECT * FROM produits WHERE id = ?", (pid,)).fetchone()
    c.close()
    return row

def update_produit(pid, nom=None, categorie=None, prix_achat=None, prix_vente=None, stock=None):
    c = _get_conn()
    cur = c.cursor()
    # Build dynamic update
    fields, vals = [], []
    if nom is not None:
        fields.append("nom = ?"); vals.append(nom)
    if categorie is not None:
        fields.append("categorie = ?"); vals.append(categorie)
    if prix_achat is not None:
        fields.append("prix_achat = ?"); vals.append(float(prix_achat))
    if prix_vente is not None:
        fields.append("prix_vente = ?"); vals.append(float(prix_vente))
    if stock is not None:
        fields.append("stock = ?"); vals.append(int(stock))
    if not fields:
        c.close(); return
    vals.append(pid)
    sql = f"UPDATE produits SET {', '.join(fields)} WHERE id = ?"
    cur.execute(sql, tuple(vals))
    c.commit()
    c.close()

def delete_produit(pid):
    c = _get_conn()
    cur = c.cursor()
    cur.execute("DELETE FROM produits WHERE id = ?", (pid,))
    # Note: on ne supprime pas ventes/achats liés pour conserver historique (optionnel)
    c.commit()
    c.close()

def get_produits_stock_below(threshold):
    c = _get_conn()
    rows = c.execute("SELECT * FROM produits WHERE stock <= ? ORDER BY stock ASC", (threshold,)).fetchall()
    c.close()
    return rows

# ----------------- Achats -----------------
def add_achat(produit_id, quantite, prix_achat_unitaire, date_str=None):
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    c = _get_conn()
    cur = c.cursor()
    cur.execute("INSERT INTO achats (produit_id, quantite, prix_achat_unitaire, date) VALUES (?, ?, ?, ?)",
                (produit_id, int(quantite), float(prix_achat_unitaire), date_str))
    # Mettre à jour stock et prix achat moyen pondéré
    cur.execute("SELECT stock, prix_achat FROM produits WHERE id = ?", (produit_id,))
    row = cur.fetchone()
    if row:
        ancien_stock = row["stock"] or 0
        ancien_prix = row["prix_achat"] or 0.0
        total_q = ancien_stock + int(quantite)
        if total_q > 0:
            prix_moy = (ancien_prix * ancien_stock + float(prix_achat_unitaire) * int(quantite)) / total_q
        else:
            prix_moy = float(prix_achat_unitaire)
        cur.execute("UPDATE produits SET stock = ?, prix_achat = ? WHERE id = ?", (total_q, prix_moy, produit_id))
    c.commit()
    c.close()

def get_achats(limit=500):
    c = _get_conn()
    rows = c.execute("""
        SELECT a.*, p.nom AS produit_nom FROM achats a
        LEFT JOIN produits p ON a.produit_id = p.id
        ORDER BY date DESC LIMIT ?
    """, (limit,)).fetchall()
    c.close()
    return rows

# ----------------- Ventes -----------------
def add_vente(produit_id, quantite, prix_vente_unitaire, date_str=None):
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    c = _get_conn()
    cur = c.cursor()
    cur.execute("INSERT INTO ventes (produit_id, quantite, prix_vente_unitaire, date) VALUES (?, ?, ?, ?)",
                (produit_id, int(quantite), float(prix_vente_unitaire), date_str))
    # Mise à jour produit : stock, total_vendu, total_revenu
    cur.execute("""
        UPDATE produits
        SET stock = stock - ?, total_vendu = total_vendu + ?, total_revenu = total_revenu + ?
        WHERE id = ?
    """, (int(quantite), int(quantite), int(quantite) * float(prix_vente_unitaire), produit_id))
    c.commit()
    c.close()

def get_ventes(limit=500):
    c = _get_conn()
    rows = c.execute("""
        SELECT v.*, p.nom AS produit_nom FROM ventes v
        LEFT JOIN produits p ON v.produit_id = p.id
        ORDER BY date DESC LIMIT ?
    """, (limit,)).fetchall()
    c.close()
    return rows

# ----------------- Depenses -----------------
def add_depense(type_dep, montant, description="", date_str=None):
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    c = _get_conn()
    cur = c.cursor()
    cur.execute("INSERT INTO depenses (type, description, montant, date) VALUES (?, ?, ?, ?)",
                (type_dep, description, float(montant), date_str))
    c.commit()
    c.close()

def get_depenses(limit=500):
    c = _get_conn()
    rows = c.execute("SELECT * FROM depenses ORDER BY date DESC LIMIT ?", (limit,)).fetchall()
    c.close()
    return rows

# ----------------- Exports utilitaires -----------------
def get_all_produits_dict():
    return [dict(r) for r in get_produits()]

def get_all_ventes_dict():
    return [dict(r) for r in get_ventes(100000)]

def get_all_achats_dict():
    return [dict(r) for r in get_achats(100000)]

def get_all_depenses_dict():
    return [dict(r) for r in get_depenses(100000)]

def reset_database(confirm=False):
    """
    Supprime toutes les données (produits, ventes, achats, dépenses)
    sans supprimer la structure des tables.
    Utiliser confirm=True pour exécuter réellement.
    """
    if not confirm:
        print("⚠️  Appel ignoré : utilisez reset_database(confirm=True) pour confirmer la suppression.")
        return

    c = _get_conn()
    cur = c.cursor()
    cur.executescript("""
        DELETE FROM ventes;
        DELETE FROM achats;
        DELETE FROM depenses;
        DELETE FROM produits;
        VACUUM;
    """)
    c.commit()
    c.close()
    print("✅ Base de données entièrement vidée.")