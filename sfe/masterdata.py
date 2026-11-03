"""Données de base d'une usine d'assemblage de mixeurs réparables (produit et fournisseurs fictifs).

C'est le travail le plus structurant d'un déploiement ERP : articles, nomenclatures, gammes, postes, emplacements,
fournisseurs et plans de contrôle. Tout le reste (ordres de fabrication, stock, qualité, indicateurs) en dépend.
"""
from __future__ import annotations

SUPPLIERS = [
    # id, nom (fictif), pays, délai (jours ouvrés), quantité minimale de commande
    ("SUP-MOT", "Moteurs du Rhône", "France", 15, 200),
    ("SUP-ROU", "Roulements d'Alsace", "France", 8, 500),
    ("SUP-PLA", "Plasturgie de l'Ain", "France", 10, 300),
    ("SUP-INO", "Coutellerie de Thiers", "France", 12, 200),
    ("SUP-ELE", "Électronique d'Anjou", "France", 18, 250),
    ("SUP-SIL", "Silicones Lyonnais", "France", 8, 500),
    ("SUP-VER", "Verrerie du Nord", "France", 12, 200),
    ("SUP-VIS", "Visserie Pro", "France", 5, 2000),
    ("SUP-EMB", "Cartonnage Normand", "France", 5, 500),
]

ITEMS = [
    # id, désignation, type, traçabilité, fournisseur, coût unitaire (€), critique, pièce détachée
    ("MOT-650", "Moteur universel 650 W", "composant", "lot", "SUP-MOT", 18.40, 1, 1),
    ("ROU-608", "Roulement 608-2RS", "composant", "lot", "SUP-ROU", 0.62, 1, 1),
    ("ACC-01", "Accouplement moteur-couteau", "composant", "lot", "SUP-PLA", 0.85, 0, 1),
    ("CTO-4L", "Couteau inox 4 lames", "composant", "lot", "SUP-INO", 3.10, 0, 1),
    ("JNT-BOL", "Joint de bol silicone", "composant", "lot", "SUP-SIL", 0.38, 0, 1),
    ("BOL-15", "Bol verre 1,5 L", "composant", "lot", "SUP-VER", 4.90, 0, 1),
    ("COU-15", "Couvercle de bol", "composant", "aucun", "SUP-PLA", 1.20, 0, 1),
    ("BAS-INJ", "Base injectée", "composant", "lot", "SUP-PLA", 2.75, 0, 0),
    ("CAP-INJ", "Capot moteur", "composant", "aucun", "SUP-PLA", 1.05, 0, 0),
    ("CTE-PWR", "Carte de puissance", "composant", "lot", "SUP-ELE", 6.80, 1, 1),
    ("CTE-IHM", "Carte interface à écran", "composant", "lot", "SUP-ELE", 5.20, 1, 1),
    ("BTN-ROT", "Bouton rotatif", "composant", "aucun", "SUP-PLA", 0.45, 0, 1),
    ("CAB-ALM", "Cordon d'alimentation", "composant", "lot", "SUP-ELE", 1.60, 1, 1),
    ("VIS-M4", "Vis M4 x 12", "composant", "aucun", "SUP-VIS", 0.02, 0, 0),
    ("PIE-SIL", "Pied silicone", "composant", "aucun", "SUP-SIL", 0.08, 0, 1),
    ("ETQ-SER", "Étiquette signalétique", "emballage", "aucun", "SUP-EMB", 0.05, 0, 0),
    ("CAR-M1", "Carton individuel", "emballage", "aucun", "SUP-EMB", 0.90, 0, 0),
    ("NOT-REP", "Notice et guide de réparation", "emballage", "aucun", "SUP-EMB", 0.30, 0, 0),
    ("SE-MOT", "Bloc moteur", "sous-ensemble", "aucun", None, 0.0, 0, 1),
    ("SE-BOL", "Bol équipé", "sous-ensemble", "aucun", None, 0.0, 0, 1),
    ("SE-BAS", "Base équipée, bouton", "sous-ensemble", "aucun", None, 0.0, 0, 0),
    ("SE-BAP", "Base équipée, écran", "sous-ensemble", "aucun", None, 0.0, 0, 0),
    ("PF-M1", "Mixeur réparable M1", "produit fini", "série", None, 0.0, 0, 0),
    ("PF-M1P", "Mixeur réparable M1 Plus", "produit fini", "série", None, 0.0, 0, 0),
]

BOM = [
    ("SE-MOT", "MOT-650", 1), ("SE-MOT", "ROU-608", 2), ("SE-MOT", "ACC-01", 1), ("SE-MOT", "CTE-PWR", 1),
    ("SE-MOT", "CAP-INJ", 1), ("SE-MOT", "VIS-M4", 4),
    ("SE-BOL", "BOL-15", 1), ("SE-BOL", "CTO-4L", 1), ("SE-BOL", "JNT-BOL", 1), ("SE-BOL", "COU-15", 1),
    ("SE-BAS", "BAS-INJ", 1), ("SE-BAS", "CAB-ALM", 1), ("SE-BAS", "BTN-ROT", 1), ("SE-BAS", "PIE-SIL", 4),
    ("SE-BAS", "VIS-M4", 4),
    ("SE-BAP", "BAS-INJ", 1), ("SE-BAP", "CAB-ALM", 1), ("SE-BAP", "CTE-IHM", 1), ("SE-BAP", "PIE-SIL", 4),
    ("SE-BAP", "VIS-M4", 4),
    ("PF-M1", "SE-MOT", 1), ("PF-M1", "SE-BOL", 1), ("PF-M1", "SE-BAS", 1), ("PF-M1", "ETQ-SER", 1),
    ("PF-M1", "CAR-M1", 1), ("PF-M1", "NOT-REP", 1),
    ("PF-M1P", "SE-MOT", 1), ("PF-M1P", "SE-BOL", 1), ("PF-M1P", "SE-BAP", 1), ("PF-M1P", "ETQ-SER", 1),
    ("PF-M1P", "CAR-M1", 1), ("PF-M1P", "NOT-REP", 1),
]

WORKCENTERS = [
    ("WC-PRE", "Pré-assemblage bloc moteur", 7.5),
    ("WC-ASM", "Assemblage final", 7.5),
    ("WC-TST", "Banc de test fonctionnel", 7.5),
    ("WC-EMB", "Étiquetage et emballage", 7.5),
]

ROUTING = []
for pf, extra in (("PF-M1", 0), ("PF-M1P", 12)):
    ROUTING += [
        (pf, 10, "WC-PRE", "Montage du bloc moteur (roulements, carte, capot)", 96, "Couple de serrage capot"),
        (pf, 20, "WC-ASM", "Assemblage base, bloc moteur et bol", 104 + extra, None),
        (pf, 30, "WC-TST", "Test fonctionnel : courant, bruit, rigidité diélectrique", 78, "Test final"),
        (pf, 40, "WC-EMB", "Étiquetage, notice et emballage", 52, None),
    ]


def locations():
    locs = [("REC-01", "réception", 40), ("REC-02", "réception", 40), ("CTL-01", "contrôle", 10),
            ("QUA-01", "quarantaine", 20), ("BDL-PRE", "bord de ligne", 12), ("BDL-ASM", "bord de ligne", 16),
            ("EXP-01", "expédition", 30), ("EXP-02", "expédition", 30)]
    locs += [(f"STK-{r}{b:02d}-{n}", "stock", 4) for r in "ABC" for b in range(1, 5) for n in range(1, 4)]
    locs += [(f"PFI-{i:02d}", "produits finis", 24) for i in range(1, 7)]
    locs += [(f"SAV-{i:02d}", "pièces détachées", 8) for i in range(1, 4)]
    return locs


CONTROL_PLANS = [
    # id, étape, article, caractéristique, LSL, USL, unité, taille d'échantillon
    ("CP-R-MOT", "réception", "MOT-650", "Courant à vide", 0.8, 1.4, "A", 3),
    ("CP-R-ROU", "réception", "ROU-608", "Jeu radial", None, 20.0, "µm", 5),
    ("CP-R-PWR", "réception", "CTE-PWR", "Test fonctionnel carte", 1.0, None, "ok", 5),
    ("CP-R-IHM", "réception", "CTE-IHM", "Test fonctionnel carte", 1.0, None, "ok", 5),
    ("CP-R-CAB", "réception", "CAB-ALM", "Continuité et isolement", 1.0, None, "ok", 5),
    ("CP-E-CPL", "en-cours", "SE-MOT", "Couple de serrage capot", 1.0, 1.4, "N·m", 1),
    ("CP-F-CUR", "final", "PF-M1", "Courant en charge", 2.4, 3.2, "A", 1),
    ("CP-F-BRU", "final", "PF-M1", "Niveau sonore à 1 m", None, 82.0, "dB(A)", 1),
    ("CP-F-DIE", "final", "PF-M1", "Rigidité diélectrique", 1.0, None, "ok", 1),
]


def tracked_components(item_id: str) -> dict[str, float]:
    """Composants suivis par lot dans un produit fini, avec leur quantité (nomenclature éclatée)."""
    track = {i[0]: i[3] for i in ITEMS}
    need: dict[str, float] = {}

    def walk(parent, mult):
        for p, c, q in BOM:
            if p == parent:
                if any(x == c for x, _, _ in BOM):
                    walk(c, mult * q)
                elif track[c] == "lot":
                    need[c] = need.get(c, 0) + mult * q
    walk(item_id, 1)
    return need


def explode(item_id: str, qty: float = 1.0) -> dict[str, float]:
    """Besoin brut en composants achetés pour qty produits (éclatement multiniveau de la nomenclature)."""
    out: dict[str, float] = {}
    parents = {p for p, _, _ in BOM}

    def walk(parent, mult):
        for p, c, q in BOM:
            if p == parent:
                if c in parents:
                    walk(c, mult * q)
                else:
                    out[c] = out.get(c, 0) + mult * q
    walk(item_id, qty)
    return out
