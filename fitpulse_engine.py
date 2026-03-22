"""
FitPulse Engine — Moteur d'Analyse Opérationnelle
Preuve de concept : croisement scan × stock × cabine → décisions

Ce script simule le pipeline de traitement FitPulse sur un échantillon
de données réalistes d'un samedi en magasin mode.

Auteur : Hajar Bougataya — CY Tech / Analytics Engineer Nickel (BNP Paribas)
Projet : PwC Challenge Étudiants 2026
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

np.random.seed(42)

# ============================================================
# 1. DONNÉES DE RÉFÉRENCE — Catalogue & Stock
# ============================================================

articles = pd.DataFrame([
    {"ref": "REF-2847", "name": "Veste blazer oversize", "price": 59.95, "category": "Vestes", "fit": "oversize"},
    {"ref": "REF-3291", "name": "Jean wide leg", "price": 39.95, "category": "Pantalons", "fit": "regular"},
    {"ref": "REF-1156", "name": "Top côtelé blanc", "price": 15.95, "category": "Tops", "fit": "slim"},
    {"ref": "REF-4420", "name": "Robe midi satinée", "price": 49.95, "category": "Robes", "fit": "regular"},
    {"ref": "REF-5503", "name": "Pantalon cargo", "price": 35.95, "category": "Pantalons", "fit": "regular"},
    {"ref": "REF-6612", "name": "Pull maille torsadée", "price": 29.95, "category": "Maille", "fit": "oversize"},
    {"ref": "REF-7701", "name": "Jupe plissée midi", "price": 25.95, "category": "Jupes", "fit": "regular"},
    {"ref": "REF-8890", "name": "Chemise oversize lin", "price": 35.95, "category": "Chemises", "fit": "oversize"},
])

sizes = ["XS", "S", "M", "L", "XL"]

# Stock initial — volontairement bas sur certaines tailles pour déclencher des alertes
stock_data = []
for _, art in articles.iterrows():
    for size in sizes:
        # Stock réaliste : M et S plus demandés donc stock plus bas
        if size == "M":
            qty = np.random.randint(1, 5)
        elif size == "S":
            qty = np.random.randint(2, 7)
        else:
            qty = np.random.randint(3, 12)
        stock_data.append({"article_ref": art["ref"], "size": size, "stock_qty": qty})

stock = pd.DataFrame(stock_data)

# Forcer un cas critique pour la démo
stock.loc[(stock["article_ref"] == "REF-2847") & (stock["size"] == "M"), "stock_qty"] = 2
stock.loc[(stock["article_ref"] == "REF-1156") & (stock["size"] == "S"), "stock_qty"] = 1

print("=" * 70)
print("FITPULSE ENGINE — Simulation Samedi en Magasin Mode")
print("=" * 70)
print(f"\n📦 Catalogue : {len(articles)} articles")
print(f"📊 Stock : {len(stock)} lignes (article × taille)")

# ============================================================
# 2. SIMULATION — 500 événements de scan (samedi 10h-18h)
# ============================================================

n_scans = 500

# Distribution réaliste : certains articles plus populaires
article_probs = [0.22, 0.18, 0.16, 0.14, 0.10, 0.08, 0.07, 0.05]
# Distribution tailles : M et S plus demandés
size_probs = [0.08, 0.25, 0.35, 0.22, 0.10]
# Distribution horaire : pic 14h-17h
hour_probs = [0.04, 0.06, 0.09, 0.12, 0.18, 0.20, 0.18, 0.13]

scans = pd.DataFrame({
    "scan_id": range(1, n_scans + 1),
    "article_ref": np.random.choice(articles["ref"].values, n_scans, p=article_probs),
    "size_viewed": np.random.choice(sizes, n_scans, p=size_probs),
    "hour": np.random.choice(range(10, 18), n_scans, p=hour_probs),
    "session_id": [f"sess_{np.random.randint(1, 150):04d}" for _ in range(n_scans)],
})

print(f"\n⚡ Scans générés : {n_scans} événements (samedi 10h-18h)")
print(f"   Sessions uniques : {scans['session_id'].nunique()} clients")

# ============================================================
# 3. SIMULATION — Cabine (essayage + gardé/reposé)
# ============================================================

# 35% des articles scannés sont essayés en cabine
cabin_mask = np.random.random(n_scans) < 0.35
cabin_events = scans[cabin_mask].copy()

# Parmi les essayés : taux de conversion variable par article
# REF-2847 a un problème → conversion basse
conversion_rates = {
    "REF-2847": 0.25,  # Problématique — coupe décevante
    "REF-3291": 0.65,  # Bon
    "REF-1156": 0.60,  # Correct
    "REF-4420": 0.78,  # Très bon
    "REF-5503": 0.55,  # Moyen
    "REF-6612": 0.50,  # Moyen
    "REF-7701": 0.45,  # Moyen-bas
    "REF-8890": 0.70,  # Bon
}

cabin_events["kept"] = cabin_events["article_ref"].apply(
    lambda ref: np.random.random() < conversion_rates.get(ref, 0.5)
)
cabin_events["duration_min"] = np.random.normal(8, 2.5, len(cabin_events)).clip(3, 18).astype(int)

print(f"\n👗 Essayages cabine : {len(cabin_events)} articles essayés")
print(f"   Gardés : {cabin_events['kept'].sum()} | Reposés : {(~cabin_events['kept']).sum()}")

# ============================================================
# 4. SIMULATION — Ventes (POS)
# ============================================================

# Les articles gardés en cabine + quelques achats directs sans scan
ventes_cabine = cabin_events[cabin_events["kept"]][["article_ref", "size_viewed", "hour"]].copy()
ventes_cabine.columns = ["article_ref", "size", "hour"]

# 10% d'achats directs (clients sans FitPulse)
n_direct = 50
ventes_directes = pd.DataFrame({
    "article_ref": np.random.choice(articles["ref"].values, n_direct, p=article_probs),
    "size": np.random.choice(sizes, n_direct, p=size_probs),
    "hour": np.random.choice(range(10, 18), n_direct, p=hour_probs),
})

ventes = pd.concat([ventes_cabine, ventes_directes], ignore_index=True)
print(f"\n💰 Ventes POS : {len(ventes)} transactions")

# ============================================================
# 5. WORKER STOCKMONITOR — Croisement scans vs stock → alertes
# ============================================================

print("\n" + "=" * 70)
print("🔴 WORKER STOCKMONITOR — Alertes Réassort")
print("=" * 70)

scan_demand = scans.groupby(["article_ref", "size_viewed"]).size().reset_index(name="nb_scans")
scan_demand.columns = ["article_ref", "size", "nb_scans"]

stock_cross = scan_demand.merge(stock, on=["article_ref", "size"])
stock_cross["ratio"] = (stock_cross["nb_scans"] / stock_cross["stock_qty"].replace(0, 0.1)).round(1)

# Seuil configurable — défaut : ratio > 3
SEUIL_RESTOCK = 3.0

alertes_restock = stock_cross[stock_cross["ratio"] > SEUIL_RESTOCK].sort_values("ratio", ascending=False)
alertes_restock = alertes_restock.merge(articles[["ref", "name"]], left_on="article_ref", right_on="ref")

print(f"\n⚠️  {len(alertes_restock)} alertes réassort détectées (seuil ratio > {SEUIL_RESTOCK}) :\n")
for _, row in alertes_restock.iterrows():
    severity = "🔴 CRITIQUE" if row["stock_qty"] <= 1 else "🟡 WARNING"
    print(f"   {severity} | {row['name']} taille {row['size']}")
    print(f"            Scans: {row['nb_scans']} | Stock: {row['stock_qty']} | Ratio: {row['ratio']}x")

# ============================================================
# 6. WORKER PRODUCTSCORER — Conversion cabine + tueurs de panier
# ============================================================

print("\n" + "=" * 70)
print("🟡 WORKER PRODUCTSCORER — Analyse Conversion Cabine")
print("=" * 70)

product_kpis = scans.groupby("article_ref").size().reset_index(name="nb_scans")
essais = cabin_events.groupby("article_ref").size().reset_index(name="nb_essais")
achats = cabin_events[cabin_events["kept"]].groupby("article_ref").size().reset_index(name="nb_achats")

product_kpis = product_kpis.merge(essais, on="article_ref", how="left")
product_kpis = product_kpis.merge(achats, on="article_ref", how="left")
product_kpis = product_kpis.merge(articles[["ref", "name", "price"]], left_on="article_ref", right_on="ref")
product_kpis = product_kpis.fillna(0)

product_kpis["conversion_cabine"] = (
    product_kpis["nb_achats"] / product_kpis["nb_essais"].replace(0, 1) * 100
).round(1)
product_kpis["scan_to_buy"] = (
    product_kpis["nb_achats"] / product_kpis["nb_scans"].replace(0, 1) * 100
).round(1)

product_kpis = product_kpis.sort_values("nb_scans", ascending=False)

print(f"\n📊 Scoring produits :\n")
print(f"   {'Article':<30} {'Scans':>6} {'Essais':>7} {'Achats':>7} {'Conv.cab':>9} {'Scan→Buy':>9}")
print("   " + "-" * 72)
for _, row in product_kpis.iterrows():
    flag = " ⚠️" if row["conversion_cabine"] < 35 and row["nb_essais"] >= 5 else ""
    print(f"   {row['name']:<30} {int(row['nb_scans']):>6} {int(row['nb_essais']):>7} {int(row['nb_achats']):>7} {row['conversion_cabine']:>8}% {row['scan_to_buy']:>8}%{flag}")

# Articles problématiques
problematic = product_kpis[(product_kpis["conversion_cabine"] < 35) & (product_kpis["nb_essais"] >= 5)]
if len(problematic) > 0:
    print(f"\n🚨 {len(problematic)} article(s) problématique(s) détecté(s) :")
    for _, row in problematic.iterrows():
        print(f"   → {row['name']} : conversion cabine {row['conversion_cabine']}% (essayé {int(row['nb_essais'])}x, gardé {int(row['nb_achats'])}x)")
        print(f"     Signal : coupe, matière ou taillant à revoir")

# ============================================================
# 7. WORKER STAFFINGPREDICTOR — Pics d'affluence
# ============================================================

print("\n" + "=" * 70)
print("🟢 WORKER STAFFINGPREDICTOR — Détection Pics Affluence")
print("=" * 70)

hourly_scans = scans.groupby("hour").size()
mean_hourly = hourly_scans.mean()
seuil_pic = mean_hourly * 1.3

print(f"\n📈 Scans par heure :\n")
for hour in range(10, 18):
    count = hourly_scans.get(hour, 0)
    bar = "█" * int(count / 3)
    flag = " ← 🔴 PIC DÉTECTÉ" if count > seuil_pic else ""
    print(f"   {hour:02d}h : {count:>4} scans {bar}{flag}")

pics = hourly_scans[hourly_scans > seuil_pic]
print(f"\n⚡ {len(pics)} pic(s) détecté(s) (seuil: {seuil_pic:.0f} scans/h)")
for hour, count in pics.items():
    surplus_pct = ((count - mean_hourly) / mean_hourly * 100)
    print(f"   → {hour}h : {count} scans (+{surplus_pct:.0f}% vs moyenne) → Recommandation : +2 vendeurs")

# ============================================================
# 8. ANALYSE DIRECTION — Demande réelle vs Ventes
# ============================================================

print("\n" + "=" * 70)
print("🟣 ANALYSE DIRECTION — Demande Réelle vs Ventes (kpi_demand_vs_sales)")
print("=" * 70)

vente_counts = ventes.groupby(["article_ref", "size"]).size().reset_index(name="nb_ventes")

demand_vs_sales = scan_demand.merge(vente_counts, on=["article_ref", "size"], how="left")
demand_vs_sales = demand_vs_sales.fillna(0)
demand_vs_sales["nb_ventes"] = demand_vs_sales["nb_ventes"].astype(int)
demand_vs_sales["demand_multiplier"] = (
    demand_vs_sales["nb_scans"] / demand_vs_sales["nb_ventes"].replace(0, 0.5)
).round(1)
demand_vs_sales = demand_vs_sales.merge(articles[["ref", "name"]], left_on="article_ref", right_on="ref")
demand_vs_sales = demand_vs_sales.merge(stock, on=["article_ref", "size"])

# Cas critiques : demande >> ventes
sous_commandes = demand_vs_sales[demand_vs_sales["demand_multiplier"] > 3].sort_values("demand_multiplier", ascending=False)

print(f"\n📊 Sous-commandes détectées (demand_multiplier > 3x) :\n")
print(f"   {'Article':<30} {'Taille':>6} {'Scans':>6} {'Ventes':>7} {'Multi.':>7} {'Stock':>6} {'Diagnostic'}")
print("   " + "-" * 90)
for _, row in sous_commandes.iterrows():
    if row["stock_qty"] <= 2:
        diag = "RUPTURE STOCK → ventes perdues"
    elif row["demand_multiplier"] > 5:
        diag = "FORTE sous-commande taille"
    else:
        diag = "Sous-commande probable"
    print(f"   {row['name']:<30} {row['size']:>6} {int(row['nb_scans']):>6} {int(row['nb_ventes']):>7} {row['demand_multiplier']:>6}x {int(row['stock_qty']):>6} {diag}")

# ============================================================
# 9. RÉSUMÉ — Ce que FitPulse a détecté
# ============================================================

print("\n" + "=" * 70)
print("📋 RÉSUMÉ — Décisions générées par FitPulse")
print("=" * 70)

print(f"""
   🔴 Alertes réassort :        {len(alertes_restock)} (dont {len(alertes_restock[alertes_restock['stock_qty'] <= 1])} critiques)
   🟡 Articles problématiques : {len(problematic)}
   🟢 Pics affluence détectés : {len(pics)}
   🟣 Sous-commandes tailles :  {len(sous_commandes)}

   Sans FitPulse, AUCUNE de ces {len(alertes_restock) + len(problematic) + len(pics) + len(sous_commandes)} décisions
   n'aurait été détectée. Le manager aurait piloté à l'aveugle.
   La direction aurait commandé les mêmes tailles le mois prochain.
""")

# ============================================================
# 10. EXPORT — Données pour le dashboard Streamlit
# ============================================================

product_kpis.to_csv("fitpulse_product_kpis.csv", index=False)
alertes_restock.to_csv("fitpulse_alertes_restock.csv", index=False)
hourly_scans.to_frame("scans").to_csv("fitpulse_hourly.csv")
sous_commandes.to_csv("fitpulse_demand_vs_sales.csv", index=False)
scans.to_csv("fitpulse_scans_raw.csv", index=False)

print("   📁 Fichiers exportés pour le dashboard Streamlit :")
print("      → fitpulse_product_kpis.csv")
print("      → fitpulse_alertes_restock.csv")
print("      → fitpulse_hourly.csv")
print("      → fitpulse_demand_vs_sales.csv")
print("      → fitpulse_scans_raw.csv")
