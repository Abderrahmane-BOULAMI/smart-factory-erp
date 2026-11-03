# Modes opératoires d'atelier

Fiches courtes, une par geste, écrites pour être affichées au poste. Chaque fiche dit ce qu'on fait, ce qu'on
saisit et ce qu'on fait si ça ne va pas.

---

## MO-01 · Réceptionner un lot fournisseur

**Qui :** magasinier · **Où :** quai REC-01 / REC-02

1. Vérifier que la livraison correspond à une commande ouverte (numéro de commande sur le bon de livraison).
2. Scanner l'étiquette du colis. Le système crée le lot `L-<article>-<jour><rang>` et l'affecte à la commande.
3. Saisir la quantité reçue. Écart supérieur à 2 % avec la commande : le signaler aux achats avant de continuer.
4. Déposer le lot sur l'emplacement proposé et scanner le code-barres de l'emplacement.
5. Article critique (moteur, roulements, cartes, cordon) : le lot est bloqué en contrôle tant que MO-02 n'est pas fait.

**Si ça ne va pas :** colis abîmé ou étiquette illisible, poser le lot en QUA-01 et ouvrir une non-conformité
« réception ».

## MO-02 · Contrôler un lot à réception

**Qui :** contrôleur qualité · **Où :** CTL-01

1. Ouvrir le plan de contrôle de l'article (`CP-R-*`). Il donne la caractéristique, les limites et la taille d'échantillon.
2. Prélever l'échantillon au hasard dans le lot, mesurer, saisir chaque valeur.
3. Toutes les valeurs dans les limites : le lot passe « accepté » et devient disponible.
4. Une valeur hors limites : le lot passe « quarantaine » et part en QUA-01. Non-conformité ouverte, achats prévenus.

**Depuis le 8D-001 :** roulements contrôlés sur 13 pièces au lieu de 5, limite de décision à 18 µm, certificat
fournisseur exigé pour chaque lot.

## MO-03 · Déclarer sa production

**Qui :** opérateur · **Où :** chaque poste, terminal du poste

1. Début de poste : scanner l'OF du jour. Le temps d'ouverture démarre.
2. Pré-assemblage : à chaque changement de bac, scanner le lot du composant critique (moteur, roulements, carte).
   C'est ce scan qui permet la traçabilité.
3. Arrêt de plus de 2 minutes : choisir la cause dans la liste (panne, attente composant, réglage, micro-arrêts,
   qualité). Pas de cause « divers ».
4. Fin de poste : saisir les quantités bonnes et rebutées. Le TRS du poste est calculé automatiquement.

**Si ça ne va pas :** composant manquant au bord de ligne, déclarer l'arrêt « attente composant » et appeler le
magasin. Ne pas prendre de composant dans un bac sans étiquette de lot.

## MO-04 · Test final et étiquetage

**Qui :** opérateur de test · **Où :** WC-TST puis WC-EMB

1. Poser l'appareil sur le banc. Le banc mesure courant en charge, bruit à 1 m et rigidité diélectrique et enregistre
   les valeurs sur le numéro de série.
2. Conforme : l'appareil passe à l'emballage, l'étiquette série est imprimée.
3. Bruit au-dessus de 82 dB(A) : retouche (remplacement du bloc moteur) puis nouveau test. Autre défaut : rebut et
   non-conformité.
4. Plus de 3 refus bruit dans la journée : prévenir le responsable qualité. La carte p du test final est revue chaque
   jour.

## MO-05 · Rappeler un lot

**Qui :** responsable qualité · **Où :** vue Traçabilité du cockpit

1. Saisir le lot suspect. Le système liste tous les numéros de série qui le contiennent, leur statut et leur client.
2. Bloquer immédiatement le lot restant en stock et les produits finis non expédiés concernés.
3. Exporter la liste des clients livrés et la transmettre au service client.
4. Ouvrir ou compléter le 8D (étape D3, confinement).
