"""Indicateurs de pilotage (vues atelier et direction) et requêtes de traçabilité, lus dans la base SQLite."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .db import query

BOTTLENECK = "WC-ASM"   # le TRS de la ligne est celui du poste goulot


def week(day: pd.Series) -> pd.Series:
    return (day - 1) // 5 + 1


def trs_line_day() -> pd.DataFrame:
    df = query("SELECT * FROM v_trs_poste_jour WHERE wc_id = ?", params=(BOTTLENECK,))
    return df.fillna({"qualite": 1.0})


def trs_week() -> pd.DataFrame:
    d = query("""SELECT se.day, SUM(se.planned_s) ouv, SUM(se.run_s) run,
                        SUM((se.good_qty + se.scrap_qty) * rs.std_time_s) prod_std, SUM(se.good_qty * rs.std_time_s) bon_std
                 FROM shop_entry se JOIN manufacturing_order mo ON mo.mo_id = se.mo_id
                 JOIN routing_step rs ON rs.item_id = mo.item_id AND rs.wc_id = se.wc_id
                 WHERE se.wc_id = ? GROUP BY se.day""", params=(BOTTLENECK,))
    d["semaine"] = week(d.day)
    w = d.groupby("semaine")[["ouv", "run", "prod_std", "bon_std"]].sum()
    w["disponibilité"] = w.run / w.ouv
    w["performance"] = w.prod_std / w.run
    w["qualité"] = w.bon_std / w.prod_std
    w["TRS"] = w.bon_std / w.ouv
    return w.reset_index()


def service_week() -> pd.DataFrame:
    s = query("SELECT * FROM v_service_jour")
    s["semaine"] = week(s.day)
    w = s.groupby("semaine")[["commandes", "a_l_heure", "qte_due", "qte_a_l_heure"]].sum()
    w["respect des délais"] = w.a_l_heure / w.commandes
    w["taux de service"] = w.qte_a_l_heure / w.qte_due
    return w.reset_index()


def quality_week() -> pd.DataFrame:
    q = query("SELECT * FROM v_qualite_jour")
    q["semaine"] = week(q.day)
    nc = query("SELECT day, COUNT(*) n FROM nonconformity WHERE stage IN ('en-cours','final') GROUP BY day")
    q = q.merge(nc, on="day", how="left").fillna({"n": 0})
    w = q.groupby("semaine")[["produits", "rebuts", "n"]].sum()
    w["taux de rebut"] = w.rebuts / w.produits
    w["rendement 1er passage"] = 1 - w.n / w.produits
    return w.reset_index()


def headline() -> dict:
    t, s, q = trs_week(), service_week(), quality_week()
    units = query("SELECT COUNT(*) n, SUM(status = 'expédié') exp FROM serial_unit").iloc[0]
    return {
        "trs_first": t.TRS.iloc[0], "trs_last": t.TRS.iloc[-1],
        "otd_first": s["respect des délais"].iloc[1], "otd_last": s["respect des délais"].iloc[-1],
        "scrap_last": q["taux de rebut"].iloc[-1], "scrap_first": q["taux de rebut"].iloc[0],
        "service_last": s["taux de service"].iloc[-1],
        "produits": int(units.n), "expédiés": int(units.exp),
    }


def losses(day_from: int = 1, day_to: int = 40) -> pd.DataFrame:
    """Décomposition du temps d'ouverture du goulot : où passe le temps perdu."""
    d = query("""SELECT SUM(se.planned_s) ouv, SUM(se.planned_s - se.run_s) arrets,
                        SUM(se.run_s) - SUM((se.good_qty + se.scrap_qty) * rs.std_time_s) ralentissements,
                        SUM(se.scrap_qty * rs.std_time_s) non_qualite, SUM(se.good_qty * rs.std_time_s) utile
                 FROM shop_entry se JOIN manufacturing_order mo ON mo.mo_id = se.mo_id
                 JOIN routing_step rs ON rs.item_id = mo.item_id AND rs.wc_id = se.wc_id
                 WHERE se.wc_id = ? AND se.day BETWEEN ? AND ?""", params=(BOTTLENECK, day_from, day_to)).iloc[0]
    return pd.DataFrame({"poste": ["Temps d'ouverture", "Arrêts", "Ralentissements", "Non-qualité", "Temps utile"],
                         "heures": [d.ouv / 3600, -d.arrets / 3600, -d.ralentissements / 3600,
                                    -d.non_qualite / 3600, d.utile / 3600]})


def downtime_pareto(day_from: int = 1, day_to: int = 40, wc: str | None = None) -> pd.DataFrame:
    sql = "SELECT cause, SUM(duration_s)/3600.0 heures FROM downtime WHERE day BETWEEN ? AND ?"
    params = [day_from, day_to]
    if wc:
        sql += " AND wc_id = ?"
        params.append(wc)
    d = query(sql + " GROUP BY cause ORDER BY heures DESC", params=tuple(params))
    d["cumul %"] = 100 * d.heures.cumsum() / d.heures.sum()
    return d


def nc_pareto(stage: tuple = ("en-cours", "final")) -> pd.DataFrame:
    marks = ",".join("?" * len(stage))
    d = query(f"SELECT defect, COUNT(*) n FROM nonconformity WHERE stage IN ({marks}) GROUP BY defect "
              "ORDER BY n DESC", params=stage)
    d["cumul %"] = 100 * d.n.cumsum() / d.n.sum()
    return d


def p_chart() -> pd.DataFrame:
    """Carte p du taux de refus au test final, limites calculées sur les 15 premiers jours stabilisés."""
    d = query("""SELECT day, COUNT(DISTINCT ref) n, COUNT(DISTINCT CASE WHEN ok = 0 THEN ref END) refus
                 FROM inspection WHERE plan_id LIKE 'CP-F-%' GROUP BY day ORDER BY day""")
    d["p"] = d.refus / d.n
    base = d[(d.day >= 6) & (d.day <= 20)]
    pbar = base.refus.sum() / base.n.sum()
    d["LC"] = pbar
    d["LSC"] = pbar + 3 * np.sqrt(pbar * (1 - pbar) / d.n)
    d["hors contrôle"] = d.p > d.LSC
    return d


def noise_by_day() -> pd.DataFrame:
    return query("""SELECT day, AVG(value) moyenne, MAX(value) maxi,
                           SUM(value > 82.0) au_dessus_limite FROM inspection
                    WHERE plan_id = 'CP-F-BRU' GROUP BY day ORDER BY day""")


def stock_item(item: str) -> pd.DataFrame:
    s = query("SELECT day, stock FROM v_stock_jour WHERE item_id = ? ORDER BY day", params=(item,))
    po = query("""SELECT po.order_day, COALESCE(MIN(r.day), 99) recu, po.qty FROM purchase_order po
                  LEFT JOIN receipt r ON r.po_id = po.po_id WHERE po.item_id = ? GROUP BY po.po_id""", params=(item,))
    s["position (stock + en commande)"] = [st + po[(po.order_day <= d) & (po.recu > d)].qty.sum()
                                           for d, st in zip(s.day, s.stock, strict=True)]
    r = query("SELECT * FROM replenishment_rule WHERE item_id = ?", params=(item,))
    if not r.empty:
        s["point de commande"] = r.reorder_point.iloc[0]
        s["stock de sécurité"] = r.safety_stock.iloc[0]
    return s


def coverage(day: int = 40) -> pd.DataFrame:
    """Couverture du stock en jours de consommation moyenne des 10 derniers jours."""
    s = query("SELECT item_id, stock FROM v_stock_jour WHERE day = ?", params=(day,))
    c = query("""SELECT item_id, -SUM(qty) / 10.0 conso FROM stock_move WHERE reason = 'consommation OF'
                 AND day > ? GROUP BY item_id""", params=(day - 10,))
    d = s.merge(c, on="item_id").merge(query("SELECT item_id, name, reorder_point, safety_stock FROM item "
                                             "JOIN replenishment_rule USING (item_id)"), on="item_id")
    d["couverture (jours)"] = d.stock / d.conso
    return d.sort_values("couverture (jours)")


def trace_serial(serial: str) -> pd.DataFrame:
    return query("""SELECT g.item_id composant, i.name désignation, g.lot_id lot, g.qty qté, r.day "jour réception",
                           s.name fournisseur, r.status "statut lot"
                    FROM genealogy g JOIN item i USING (item_id) JOIN receipt r ON r.lot_id = g.lot_id
                    JOIN purchase_order po ON po.po_id = r.po_id JOIN supplier s ON s.supplier_id = po.supplier_id
                    WHERE g.serial_no = ? ORDER BY g.item_id""", params=(serial,))


def trace_lot(lot: str) -> pd.DataFrame:
    return query("""SELECT DISTINCT serial_no "numéro de série", produit, jour_fabrication "jour de fabrication",
                           status statut, CASE WHEN status = 'rebut' THEN 'rebuté à l''usine' ELSE COALESCE(customer, 'en stock usine') END destination,
                           shipped_day "jour d'expédition"
                    FROM v_tracabilite WHERE lot_id = ? ORDER BY serial_no""", params=(lot,))


def serial_info(serial: str) -> pd.DataFrame:
    return query("""SELECT su.serial_no, su.item_id, i.name, su.day, su.status, su.mo_id, so.customer, so.shipped_day
                    FROM serial_unit su JOIN item i USING (item_id) LEFT JOIN sales_order so ON so.so_id = su.so_id
                    WHERE su.serial_no = ?""", params=(serial,))


def serial_tests(serial: str) -> pd.DataFrame:
    return query("""SELECT cp.stage étape, cp.characteristic caractéristique, ROUND(ins.value, 2) valeur,
                           COALESCE(CAST(cp.lsl AS TEXT), '') LSL, COALESCE(CAST(cp.usl AS TEXT), '') USL,
                           cp.unit unité, CASE ins.ok WHEN 1 THEN 'conforme' ELSE 'non conforme' END résultat
                    FROM inspection ins JOIN control_plan cp USING (plan_id) WHERE ins.ref = ?""", params=(serial,))
