---
description: Lancer l'experiment Langfuse et rédiger la comparaison honnête avec le run précédent
argument-hint: [ce qui a changé depuis le run précédent]
---
Changement à mesurer : $ARGUMENTS
1. Synchronise le dataset depuis le JSON du dépôt (identifiants d'items stables), puis lance dataset.run_experiment avec max_concurrency=1 et un run_name qui décrit le changement.
2. Compare avec le run précédent, cas par cas.
3. Rédige la phrase honnête : « x passe de a/N à b/N ; ces cas restent faux : … ». Donne les chiffres même s'ils baissent. N'ajuste ni le dataset ni les évaluateurs pour améliorer le score.
