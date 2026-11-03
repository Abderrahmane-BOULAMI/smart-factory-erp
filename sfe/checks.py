"""Contrôles de qualité des données de base, à passer avant chaque mise en service d'un volet de l'ERP.

Une donnée de base fausse se propage partout : un article sans fournisseur n'est jamais réapprovisionné, une
nomenclature incomplète fausse le calcul des besoins, un emplacement mal codé rend le code-barres illisible.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

LOC_PATTERN = re.compile(r"^[A-Z]{3}-[A-Z0-9]{2,3}(-\d)?$")


@dataclass
class Issue:
    rule: str
    obj: str
    detail: str
    severity: str  # "bloquant" ou "à corriger"


def check(items, bom, routing, workcenters, suppliers, locations, plans, rules) -> list[Issue]:
    issues: list[Issue] = []
    item_ids = {i[0] for i in items}
    sup_ids = {s[0] for s in suppliers}
    wc_ids = {w[0] for w in workcenters}
    loc_zone = {}
    parents = {p for p, _, _ in bom}
    routed = {r[0] for r in routing}

    for i in items:
        iid, _, typ, track, sup, cost, critical, _rep = i
        if typ in ("composant", "emballage"):
            if not sup:
                issues.append(Issue("Fournisseur manquant", iid, "article acheté sans fournisseur", "bloquant"))
            elif sup not in sup_ids:
                issues.append(Issue("Fournisseur inconnu", iid, f"{sup} absent du référentiel", "bloquant"))
            if cost <= 0:
                issues.append(Issue("Coût manquant", iid, "coût unitaire nul", "à corriger"))
        if typ in ("sous-ensemble", "produit fini") and iid not in parents:
            issues.append(Issue("Nomenclature manquante", iid, "article fabriqué sans nomenclature", "bloquant"))
        if typ == "produit fini":
            if iid not in routed:
                issues.append(Issue("Gamme manquante", iid, "produit fini sans gamme", "bloquant"))
            if track != "série":
                issues.append(Issue("Traçabilité", iid, "produit fini non suivi par numéro de série", "bloquant"))
        if critical and track != "lot":
            issues.append(Issue("Traçabilité", iid, "composant critique non suivi par lot", "bloquant"))

    for p, c, q in bom:
        for x in (p, c):
            if x not in item_ids:
                issues.append(Issue("Nomenclature", f"{p} > {c}", f"article {x} inconnu", "bloquant"))
        if q <= 0:
            issues.append(Issue("Nomenclature", f"{p} > {c}", "quantité nulle ou négative", "bloquant"))

    # cycles de nomenclature (un article qui se contient lui-même)
    children: dict[str, list[str]] = {}
    for p, c, _ in bom:
        children.setdefault(p, []).append(c)

    def has_cycle(node, path):
        for c in children.get(node, []):
            if c in path:
                return True
            if has_cycle(c, path | {c}):
                return True
        return False
    for p in parents:
        if has_cycle(p, {p}):
            issues.append(Issue("Nomenclature", p, "cycle : l'article se contient lui-même", "bloquant"))

    for r in routing:
        if r[2] not in wc_ids:
            issues.append(Issue("Gamme", f"{r[0]} op {r[1]}", f"poste {r[2]} inconnu", "bloquant"))
        if r[4] <= 0:
            issues.append(Issue("Gamme", f"{r[0]} op {r[1]}", "temps standard nul", "bloquant"))

    seen = set()
    for code, zone, _cap in locations:
        if code in seen:
            issues.append(Issue("Emplacement", code, "code en double", "bloquant"))
        seen.add(code)
        loc_zone[code] = zone
        if not LOC_PATTERN.match(code):
            issues.append(Issue("Emplacement", code, "code non conforme au format des codes-barres", "à corriger"))

    plan_items = {(p[1], p[2]) for p in plans}
    for i in items:
        if i[6] and ("réception", i[0]) not in plan_items:
            issues.append(Issue("Plan de contrôle", i[0], "composant critique sans contrôle à réception", "bloquant"))
    for p in plans:
        if p[4] is not None and p[5] is not None and p[4] >= p[5]:
            issues.append(Issue("Plan de contrôle", p[0], "limite basse supérieure à la limite haute", "bloquant"))

    rule_items = {r[0]: r for r in rules}
    for i in items:
        if i[2] in ("composant", "emballage"):
            r = rule_items.get(i[0])
            if r is None:
                issues.append(Issue("Réapprovisionnement", i[0], "aucune règle de réapprovisionnement", "bloquant"))
            elif loc_zone.get(r[4]) not in ("stock", "bord de ligne"):
                issues.append(Issue("Réapprovisionnement", i[0], f"emplacement {r[4]} hors zone de stock",
                                    "à corriger"))
    return issues
