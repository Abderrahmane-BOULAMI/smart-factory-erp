"""Construction de la base SQLite du socle ERP : schéma, données de base, flux simulés et vues d'indicateurs."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from .simulate import simulate

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "usine.db"
ORDER = ["supplier", "item", "bom_line", "workcenter", "routing_step", "location", "control_plan",
         "replenishment_rule", "purchase_order", "receipt", "inspection", "stock_move", "sales_order",
         "manufacturing_order", "shop_entry", "downtime", "serial_unit", "genealogy", "nonconformity",
         "corrective_action"]


def build(path: Path = DB, seed: int = 2027) -> Path:
    frames = simulate(seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript((ROOT / "sql" / "schema.sql").read_text(encoding="utf-8"))
    for name in ORDER:
        df = frames[name]
        cols = [c[1] for c in con.execute(f"PRAGMA table_info({name})")]
        df = df[[c for c in cols if c in df.columns]]
        try:
            df.to_sql(name, con, if_exists="append", index=False)
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"chargement de la table {name} impossible : {e}") from e
    con.executescript((ROOT / "sql" / "views.sql").read_text(encoding="utf-8"))
    con.commit()
    con.close()
    return path


def query(sql: str, path: Path = DB, params=()) -> pd.DataFrame:
    with sqlite3.connect(path) as con:
        return pd.read_sql_query(sql, con, params=params)


if __name__ == "__main__":
    p = build()
    print(p, round(p.stat().st_size / 1e6, 1), "Mo")
