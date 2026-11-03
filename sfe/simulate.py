"""Simulation des 8 premières semaines d'exploitation de l'usine (40 jours ouvrés), alimentant le socle ERP.

Montée en cadence de la ligne, réceptions avec contrôle, consommation des lots en FIFO, saisies atelier, test final,
expéditions. Deux incidents réalistes sont injectés pour montrer à quoi servent la traçabilité et la qualité :
  - jour 12 : un lot de cartes de puissance échoue au contrôle à réception et part en quarantaine ;
  - jour 20 : un lot de roulements légèrement hors tolérance passe l'échantillonnage, fait monter le bruit au test
    final, puis est retrouvé par la traçabilité et bloqué (8D).
Toutes les données sont générées : aucune donnée réelle d'entreprise n'est utilisée.
"""
from __future__ import annotations

import math
from collections import defaultdict, deque
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import masterdata as md
from . import replenish

DAYS = 40
SHIFT_S = 7.5 * 3600
PRODUCTS = ("PF-M1", "PF-M1P")
MIX = {"PF-M1": 0.7, "PF-M1P": 0.3}
DT_CAUSES = {
    "WC-PRE": ["Réglage visseuse", "Micro-arrêts", "Attente composant bord de ligne"],
    "WC-ASM": ["Micro-arrêts", "Changement de série", "Attente composant bord de ligne", "Réglage outillage"],
    "WC-TST": ["Panne banc de test", "Étalonnage banc", "Micro-arrêts"],
    "WC-EMB": ["Micro-arrêts", "Bourrage étiqueteuse"],
}
ASM_DEFECTS = ["Joint de bol mal positionné", "Vis foirée", "Rayure sur la base", "Clip de capot cassé"]
BAD_PWR_DAY, BAD_ROU_DAY = 12, 17
NOISE_ALERT = 12   # refus « bruit » cumulés qui déclenchent l'ouverture du 8D


def ramp(day: int, start: float, end: float, k: float = 3.5) -> float:
    x = (day - 1) / (DAYS - 1)
    return start + (end - start) * (1 - math.exp(-k * x))


@dataclass
class Factory:
    seed: int = 2027
    rng: np.random.Generator = field(init=False)
    t: dict = field(default_factory=lambda: defaultdict(list))

    def __post_init__(self):
        self.rng = np.random.default_rng(self.seed)
        self.items = {i[0]: i for i in md.ITEMS}
        self.sup = {s[0]: s for s in md.SUPPLIERS}
        self.purchased = [i[0] for i in md.ITEMS if i[2] in ("composant", "emballage")]
        self.std = {(r[0], r[2]): r[4] for r in md.ROUTING}
        self.plans = {(p[1], p[2]): p for p in md.CONTROL_PLANS}
        plan_ref = {pf: 200 * MIX[pf] for pf in PRODUCTS}          # cadence cible : 200 mixeurs par jour
        self.rules = {r[0]: r for r in replenish.build_rules(plan_ref)}
        self.lots: dict[str, deque] = defaultdict(deque)            # lots acceptés, consommés en FIFO
        self.untracked: dict[str, float] = defaultdict(float)
        self.on_order: dict[str, float] = defaultdict(float)
        self.open_po: list[tuple] = []
        self.fg: dict[str, deque] = defaultdict(deque)              # numéros de série conformes en stock
        self.counters = defaultdict(int)
        self.bad_lots: set[str] = set()
        self.quarantined: set[str] = set()
        self.cons: dict = defaultdict(float)
        self.serials: dict = {}
        self.flags: set[str] = set()
        self.contain_day = None
        self.noise_fails = 0
        self.first_noise = None

    # ----------------------------------------------------------- utilitaires
    def nid(self, prefix):
        self.counters[prefix] += 1
        return f"{prefix}-{self.counters[prefix]:05d}"

    def move(self, day, item, lot, qty, src, dst, reason):
        self.t["stock_move"].append(dict(day=day, item_id=item, lot_id=lot, qty=qty, from_loc=src, to_loc=dst,
                                         reason=reason))

    def stock(self, item):
        if self.items[item][3] == "lot":
            return sum(q for _, q in self.lots[item])
        return self.untracked[item]

    # ----------------------------------------------------------- achats et réceptions
    def order(self, day, item, qty):
        sup = self.items[item][4]
        lt = self.sup[sup][3]
        po = self.nid("PO")
        late = int(self.rng.random() < 0.1) * int(self.rng.integers(1, 4))
        self.t["purchase_order"].append(dict(po_id=po, supplier_id=sup, item_id=item, qty=qty, order_day=day,
                                             due_day=day + lt))
        self.open_po.append((day + lt + late, po, item, qty))
        self.on_order[item] += qty

    def receive(self, day, po, item, qty):
        self.on_order[item] -= qty
        lot = f"L-{item}-{day:02d}{self.counters['lot_' + item]:02d}"
        self.counters["lot_" + item] += 1
        status, loc = "accepté", self.rules[item][4]
        plan = self.plans.get(("réception", item))
        incident = None
        if item == "CTE-PWR" and day >= BAD_PWR_DAY and "pwr" not in self.flags:
            incident = "pwr"
        if item == "ROU-608" and day >= BAD_ROU_DAY and "rou" not in self.flags:
            incident = "rou"
        if incident:
            self.flags.add(incident)
        if plan:
            ok_all = True
            for k in range(plan[7]):
                v, ok = self.measure_reception(item, plan, incident, k)
                self.t["inspection"].append(dict(plan_id=plan[0], ref=lot, day=day, value=round(v, 3), ok=int(ok)))
                ok_all &= ok
            if not ok_all:
                status, loc = "quarantaine", "QUA-01"
                self.t["nonconformity"].append(dict(
                    nc_id=self.nid("NC"), day=day, stage="réception", ref=lot, item_id=item,
                    defect="Échec au contrôle à réception", cause="Fournisseur", disposition="Retour fournisseur",
                    status="clôturée"))
        self.t["receipt"].append(dict(lot_id=lot, po_id=po, item_id=item, qty=qty, day=day, status=status,
                                      loc_code=loc))
        self.move(day, item, lot if self.items[item][3] == "lot" else None, qty, "REC-01", loc, "réception")
        if status == "accepté":
            if self.items[item][3] == "lot":
                self.lots[item].append([lot, qty])
                if incident == "rou":
                    self.bad_lots.add(lot)
            else:
                self.untracked[item] += qty
        else:
            self.quarantined.add(lot)
            self.open_po.append((day + 3, po, item, qty))           # lot de remplacement sous 3 jours
            self.on_order[item] += qty

    def measure_reception(self, item, plan, incident, k):
        if incident == "pwr":
            ok = k not in (1, 3)                       # 2 cartes sur 5 échouent : lot refusé
            return float(ok), ok
        if plan[6] == "ok":
            return 1.0, True
        if item == "ROU-608":
            if incident == "rou":                       # proche de la limite : l'échantillon passe quand même
                v = min(19.6, self.rng.normal(17.6, 0.8))
            else:
                v = self.rng.normal(13.5, 1.6)
            return v, v <= plan[5]
        if item == "MOT-650":
            v = self.rng.normal(1.1, 0.07)
            return v, plan[4] <= v <= plan[5]
        return 1.0, True

    # ----------------------------------------------------------- consommation
    def available(self, pf, n):
        need = md.explode(pf, 1)
        return min(int(self.stock(c) // q) for c, q in need.items())

    def consume(self, day, pf, serial, mo):
        bad_bearing = False
        for c, q in md.explode(pf, 1).items():
            if self.items[c][3] == "lot":
                left = q
                while left > 0:
                    lot = self.lots[c][0]
                    take = min(left, lot[1])
                    lot[1] -= take
                    left -= take
                    self.t["genealogy"].append(dict(serial_no=serial, item_id=c, lot_id=lot[0], qty=take))
                    self.cons[(day, c, lot[0])] += take
                    if lot[0] in self.bad_lots:
                        bad_bearing = True
                    if lot[1] == 0:
                        self.lots[c].popleft()
            else:
                self.untracked[c] -= q
                self.cons[(day, c, None)] += q
        return bad_bearing

    # ----------------------------------------------------------- une journée
    def run_day(self, day):
        rng = self.rng
        for _due, po, item, qty in [p for p in self.open_po if p[0] == day]:
            self.receive(day, po, item, qty)
        self.open_po = [p for p in self.open_po if p[0] != day]

        if day == self.contain_day:                                  # 8D : confinement du lot de roulements
            for c, dq in self.lots.items():
                for lot in list(dq):
                    if lot[0] in self.bad_lots:
                        self.move(day, c, lot[0], -lot[1], self.rules[c][4], "QUA-01", "mise en quarantaine")
                        self.quarantined.add(lot[0])
                        dq.remove(lot)
                        po = self.nid("PO")
                        self.t["purchase_order"].append(dict(po_id=po, supplier_id=self.items[c][4], item_id=c,
                                                             qty=int(lot[1]), order_day=day, due_day=day + 1))
                        self.open_po.append((day + 1, po, c, int(lot[1])))
                        self.on_order[c] += int(lot[1])
            for r in self.t["receipt"]:
                if r["lot_id"] in self.bad_lots:
                    r["status"] = "quarantaine"
                    r["loc_code"] = "QUA-01"
            self.bad_lots_contained = True

        # nouvelles commandes clients (jour 1 : précommandes de lancement du distributeur)
        if day == 1:
            for pf, q in (("PF-M1", 560), ("PF-M1P", 240)):
                self.t["sales_order"].append(dict(so_id=self.nid("CC"), customer="Distributeur électroménager",
                                                  item_id=pf, qty=q, order_day=day, due_day=6, shipped_day=None,
                                                  shipped_qty=0))
        demand = ramp(day, 135, 195, 2.0) * rng.uniform(0.85, 1.15)
        for cust, share, lead in (("Distributeur électroménager", 0.55, 8), ("Boutique en ligne", 0.35, 2),
                                  ("Réseau de réparateurs", 0.10, 5)):
            for pf in PRODUCTS:
                q = int(round(demand * share * MIX[pf] * rng.uniform(0.8, 1.2)))
                if q > 0 and (cust != "Distributeur électroménager" or day % 2 == 1):
                    q = q * 2 if cust == "Distributeur électroménager" else q
                    self.t["sales_order"].append(dict(so_id=self.nid("CC"), customer=cust, item_id=pf, qty=q,
                                                      order_day=day, due_day=day + lead, shipped_day=None,
                                                      shipped_qty=0))

        # performance de la ligne pendant la montée en cadence
        perf = min(0.97, ramp(day, 0.56, 0.90) + rng.normal(0, 0.025))
        fpy_asm = min(0.995, ramp(day, 0.935, 0.988) + rng.normal(0, 0.004))
        downtime = {}
        for wc in md.WORKCENTERS:
            avail = min(0.97, ramp(day, 0.80, 0.93) + rng.normal(0, 0.02))
            if wc[0] == "WC-TST" and rng.random() < 0.08:
                avail -= 0.10
            total = SHIFT_S * (1 - avail)
            causes = DT_CAUSES[wc[0]]
            w = rng.dirichlet(np.ones(len(causes)))
            downtime[wc[0]] = {c: total * x for c, x in zip(causes, w, strict=True)}
        asm_run = SHIFT_S - sum(downtime["WC-ASM"].values())
        mean_std = sum(MIX[pf] * self.std[(pf, "WC-ASM")] for pf in PRODUCTS)
        capacity = int(asm_run * perf / mean_std)

        made = {}
        for pf in PRODUCTS:
            target = int(round(capacity * MIX[pf]))
            n = min(target, self.available(pf, target))
            if n < target:                                           # rupture : arrêt pour manque composant
                lost = (target - n) * self.std[(pf, "WC-ASM")] / perf
                downtime["WC-ASM"]["Manque composant"] = downtime["WC-ASM"].get("Manque composant", 0) + lost
            made[pf] = n
            mo = self.nid("OF")
            self.t["manufacturing_order"].append(dict(mo_id=mo, item_id=pf, qty=n, day=day,
                                                      status="clôturé" if n else "suspendu (rupture)"))
            scrap = defaultdict(int)
            for _ in range(n):
                serial = f"{'M1P' if pf == 'PF-M1P' else 'M1'}-{self.nid('SN')[3:]}"
                bad = self.consume(day, pf, serial, mo)
                self.t["inspection"].append(dict(plan_id="CP-E-CPL", ref=serial, day=day,
                                                 value=round(rng.normal(1.2, 0.045), 3), ok=1))
                status = "conforme"
                if rng.random() > fpy_asm:
                    status = "rebut"
                    scrap["WC-ASM"] += 1
                    self.nc(day, "en-cours", serial, pf, str(rng.choice(ASM_DEFECTS)), "Assemblage", "Rebut")
                else:
                    cur = rng.normal(2.80, 0.10)
                    noise = rng.normal(73.5, 1.9) + (rng.normal(9.5, 1.5) if bad and rng.random() < 0.55 else 0)
                    die = rng.random() > 0.002
                    for pid, v, ok in (("CP-F-CUR", cur, 2.4 <= cur <= 3.2), ("CP-F-BRU", noise, noise <= 82.0),
                                       ("CP-F-DIE", float(die), die)):
                        self.t["inspection"].append(dict(plan_id=pid, ref=serial, day=day, value=round(v, 3),
                                                         ok=int(ok)))
                    if noise > 82.0 and bad:
                        self.noise_fails += 1
                        self.first_noise = self.first_noise or day
                    if noise > 82.0 or not die or not (2.4 <= cur <= 3.2):
                        scrap["WC-TST"] += 1
                        defect = ("Bruit excessif" if noise > 82.0 else
                                  "Échec rigidité diélectrique" if not die else "Courant hors tolérance")
                        cause = "Roulement (jeu radial)" if noise > 82.0 and bad else (
                            "Moteur" if defect == "Courant hors tolérance" else "Assemblage")
                        rework = defect == "Bruit excessif" and rng.random() < 0.8
                        status = "retouché" if rework else "rebut"
                        self.nc(day, "final", serial, pf, defect, cause, "Retouche" if rework else "Rebut")
                rec = dict(serial_no=serial, item_id=pf, mo_id=mo, day=day, status=status, so_id=None)
                self.t["serial_unit"].append(rec)
                self.serials[serial] = rec
                if status in ("conforme", "retouché"):
                    self.fg[pf].append(serial)
                    self.move(day, pf, serial, 1, "WC-EMB", "PFI-01", "déclaration de production")
            self.t["_made"].append(dict(day=day, item_id=pf, mo_id=mo, qty=n, scrap_asm=scrap["WC-ASM"],
                                        scrap_tst=scrap["WC-TST"]))

        if self.contain_day is None and self.noise_fails >= NOISE_ALERT:
            self.contain_day = day + 1                               # alerte qualité : confinement le lendemain

        # saisies atelier par poste (une ligne par poste et par OF)
        total_made = sum(made.values()) or 1
        for row in [r for r in self.t["_made"] if r["day"] == day]:
            pf, mo, n = row["item_id"], row["mo_id"], row["qty"]
            frac = n / total_made if sum(made.values()) else MIX[pf]
            passed = n
            for wc_id, _, _ in md.WORKCENTERS:
                dt = sum(downtime[wc_id].values()) * frac
                scrap_here = row["scrap_asm"] if wc_id == "WC-ASM" else row["scrap_tst"] if wc_id == "WC-TST" else 0
                self.t["shop_entry"].append(dict(mo_id=mo, wc_id=wc_id, day=day, planned_s=SHIFT_S * frac,
                                                 downtime_s=round(dt, 1), run_s=round(SHIFT_S * frac - dt, 1),
                                                 good_qty=passed - scrap_here, scrap_qty=scrap_here))
                passed -= scrap_here if wc_id == "WC-ASM" else 0
        for wc_id, causes in downtime.items():
            for cause, d in causes.items():
                self.t["downtime"].append(dict(wc_id=wc_id, day=day, cause=cause, duration_s=round(d, 1)))

        # expéditions : commandes servies par date d'échéance
        open_so = sorted([s for s in self.t["sales_order"] if s["shipped_day"] is None],
                         key=lambda s: (s["due_day"], s["so_id"]))
        for (d, c, lot), q in list(self.cons.items()):
            if d == day:
                self.move(day, c, lot, -q, self.rules[c][4], "BDL-ASM", "consommation OF")
                del self.cons[(d, c, lot)]
        units = self.serials
        for so in open_so:
            q = so["qty"] - so["shipped_qty"]
            k = min(q, len(self.fg[so["item_id"]]))
            for _ in range(k):
                sn = self.fg[so["item_id"]].popleft()
                units[sn]["status"] = "expédié"
                units[sn]["so_id"] = so["so_id"]
                self.move(day, so["item_id"], sn, -1, "PFI-01", "EXP-01", "expédition")
            so["shipped_qty"] += k
            if so["shipped_qty"] == so["qty"]:
                so["shipped_day"] = day

        # réapprovisionnement : point de commande sur la position de stock
        for item in self.purchased:
            pos = self.stock(item) + self.on_order[item]
            iid, rop, qty, _ss, _loc = self.rules[item]
            if pos <= rop:
                self.order(day, item, qty)

    def nc(self, day, stage, ref, item, defect, cause, disposition):
        self.t["nonconformity"].append(dict(nc_id=self.nid("NC"), day=day, stage=stage, ref=ref, item_id=item,
                                            defect=defect, cause=cause, disposition=disposition, status="clôturée"))

    # ----------------------------------------------------------- démarrage
    def opening_stock(self):
        """Stock initial reçu avant le démarrage (jour 0) : environ 20 jours de consommation à la cadence cible."""
        use = replenish.daily_usage({pf: 200 * MIX[pf] for pf in PRODUCTS})
        for item in self.purchased:
            qty = int(math.ceil(use[item] * 20))
            po = self.nid("PO")
            self.t["purchase_order"].append(dict(po_id=po, supplier_id=self.items[item][4], item_id=item, qty=qty,
                                                 order_day=-20, due_day=0))
            self.on_order[item] += qty
            self.receive(0, po, item, qty)
            iid, rop, oq, _ss, _loc = self.rules[item]
            if self.stock(item) <= rop:
                self.order(0, item, oq)

    def run(self) -> dict[str, pd.DataFrame]:
        self.opening_stock()
        for day in range(1, DAYS + 1):
            self.run_day(day)
        self.eight_d()
        self.t.pop("_made", None)
        return {k: pd.DataFrame(v) for k, v in self.t.items()}

    def eight_d(self):
        lot = sorted(self.bad_lots)[0] if self.bad_lots else "?"
        steps = [
            ("D1", "Responsable qualité", "Équipe : qualité, production, achats, fournisseur de roulements."),
            ("D2", "Responsable qualité", "Hausse des refus au test final pour bruit excessif à partir du jour "
                                          f"{self.first_noise}, uniquement sur les blocs moteurs."),
            ("D3", "Responsable production", f"Confinement jour {self.contain_day} : lot {lot} mis en quarantaine ; "
                                             "liste des numéros de série expédiés contenant ce lot extraite par la "
                                             "traçabilité."),
            ("D4", "Ingénieur qualité", "Cause racine : jeu radial proche de la limite haute sur le lot ; "
                                        "l'échantillon de 5 pièces à réception n'a pas détecté la dérive."),
            ("D5", "Ingénieur qualité", "Échantillon à réception porté à 13 pièces sur les roulements et limite de "
                                        "décision abaissée à 18 µm ; certificat de contrôle exigé par lot."),
            ("D6", "Responsable production", "Actions appliquées dans le plan de contrôle CP-R-ROU ; suivi du taux de "
                                             "refus bruit sur 10 jours."),
            ("D7", "Responsable qualité", "Plan de surveillance fournisseur et retour d'expérience partagé avec les "
                                          "achats."),
            ("D8", "Direction", "Clôture et remerciements à l'équipe."),
        ]
        for d, owner, txt in steps:
            self.t["corrective_action"].append(dict(ca_id=f"8D-001-{d}", title="Bruit excessif au test final",
                                                    opened_day=self.contain_day - 1, d_step=d, owner=owner, content=txt))


def master_frames(rules) -> dict[str, pd.DataFrame]:
    cols = {
        "supplier": (md.SUPPLIERS, ["supplier_id", "name", "country", "lead_time_d", "min_order_qty"]),
        "item": (md.ITEMS, ["item_id", "name", "item_type", "tracking", "supplier_id", "unit_cost", "critical",
                            "repairable"]),
        "bom_line": (md.BOM, ["parent_id", "component_id", "qty"]),
        "workcenter": (md.WORKCENTERS, ["wc_id", "name", "hours_per_day"]),
        "routing_step": (md.ROUTING, ["item_id", "seq", "wc_id", "operation", "std_time_s", "control_point"]),
        "location": (md.locations(), ["loc_code", "zone", "capacity"]),
        "control_plan": (md.CONTROL_PLANS, ["plan_id", "stage", "item_id", "characteristic", "lsl", "usl", "unit",
                                            "sample_size"]),
        "replenishment_rule": (rules, ["item_id", "reorder_point", "order_qty", "safety_stock", "home_loc"]),
    }
    return {k: pd.DataFrame(v, columns=c) for k, (v, c) in cols.items()}


def simulate(seed: int = 2027) -> dict[str, pd.DataFrame]:
    f = Factory(seed)
    flows = f.run()
    frames = master_frames(list(f.rules.values()))
    frames.update(flows)
    return frames
