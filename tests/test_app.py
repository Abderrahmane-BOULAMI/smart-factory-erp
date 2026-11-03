"""Tests de fumée du cockpit : chaque page s'exécute sans exception, y compris en changeant les filtres."""
from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app" / "app.py"
PAGES = ["page_direction", "page_atelier", "page_tracabilite", "page_qualite", "page_stock", "page_donnees",
         "page_deploiement"]


def page_script(page: str) -> str:
    """Code de l'application où la navigation est remplacée par l'appel direct d'une page."""
    src = APP.read_text(encoding="utf-8")
    head, sep, _ = src.partition("\npages = [")
    assert sep, "liste des pages introuvable dans app.py"
    return head.replace("Path(__file__)", f"Path({str(APP)!r})") + f"\n{page}()\n"


def run(page: str) -> AppTest:
    at = AppTest.from_string(page_script(page), default_timeout=120).run()
    assert not at.exception, [e.value for e in at.exception]
    return at


@pytest.mark.parametrize("page", PAGES)
def test_page_sans_erreur(page):
    run(page)


def test_atelier_toutes_les_journees():
    at = run("page_atelier")
    for day in range(1, 41):
        at.slider[0].set_value(day).run()
        assert not at.exception, (day, [e.value for e in at.exception])


def test_tracabilite_tous_les_lots():
    at = run("page_tracabilite")
    for lot in at.selectbox[0].options:
        at.selectbox[0].set_value(lot).run()
        assert not at.exception, (lot, [e.value for e in at.exception])


@pytest.mark.parametrize("serial", ["", "inconnu", "  "])
def test_tracabilite_numero_de_serie_invalide(serial):
    at = run("page_tracabilite")
    at.radio[0].set_value("Par numéro de série").run()
    at.text_input[0].input(serial).run()
    assert not at.exception, [e.value for e in at.exception]


def test_stock_tous_les_articles():
    at = run("page_stock")
    for item in at.selectbox[0].options:
        at.selectbox[0].set_value(item).run()
        assert not at.exception, (item, [e.value for e in at.exception])


def test_donnees_les_deux_nomenclatures():
    at = run("page_donnees")
    for pf in at.radio[0].options:
        at.radio[0].set_value(pf).run()
        assert not at.exception, (pf, [e.value for e in at.exception])


def test_tracabilite_numero_de_serie_saisi_en_minuscules():
    at = run("page_tracabilite")
    at.radio[0].set_value("Par numéro de série").run()
    at.text_input[0].input(" m1-00002 ").run()
    assert not at.exception and not at.warning
    assert any("rebuté" in m.value for m in at.markdown)
