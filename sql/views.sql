-- Indicateurs calculés directement dans la base : les mêmes requêtes alimentent les vues atelier et direction.

-- TRS (taux de rendement synthétique) par poste et par jour = disponibilité x performance x qualité
CREATE VIEW v_trs_poste_jour AS
SELECT se.day,
       se.wc_id,
       SUM(se.planned_s)                                             AS ouverture_s,
       SUM(se.run_s)                                                 AS marche_s,
       SUM(se.good_qty + se.scrap_qty)                               AS produits,
       SUM(se.good_qty)                                              AS bons,
       SUM(se.run_s) / SUM(se.planned_s)                             AS disponibilite,
       SUM((se.good_qty + se.scrap_qty) * rs.std_time_s) / SUM(se.run_s) AS performance,
       CAST(SUM(se.good_qty) AS REAL) / SUM(se.good_qty + se.scrap_qty)  AS qualite,
       SUM(se.good_qty * rs.std_time_s) / SUM(se.planned_s)          AS trs
FROM shop_entry se
JOIN manufacturing_order mo ON mo.mo_id = se.mo_id
JOIN routing_step rs ON rs.item_id = mo.item_id AND rs.wc_id = se.wc_id
GROUP BY se.day, se.wc_id;

-- Taux de rebut et rendement au premier passage par jour
CREATE VIEW v_qualite_jour AS
SELECT su.day,
       COUNT(*)                                                       AS produits,
       SUM(su.status = 'rebut')                                       AS rebuts,
       CAST(SUM(su.status = 'rebut') AS REAL) / COUNT(*)              AS taux_rebut,
       1.0 - CAST((SELECT COUNT(*) FROM nonconformity nc
                   WHERE nc.day = su.day AND nc.stage IN ('en-cours', 'final')) AS REAL) / COUNT(*) AS rendement_1er_passage
FROM serial_unit su
GROUP BY su.day;

-- Respect des délais et taux de service par date d'échéance
CREATE VIEW v_service_jour AS
SELECT so.due_day                                                     AS day,
       COUNT(*)                                                       AS commandes,
       SUM(so.shipped_day IS NOT NULL AND so.shipped_day <= so.due_day) AS a_l_heure,
       CAST(SUM(so.shipped_day IS NOT NULL AND so.shipped_day <= so.due_day) AS REAL) / COUNT(*) AS respect_delais,
       SUM(so.qty)                                                    AS qte_due,
       SUM(CASE WHEN so.shipped_day <= so.due_day THEN so.qty ELSE 0 END) AS qte_a_l_heure
FROM sales_order so
WHERE so.due_day <= (SELECT MAX(day) FROM shop_entry)
GROUP BY so.due_day;

-- Stock en fin de journée par article (cumul des mouvements)
CREATE VIEW v_stock_jour AS
WITH jours AS (SELECT DISTINCT day FROM stock_move),
     articles AS (SELECT DISTINCT item_id FROM stock_move)
SELECT j.day, a.item_id,
       (SELECT COALESCE(SUM(m.qty), 0) FROM stock_move m
        WHERE m.item_id = a.item_id AND m.day <= j.day
          AND NOT (m.to_loc = 'QUA-01' AND m.reason = 'réception')) AS stock
FROM jours j CROSS JOIN articles a;

-- Traçabilité descendante : numéros de série qui contiennent un lot donné, avec leur destination
CREATE VIEW v_tracabilite AS
SELECT g.lot_id, g.item_id AS composant, r.day AS jour_reception, s.supplier_id, s.name AS fournisseur,
       su.serial_no, su.item_id AS produit, su.day AS jour_fabrication, su.status, so.customer, so.shipped_day
FROM genealogy g
JOIN receipt r ON r.lot_id = g.lot_id
JOIN purchase_order po ON po.po_id = r.po_id
JOIN supplier s ON s.supplier_id = po.supplier_id
JOIN serial_unit su ON su.serial_no = g.serial_no
LEFT JOIN sales_order so ON so.so_id = su.so_id;
