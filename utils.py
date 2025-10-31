# utils.py
from collections import defaultdict
import db
from datetime import datetime

def _parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date()

def compute_report(from_date_str, to_date_str):
    """
    Retour:
    {
      'from': str, 'to': str,
      'ca': float, 'cout_achat': float, 'depenses': float, 'profit': float,
      'top': list of {produit, qty, revenu},
      'ca_by_day': list [{date, ca}]
    }
    """
    ventes = db.get_all_ventes_dict()
    achats = db.get_all_achats_dict()
    depenses = db.get_all_depenses_dict()
    produits = {p["id"]: p for p in db.get_all_produits_dict()}

    from_d = _parse_date(from_date_str)
    to_d = _parse_date(to_date_str)

    ventes_p = [v for v in ventes if from_d <= _parse_date(v["date"]) <= to_d]
    achats_p = [a for a in achats if from_d <= _parse_date(a["date"]) <= to_d]
    deps_p = [d for d in depenses if from_d <= _parse_date(d["date"]) <= to_d]

    # CA
    ca = 0.0
    for v in ventes_p:
        ca += float(v.get("prix_vente_unitaire", 0.0)) * int(v.get("quantite", 0))

    # coût d'achat estimé — approximation utilisant prix_achat courant du produit
    cout_achat = 0.0
    for v in ventes_p:
        pid = v.get("produit_id")
        prixA = produits.get(pid, {}).get("prix_achat", 0.0)
        cout_achat += float(prixA) * int(v.get("quantite", 0))

    total_dep = sum(float(d.get("montant", 0.0)) for d in deps_p)
    profit = ca - cout_achat - total_dep

    # Top produits par quantité vendue
    byprod = defaultdict(lambda: {"produit": "", "qty": 0, "revenu": 0.0})
    for v in ventes_p:
        pid = v.get("produit_id")
        name = produits.get(pid, {}).get("nom", "—")
        byprod[pid]["produit"] = name
        byprod[pid]["qty"] += int(v.get("quantite", 0))
        byprod[pid]["revenu"] += float(v.get("prix_vente_unitaire", 0.0)) * int(v.get("quantite", 0))

    top_list = sorted(byprod.values(), key=lambda x: x["qty"], reverse=True)

    # CA par jour
    ca_by_day = defaultdict(float)
    for v in ventes_p:
        ca_by_day[v["date"]] += float(v.get("prix_vente_unitaire", 0.0)) * int(v.get("quantite", 0))
    ca_by_day_list = [{"date": d, "ca": ca_by_day[d]} for d in sorted(ca_by_day.keys())]

    return {
        "from": from_date_str,
        "to": to_date_str,
        "ca": ca,
        "cout_achat": cout_achat,
        "depenses": total_dep,
        "profit": profit,
        "top": top_list,
        "ca_by_day": ca_by_day_list
    }