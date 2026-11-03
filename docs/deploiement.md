# Plan de déploiement et décisions structurantes

## Démarche

Quatre volets (logistique, stockage, production, qualité), six étapes chacun. Chaque étape se termine par une
validation du responsable de production ; la mise en service d'un volet est validée par la direction.

| Étape | Livrable | Critère de sortie |
|---|---|---|
| 1. Cartographie des flux et besoins | [cartographie_flux.md](cartographie_flux.md), liste des besoins par métier | Flux validés sur le terrain avec les utilisateurs |
| 2. Paramétrage et adaptations | Paramétrage standard de l'ERP, adaptations limitées et justifiées | Chaque adaptation répond à un besoin écrit |
| 3. Données de base fiabilisées | Articles, nomenclatures, gammes, emplacements, plans de contrôle, règles de réappro | `sfe.checks` ne remonte aucune anomalie bloquante |
| 4. Tests avec les utilisateurs | Scénarios rejoués : réception, OF, test final, expédition, rappel de lot | Scénarios passés par les utilisateurs eux-mêmes |
| 5. Formation et modes opératoires | [modes_operatoires.md](modes_operatoires.md), sessions au poste | Chaque opérateur a fait sa saisie seul |
| 6. Mise en service accompagnée | Présence terrain les premières semaines, suivi des indicateurs | Indicateurs stables, saisies complètes |

Ordre retenu : production d'abord (le goulot conditionne tout le reste), puis logistique et stockage, la qualité
complète en dernier car elle s'appuie sur les lots et les numéros de série déjà en place.

## Décisions structurantes

**Codification des articles.** Code court lisible par l'opérateur (`MOT-650`, `ROU-608`), préfixe `SE-` pour les
sous-ensembles, `PF-` pour les produits finis. Pas de code « intelligent » qui encode des caractéristiques
susceptibles de changer.

**Codification des emplacements.** Format `ZZZ-XNN-N` (zone, allée et colonne, niveau), vérifié par expression
régulière avant impression des codes-barres. Zones : réception, contrôle, quarantaine, stock, bord de ligne, produits
finis, pièces détachées, expédition.

**Traçabilité.** Lot sur les composants critiques pour la sécurité ou le bruit (moteur, roulements, cartes,
cordon) et sur les pièces mécaniques et d'usure (accouplement, couteau, joint, bol, base) ; numéro de série sur chaque produit fini. Le lien série → lot est saisi
au pré-assemblage par scan (MO-03). Coût : un scan par changement de bac. Bénéfice : un rappel ciblé de 191 appareils
au lieu de toute la production de la période.

**Réapprovisionnement.** Point de commande = consommation pendant le délai fournisseur + stock de sécurité.
Stock de sécurité = 1,65 × variabilité × consommation × √délai (95 % de cycles sans rupture). Variabilité prise à
45 % pendant la montée en cadence, à revoir à la baisse une fois la cadence stabilisée. Quantité commandée : 10 jours
de consommation, arrondie au minimum de commande du fournisseur.

**Indicateurs.** Calculés dans la base (vues SQL), jamais dans un tableur à part : l'atelier et la direction lisent le
même chiffre. TRS mesuré au poste goulot, parce que c'est lui qui fixe la sortie de la ligne.

**Plans de contrôle.** Contrôle par échantillon à réception pour les composants critiques, contrôle à 100 % au test
final. Les tailles d'échantillon sont revues après chaque 8D.

## Risques suivis

| Risque | Parade |
|---|---|
| Saisies atelier incomplètes | Saisie au poste en moins de 30 secondes, liste fermée de causes d'arrêt, revue quotidienne |
| Données de base modifiées sans contrôle | Contrôles de cohérence relancés avant chaque modification de nomenclature ou de gamme |
| Rupture fournisseur pendant la montée en cadence | Stock de sécurité dimensionné sur une forte variabilité, suivi de la position stock + en commande |
| Défaut fournisseur non détecté | Carte p du test final suivie chaque jour, traçabilité lot pour confiner vite |
