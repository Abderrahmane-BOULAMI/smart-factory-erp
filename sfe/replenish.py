"""Règles de réapprovisionnement (point de commande, stock de sécurité) et calcul des besoins nets."""
from __future__ import annotations

import math

from . import masterdata as md

Z_95 = 1.65  # niveau de service visé : 95 % des cycles sans rupture


def daily_usage(plan_per_day: dict[str, float]) -> dict[str, float]:
    """Consommation journalière moyenne de chaque composant acheté, à partir du plan de production."""
    use: dict[str, float] = {}
    for pf, qty in plan_per_day.items():
        for c, q in md.explode(pf, qty).items():
            use[c] = use.get(c, 0) + q
    return use


def build_rules(plan_per_day: dict[str, float], cv: float = 0.45) -> list[tuple]:
    """Point de commande = consommation pendant le délai + stock de sécurité ; quantité = 10 jours, au minimum la
    quantité minimale fournisseur. cv : variabilité journalière de la consommation pendant la montée en cadence."""
    sup = {s[0]: s for s in md.SUPPLIERS}
    stock_locs = [loc for loc, zone, _ in md.locations() if zone == "stock"]
    rules = []
    use = daily_usage(plan_per_day)
    purchased = [i for i in md.ITEMS if i[2] in ("composant", "emballage")]
    for k, item in enumerate(purchased):
        iid, supplier = item[0], item[4]
        d = use.get(iid, 0.0)
        lt = sup[supplier][3]
        moq = sup[supplier][4]
        ss = math.ceil(Z_95 * cv * d * math.sqrt(lt))
        rop = math.ceil(d * lt + ss)
        qty = max(moq, math.ceil(d * 10 / moq) * moq)
        rules.append((iid, rop, qty, ss, stock_locs[k % len(stock_locs)]))
    return rules


def net_requirements(plan: dict[str, list[float]], on_hand: dict[str, float], on_order: dict[str, float],
                     safety: dict[str, float]) -> list[dict]:
    """Calcul des besoins nets (MRP simplifié) sur l'horizon du plan : besoin brut éclaté, moins stock et commandes
    en cours, plus stock de sécurité. plan : {produit fini: [quantité par jour]}."""
    horizon = len(next(iter(plan.values())))
    gross: dict[str, float] = {}
    for pf, days in plan.items():
        for c, q in md.explode(pf, sum(days)).items():
            gross[c] = gross.get(c, 0) + q
    rows = []
    for c, g in sorted(gross.items()):
        avail = on_hand.get(c, 0) + on_order.get(c, 0)
        net = max(0.0, g + safety.get(c, 0) - avail)
        rows.append({"article": c, "besoin brut": round(g), "stock": round(on_hand.get(c, 0)),
                     "en commande": round(on_order.get(c, 0)), "stock de sécurité": round(safety.get(c, 0)),
                     "besoin net": round(net), "horizon (jours)": horizon})
    return rows
