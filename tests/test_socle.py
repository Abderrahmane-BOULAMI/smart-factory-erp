"""Tests du socle : contrôles des données de base, nomenclature, cohérence de la base simulée et des indicateurs."""
from __future__ import annotations

import sqlite3

import pytest

from sfe import checks, kpi, replenish
from sfe import masterdata as md
from sfe.db import DB, build


@pytest.fixture(scope="session", autouse=True)
def base():
    if not DB.exists():
        build()
    return DB


def master(**over):
    rules = replenish.build_rules({"PF-M1": 140, "PF-M1P": 60})
    data = dict(items=list(md.ITEMS), bom=list(md.BOM), routing=list(md.ROUTING), workcenters=list(md.WORKCENTERS),
                suppliers=list(md.SUPPLIERS), locations=md.locations(), plans=list(md.CONTROL_PLANS), rules=rules)
    data.update(over)
    return data


def rules_of(issues):
    return {(i.rule, i.obj) for i in issues}


# --------------------------------------------------------------------------- données de base
def test_donnees_de_reference_sans_anomalie():
    assert checks.check(**master()) == []


def test_detecte_fournisseur_manquant():
    items = [(*i[:4], None, *i[5:]) if i[0] == "ROU-608" else i for i in md.ITEMS]
    assert ("Fournisseur manquant", "ROU-608") in rules_of(checks.check(**master(items=items)))


def test_detecte_cycle_de_nomenclature():
    bom = list(md.BOM) + [("SE-MOT", "PF-M1", 1)]
    assert ("Nomenclature", "PF-M1") in rules_of(checks.check(**master(bom=bom)))


def test_detecte_emplacement_mal_code():
    locs = md.locations() + [("stk a1", "stock", 4)]
    assert ("Emplacement", "stk a1") in rules_of(checks.check(**master(locations=locs)))


def test_detecte_composant_critique_non_trace():
    items = [(*i[:3], "aucun", *i[4:]) if i[0] == "MOT-650" else i for i in md.ITEMS]
    assert ("Traçabilité", "MOT-650") in rules_of(checks.check(**master(items=items)))


def test_detecte_regle_de_reappro_absente():
    rules = [r for r in master()["rules"] if r[0] != "VIS-M4"]
    assert ("Réapprovisionnement", "VIS-M4") in rules_of(checks.check(**master(rules=rules)))


# --------------------------------------------------------------------------- nomenclature et réappro
def test_eclatement_multiniveau():
    need = md.explode("PF-M1", 10)
    assert need["VIS-M4"] == 80          # 4 dans le bloc moteur + 4 dans la base
    assert need["ROU-608"] == 20
    assert "CTE-IHM" not in need         # carte écran réservée au M1 Plus
    assert md.explode("PF-M1P", 1)["CTE-IHM"] == 1


def test_point_de_commande_couvre_le_delai():
    use = replenish.daily_usage({"PF-M1": 140, "PF-M1P": 60})
    lead = {s[0]: s[3] for s in md.SUPPLIERS}
    sup = {i[0]: i[4] for i in md.ITEMS}
    for item, rop, qty, ss, _ in replenish.build_rules({"PF-M1": 140, "PF-M1P": 60}):
        assert rop >= use[item] * lead[sup[item]] + ss - 1
        assert ss > 0 and qty > 0


# --------------------------------------------------------------------------- cohérence de la base simulée
def q(sql):
    with sqlite3.connect(DB) as c:
        return c.execute(sql).fetchall()


def test_pas_de_stock_negatif():
    assert q("SELECT COUNT(*) FROM v_stock_jour WHERE stock < 0")[0][0] == 0


def test_chaque_serie_a_sa_genealogie_complete():
    expected = {pf: len(md.tracked_components(pf)) for pf in ("PF-M1", "PF-M1P")}
    rows = q("""SELECT su.item_id, COUNT(DISTINCT g.item_id) FROM serial_unit su
                LEFT JOIN genealogy g USING (serial_no) GROUP BY su.serial_no""")
    assert rows and all(n == expected[pf] for pf, n in rows)


def test_lot_rappele_rattache_a_des_series_reelles():
    t = kpi.trace_lot("L-ROU-608-2201")
    assert len(t) > 0
    assert set(t["numéro de série"]) <= {r[0] for r in q("SELECT serial_no FROM serial_unit")}


def test_integrite_referentielle():
    with sqlite3.connect(DB) as c:
        assert c.execute("PRAGMA foreign_key_check").fetchall() == []


# --------------------------------------------------------------------------- indicateurs
def test_indicateurs_bornes():
    t = kpi.trs_week()
    for col in ("disponibilité", "performance", "qualité", "TRS"):
        assert t[col].between(0, 1.0001).all(), col
    s = kpi.service_week()
    assert s["respect des délais"].between(0, 1).all()


def test_montee_en_cadence_visible():
    h = kpi.headline()
    assert h["trs_last"] > h["trs_first"]
    assert h["scrap_last"] < h["scrap_first"]
    assert h["expédiés"] <= h["produits"]


def test_carte_p_signale_le_lot_defectueux():
    p = kpi.p_chart()
    assert p[p["hors contrôle"]].day.min() >= 20
