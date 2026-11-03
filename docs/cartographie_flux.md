# Cartographie des flux

Première étape du déploiement : décrire ce qui circule réellement dans l'usine avant de paramétrer quoi que ce soit.
Chaque flèche correspond à une transaction enregistrée dans le socle.

## Flux physique

```mermaid
flowchart LR
    F[Fournisseurs] -->|livraison + lot| REC[Réception<br>REC-01/02]
    REC -->|échantillon| CTL[Contrôle réception<br>CTL-01]
    CTL -->|conforme| STK[Stock composants<br>STK-xnn-n]
    CTL -->|non conforme| QUA[Quarantaine<br>QUA-01]
    STK -->|réappro bord de ligne| BDL[Bords de ligne<br>BDL-PRE, BDL-ASM]
    BDL --> PRE[WC-PRE<br>bloc moteur]
    PRE --> ASM[WC-ASM<br>assemblage final, goulot]
    BDL --> ASM
    ASM --> TST[WC-TST<br>test courant, bruit, diélectrique]
    TST -->|conforme| EMB[WC-EMB<br>étiquette série, notice, carton]
    TST -->|retouche| ASM
    TST -->|rebut| RB[Rebut]
    EMB --> PFI[Stock produits finis<br>PFI-nn]
    PFI --> EXP[Expédition<br>EXP-01/02]
    EXP --> CL[Clients]
    STK -->|pièces détachées| SAV[SAV-nn]
```

## Flux d'information

```mermaid
flowchart TB
    SO[Commande client<br>sales_order] --> PLAN[Plan de production]
    PLAN --> MO[Ordre de fabrication<br>manufacturing_order]
    PLAN --> MRP[Besoins nets<br>replenish.net_requirements]
    RULE[Règles de réappro<br>replenishment_rule] --> PO[Commande fournisseur<br>purchase_order]
    MRP --> PO
    PO --> RCV[Réception lot<br>receipt]
    RCV --> INS[Contrôle<br>inspection]
    INS --> NC[Non-conformité<br>nonconformity]
    NC --> CA[8D<br>corrective_action]
    MO --> SE[Saisie atelier<br>shop_entry, downtime]
    MO --> SN[Numéro de série<br>serial_unit]
    RCV --> GEN[Généalogie<br>genealogy]
    SN --> GEN
    SN --> SO
    RCV --> MV[Mouvements de stock<br>stock_move]
    SE --> MV
    SE --> KPI[Indicateurs<br>vues SQL]
    INS --> KPI
    SO --> KPI
```

## Points de saisie

| Où | Qui | Quoi | Table |
|---|---|---|---|
| Quai de réception | Magasinier | Scan de l'étiquette fournisseur, création du lot, emplacement de dépose | `receipt`, `stock_move` |
| Contrôle réception | Contrôleur | Mesures sur l'échantillon défini par le plan de contrôle | `inspection` |
| Chaque poste | Opérateur | Début et fin d'OF, quantités bonnes et rebutées, arrêts avec cause | `shop_entry`, `downtime` |
| Pré-assemblage | Opérateur | Scan des lots de composants critiques montés | `genealogy` |
| Banc de test | Automatique | Courant, bruit, rigidité diélectrique par numéro de série | `inspection` |
| Emballage | Opérateur | Impression de l'étiquette série | `serial_unit` |
| Expédition | Magasinier | Scan des numéros de série par commande | `sales_order`, `serial_unit` |
