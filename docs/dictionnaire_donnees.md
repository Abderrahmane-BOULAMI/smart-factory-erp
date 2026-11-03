# Dictionnaire de données

Généré depuis `sql/schema.sql` et la base simulée (`data/usine.db`). Les indicateurs sont des vues décrites dans `sql/views.sql`.

## `supplier`

Fournisseurs : délai et quantité minimale de commande. · 9 lignes

| Colonne | Type | Commentaire |
|---|---|---|
| `supplier_id` | TEXT | clé |
| `name` | TEXT | obligatoire |
| `country` | TEXT | obligatoire |
| `lead_time_d` | INTEGER | obligatoire CHECK (lead_time_d > 0) |
| `min_order_qty` | INTEGER | obligatoire CHECK (min_order_qty > 0) |

## `item`

Articles : composants, emballages, sous-ensembles, produits finis ; mode de traçabilité. · 24 lignes

| Colonne | Type | Commentaire |
|---|---|---|
| `item_id` | TEXT | clé |
| `name` | TEXT | obligatoire |
| `item_type` | TEXT | obligatoire CHECK (item_type IN ('composant', 'sous-ensemble', 'produit fini', 'emballage')) |
| `unit` | TEXT | obligatoire DEFAULT 'pce' |
| `tracking` | TEXT | obligatoire CHECK (tracking IN ('aucun', 'lot', 'série')) |
| `supplier_id` | TEXT | → supplier(supplier_id) |
| `unit_cost` | REAL | obligatoire CHECK (unit_cost >= 0) |
| `critical` | INTEGER | obligatoire DEFAULT 0 · 1 = contrôle à réception renforcé |
| `repairable` | INTEGER | obligatoire DEFAULT 0 · 1 = pièce détachée vendue au réparateur |

## `bom_line`

Nomenclature : composants d'un article fabriqué et quantité par unité. · 32 lignes

| Colonne | Type | Commentaire |
|---|---|---|
| `parent_id` | TEXT | obligatoire → item(item_id) |
| `component_id` | TEXT | obligatoire → item(item_id) |
| `qty` | REAL | obligatoire CHECK (qty > 0) |

## `workcenter`

Postes de travail et heures d'ouverture par jour. · 4 lignes

| Colonne | Type | Commentaire |
|---|---|---|
| `wc_id` | TEXT | clé |
| `name` | TEXT | obligatoire |
| `hours_per_day` | REAL | obligatoire CHECK (hours_per_day > 0) |

## `routing_step`

Gamme : opérations d'un article fabriqué, poste, temps standard. · 8 lignes

| Colonne | Type | Commentaire |
|---|---|---|
| `item_id` | TEXT | obligatoire → item(item_id) |
| `seq` | INTEGER | obligatoire |
| `wc_id` | TEXT | obligatoire → workcenter(wc_id) |
| `operation` | TEXT | obligatoire |
| `std_time_s` | REAL | obligatoire CHECK (std_time_s > 0) |
| `control_point` | TEXT | point de contrôle en-cours éventuel |

## `location`

Emplacements codifiés (code-barres), zone et capacité. · 53 lignes

| Colonne | Type | Commentaire |
|---|---|---|
| `loc_code` | TEXT | clé · code-barres de l'emplacement |
| `zone` | TEXT | obligatoire CHECK (zone IN ('réception', 'contrôle', 'stock', 'bord de ligne', 'quarantaine' |
| `capacity` | INTEGER | obligatoire CHECK (capacity > 0) |

## `control_plan`

Plans de contrôle : étape, caractéristique, limites, taille d'échantillon. · 9 lignes

| Colonne | Type | Commentaire |
|---|---|---|
| `plan_id` | TEXT | clé |
| `stage` | TEXT | obligatoire CHECK (stage IN ('réception', 'en-cours', 'final')) |
| `item_id` | TEXT | obligatoire → item(item_id) |
| `characteristic` | TEXT | obligatoire |
| `lsl` | REAL |  |
| `usl` | REAL |  |
| `unit` | TEXT |  |
| `sample_size` | INTEGER | obligatoire CHECK (sample_size > 0) |

## `replenishment_rule`

Règles de réappro : point de commande, quantité, stock de sécurité, emplacement. · 18 lignes

| Colonne | Type | Commentaire |
|---|---|---|
| `item_id` | TEXT | clé → item(item_id) |
| `reorder_point` | INTEGER | obligatoire |
| `order_qty` | INTEGER | obligatoire |
| `safety_stock` | INTEGER | obligatoire |
| `home_loc` | TEXT | → location(loc_code) |

## `purchase_order`

Commandes fournisseurs. · 76 lignes

| Colonne | Type | Commentaire |
|---|---|---|
| `po_id` | TEXT | clé |
| `supplier_id` | TEXT | obligatoire → supplier(supplier_id) |
| `item_id` | TEXT | obligatoire → item(item_id) |
| `qty` | INTEGER | obligatoire |
| `order_day` | INTEGER | obligatoire |
| `due_day` | INTEGER | obligatoire |

## `receipt`

Réceptions : un lot fournisseur, son statut (accepté, quarantaine) et son emplacement. · 56 lignes

| Colonne | Type | Commentaire |
|---|---|---|
| `lot_id` | TEXT | clé |
| `po_id` | TEXT | obligatoire → purchase_order(po_id) |
| `item_id` | TEXT | obligatoire → item(item_id) |
| `qty` | INTEGER | obligatoire |
| `day` | INTEGER | obligatoire |
| `status` | TEXT | obligatoire CHECK (status IN ('accepté', 'quarantaine', 'refusé')) |
| `loc_code` | TEXT | → location(loc_code) |

## `inspection`

Résultats de contrôle par lot ou numéro de série. · 27 509 lignes

| Colonne | Type | Commentaire |
|---|---|---|
| `insp_id` | INTEGER | clé |
| `plan_id` | TEXT | obligatoire → control_plan(plan_id) |
| `ref` | TEXT | obligatoire · lot ou numéro de série contrôlé |
| `day` | INTEGER | obligatoire |
| `value` | REAL | obligatoire |
| `ok` | INTEGER | obligatoire |

## `stock_move`

Mouvements de stock (entrées positives, sorties négatives) avec motif. · 14 347 lignes

| Colonne | Type | Commentaire |
|---|---|---|
| `move_id` | INTEGER | clé |
| `day` | INTEGER | obligatoire |
| `item_id` | TEXT | obligatoire → item(item_id) |
| `lot_id` | TEXT |  |
| `qty` | INTEGER | obligatoire · positif = entrée, négatif = sortie |
| `from_loc` | TEXT |  |
| `to_loc` | TEXT |  |
| `reason` | TEXT | obligatoire |

## `sales_order`

Commandes clients : échéance et date d'expédition. · 202 lignes

| Colonne | Type | Commentaire |
|---|---|---|
| `so_id` | TEXT | clé |
| `customer` | TEXT | obligatoire |
| `item_id` | TEXT | obligatoire → item(item_id) |
| `qty` | INTEGER | obligatoire |
| `order_day` | INTEGER | obligatoire |
| `due_day` | INTEGER | obligatoire |
| `shipped_day` | INTEGER |  |
| `shipped_qty` | INTEGER | obligatoire DEFAULT 0 |

## `manufacturing_order`

Ordres de fabrication. · 80 lignes

| Colonne | Type | Commentaire |
|---|---|---|
| `mo_id` | TEXT | clé |
| `item_id` | TEXT | obligatoire → item(item_id) |
| `qty` | INTEGER | obligatoire |
| `day` | INTEGER | obligatoire |
| `status` | TEXT | obligatoire |

## `shop_entry`

Saisie atelier par poste et par jour : temps d'ouverture, arrêts, marche, bons, rebuts. · 320 lignes

| Colonne | Type | Commentaire |
|---|---|---|
| `entry_id` | INTEGER | clé |
| `mo_id` | TEXT | obligatoire → manufacturing_order(mo_id) |
| `wc_id` | TEXT | obligatoire → workcenter(wc_id) |
| `day` | INTEGER | obligatoire |
| `planned_s` | REAL | obligatoire · temps d'ouverture |
| `downtime_s` | REAL | obligatoire · arrêts |
| `run_s` | REAL | obligatoire · temps de marche |
| `good_qty` | INTEGER | obligatoire |
| `scrap_qty` | INTEGER | obligatoire |

## `downtime`

Arrêts par poste avec cause. · 481 lignes

| Colonne | Type | Commentaire |
|---|---|---|
| `dt_id` | INTEGER | clé |
| `wc_id` | TEXT | obligatoire → workcenter(wc_id) |
| `day` | INTEGER | obligatoire |
| `cause` | TEXT | obligatoire |
| `duration_s` | REAL | obligatoire |

## `serial_unit`

Produits finis identifiés par numéro de série, statut et commande client. · 6 991 lignes

| Colonne | Type | Commentaire |
|---|---|---|
| `serial_no` | TEXT | clé |
| `item_id` | TEXT | obligatoire → item(item_id) |
| `mo_id` | TEXT | obligatoire → manufacturing_order(mo_id) |
| `day` | INTEGER | obligatoire |
| `status` | TEXT | obligatoire CHECK (status IN ('conforme', 'rebut', 'retouché', 'expédié')) |
| `so_id` | TEXT | → sales_order(so_id) |

## `genealogy`

Traçabilité : lots de composants montés dans chaque numéro de série. · 65 017 lignes

| Colonne | Type | Commentaire |
|---|---|---|
| `serial_no` | TEXT | obligatoire → serial_unit(serial_no) |
| `item_id` | TEXT | obligatoire → item(item_id) |
| `lot_id` | TEXT | obligatoire → receipt(lot_id) |
| `qty` | REAL | obligatoire |

## `nonconformity`

Non-conformités : étape, défaut, cause, décision. · 275 lignes

| Colonne | Type | Commentaire |
|---|---|---|
| `nc_id` | TEXT | clé |
| `day` | INTEGER | obligatoire |
| `stage` | TEXT | obligatoire |
| `ref` | TEXT | obligatoire |
| `item_id` | TEXT | obligatoire |
| `defect` | TEXT | obligatoire |
| `cause` | TEXT | obligatoire |
| `disposition` | TEXT | obligatoire |
| `status` | TEXT | obligatoire |

## `corrective_action`

Étapes du 8D. · 8 lignes

| Colonne | Type | Commentaire |
|---|---|---|
| `ca_id` | TEXT | clé |
| `title` | TEXT | obligatoire |
| `opened_day` | INTEGER | obligatoire |
| `d_step` | TEXT | obligatoire |
| `owner` | TEXT | obligatoire |
| `content` | TEXT | obligatoire |

## Vues d'indicateurs

| Vue | Contenu |
|---|---|
| `v_trs_poste_jour` | Disponibilité, performance, qualité et TRS par poste et par jour |
| `v_qualite_jour` | Taux de rebut et rendement au premier passage par jour |
| `v_service_jour` | Respect des délais et taux de service par date d'échéance |
| `v_stock_jour` | Stock disponible en fin de journée par article (hors lots en quarantaine) |
| `v_tracabilite` | Lot → numéros de série → statut et client |
