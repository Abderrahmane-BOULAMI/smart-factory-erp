-- Socle ERP d'une usine d'assemblage d'électroménager (modèle indépendant de l'éditeur).
-- Quatre volets : logistique, stockage, production, qualité.

-- ============================================================ Données de base
CREATE TABLE supplier (
    supplier_id   TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    country       TEXT NOT NULL,
    lead_time_d   INTEGER NOT NULL CHECK (lead_time_d > 0),
    min_order_qty INTEGER NOT NULL CHECK (min_order_qty > 0)
);

CREATE TABLE item (
    item_id      TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    item_type    TEXT NOT NULL CHECK (item_type IN ('composant', 'sous-ensemble', 'produit fini', 'emballage')),
    unit         TEXT NOT NULL DEFAULT 'pce',
    tracking     TEXT NOT NULL CHECK (tracking IN ('aucun', 'lot', 'série')),
    supplier_id  TEXT REFERENCES supplier(supplier_id),
    unit_cost    REAL NOT NULL CHECK (unit_cost >= 0),
    critical     INTEGER NOT NULL DEFAULT 0,      -- 1 = contrôle à réception renforcé
    repairable   INTEGER NOT NULL DEFAULT 0       -- 1 = pièce détachée vendue au réparateur
);

CREATE TABLE bom_line (                           -- nomenclature : parent -> composant
    parent_id    TEXT NOT NULL REFERENCES item(item_id),
    component_id TEXT NOT NULL REFERENCES item(item_id),
    qty          REAL NOT NULL CHECK (qty > 0),
    PRIMARY KEY (parent_id, component_id)
);

CREATE TABLE workcenter (
    wc_id         TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    hours_per_day REAL NOT NULL CHECK (hours_per_day > 0)
);

CREATE TABLE routing_step (                       -- gamme : opérations d'un article fabriqué
    item_id       TEXT NOT NULL REFERENCES item(item_id),
    seq           INTEGER NOT NULL,
    wc_id         TEXT NOT NULL REFERENCES workcenter(wc_id),
    operation     TEXT NOT NULL,
    std_time_s    REAL NOT NULL CHECK (std_time_s > 0),
    control_point TEXT,                           -- point de contrôle en-cours éventuel
    PRIMARY KEY (item_id, seq)
);

CREATE TABLE location (
    loc_code  TEXT PRIMARY KEY,                   -- code-barres de l'emplacement
    zone      TEXT NOT NULL CHECK (zone IN ('réception', 'contrôle', 'stock', 'bord de ligne', 'quarantaine',
                                            'produits finis', 'expédition', 'pièces détachées')),
    capacity  INTEGER NOT NULL CHECK (capacity > 0)
);

CREATE TABLE control_plan (                       -- plans de contrôle : réception, en-cours, final
    plan_id     TEXT PRIMARY KEY,
    stage       TEXT NOT NULL CHECK (stage IN ('réception', 'en-cours', 'final')),
    item_id     TEXT NOT NULL REFERENCES item(item_id),
    characteristic TEXT NOT NULL,
    lsl         REAL,
    usl         REAL,
    unit        TEXT,
    sample_size INTEGER NOT NULL CHECK (sample_size > 0)
);

CREATE TABLE replenishment_rule (
    item_id       TEXT PRIMARY KEY REFERENCES item(item_id),
    reorder_point INTEGER NOT NULL,
    order_qty     INTEGER NOT NULL,
    safety_stock  INTEGER NOT NULL,
    home_loc      TEXT REFERENCES location(loc_code)
);

-- ============================================================ Flux
CREATE TABLE purchase_order (
    po_id        TEXT PRIMARY KEY,
    supplier_id  TEXT NOT NULL REFERENCES supplier(supplier_id),
    item_id      TEXT NOT NULL REFERENCES item(item_id),
    qty          INTEGER NOT NULL,
    order_day    INTEGER NOT NULL,
    due_day      INTEGER NOT NULL
);

CREATE TABLE receipt (                            -- réception : un lot fournisseur
    lot_id       TEXT PRIMARY KEY,
    po_id        TEXT NOT NULL REFERENCES purchase_order(po_id),
    item_id      TEXT NOT NULL REFERENCES item(item_id),
    qty          INTEGER NOT NULL,
    day          INTEGER NOT NULL,
    status       TEXT NOT NULL CHECK (status IN ('accepté', 'quarantaine', 'refusé')),
    loc_code     TEXT REFERENCES location(loc_code)
);

CREATE TABLE inspection (                         -- résultats de contrôle (réception, en-cours, final)
    insp_id      INTEGER PRIMARY KEY,
    plan_id      TEXT NOT NULL REFERENCES control_plan(plan_id),
    ref          TEXT NOT NULL,                   -- lot ou numéro de série contrôlé
    day          INTEGER NOT NULL,
    value        REAL NOT NULL,
    ok           INTEGER NOT NULL
);

CREATE TABLE stock_move (
    move_id      INTEGER PRIMARY KEY,
    day          INTEGER NOT NULL,
    item_id      TEXT NOT NULL REFERENCES item(item_id),
    lot_id       TEXT,
    qty          INTEGER NOT NULL,                -- positif = entrée, négatif = sortie
    from_loc     TEXT,
    to_loc       TEXT,
    reason       TEXT NOT NULL
);

CREATE TABLE sales_order (
    so_id        TEXT PRIMARY KEY,
    customer     TEXT NOT NULL,
    item_id      TEXT NOT NULL REFERENCES item(item_id),
    qty          INTEGER NOT NULL,
    order_day    INTEGER NOT NULL,
    due_day      INTEGER NOT NULL,
    shipped_day  INTEGER,
    shipped_qty  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE manufacturing_order (
    mo_id        TEXT PRIMARY KEY,
    item_id      TEXT NOT NULL REFERENCES item(item_id),
    qty          INTEGER NOT NULL,
    day          INTEGER NOT NULL,
    status       TEXT NOT NULL
);

CREATE TABLE shop_entry (                         -- saisie atelier par poste et par jour
    entry_id     INTEGER PRIMARY KEY,
    mo_id        TEXT NOT NULL REFERENCES manufacturing_order(mo_id),
    wc_id        TEXT NOT NULL REFERENCES workcenter(wc_id),
    day          INTEGER NOT NULL,
    planned_s    REAL NOT NULL,                   -- temps d'ouverture
    downtime_s   REAL NOT NULL,                   -- arrêts
    run_s        REAL NOT NULL,                   -- temps de marche
    good_qty     INTEGER NOT NULL,
    scrap_qty    INTEGER NOT NULL
);

CREATE TABLE downtime (
    dt_id        INTEGER PRIMARY KEY,
    wc_id        TEXT NOT NULL REFERENCES workcenter(wc_id),
    day          INTEGER NOT NULL,
    cause        TEXT NOT NULL,
    duration_s   REAL NOT NULL
);

CREATE TABLE serial_unit (                        -- produit fini identifié par numéro de série
    serial_no    TEXT PRIMARY KEY,
    item_id      TEXT NOT NULL REFERENCES item(item_id),
    mo_id        TEXT NOT NULL REFERENCES manufacturing_order(mo_id),
    day          INTEGER NOT NULL,
    status       TEXT NOT NULL CHECK (status IN ('conforme', 'rebut', 'retouché', 'expédié')),
    so_id        TEXT REFERENCES sales_order(so_id)
);

CREATE TABLE genealogy (                          -- traçabilité : quel lot dans quel numéro de série
    serial_no    TEXT NOT NULL REFERENCES serial_unit(serial_no),
    item_id      TEXT NOT NULL REFERENCES item(item_id),
    lot_id       TEXT NOT NULL REFERENCES receipt(lot_id),
    qty          REAL NOT NULL
);

CREATE TABLE nonconformity (
    nc_id        TEXT PRIMARY KEY,
    day          INTEGER NOT NULL,
    stage        TEXT NOT NULL,
    ref          TEXT NOT NULL,
    item_id      TEXT NOT NULL,
    defect       TEXT NOT NULL,
    cause        TEXT NOT NULL,
    disposition  TEXT NOT NULL,
    status       TEXT NOT NULL
);

CREATE TABLE corrective_action (                  -- 8D
    ca_id        TEXT PRIMARY KEY,
    title        TEXT NOT NULL,
    opened_day   INTEGER NOT NULL,
    d_step       TEXT NOT NULL,
    owner        TEXT NOT NULL,
    content      TEXT NOT NULL
);

-- ============================================================ Index des requêtes fréquentes
CREATE INDEX ix_stock_move_item_day ON stock_move (item_id, day);
CREATE INDEX ix_genealogy_lot ON genealogy (lot_id);
CREATE INDEX ix_genealogy_serial ON genealogy (serial_no);
CREATE INDEX ix_inspection_ref ON inspection (ref);
CREATE INDEX ix_inspection_plan_day ON inspection (plan_id, day);
CREATE INDEX ix_shop_entry_wc_day ON shop_entry (wc_id, day);
