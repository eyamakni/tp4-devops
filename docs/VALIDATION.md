# Validation réelle — 16 novembre 2026

Exécutée sur Windows, Docker Desktop et le cluster isolé Kind **tp4-gitops**, Kubernetes **1.32.2**. Le cluster existant devops-tp est conservé. Horaires ci-dessous en **Africa/Tunis (UTC+1)** ; le JSON de preuve utilise UTC.

## Vérifications réalisées

| Contrôle | Résultat |
|---|---|
| API HTTP réelle : 200, 500 volontaire et 404 | Réussi |
| Compteurs et durée Prometheus ; probes exclues | Réussi |
| Rendu Kustomize application et observabilité | Réussi |
| Syntaxe de 4 scripts Python et 13 YAML | Valide |
| Analyse syntaxique des scripts PowerShell | Valide |
| Trois Applications ArgoCD | Synced / Healthy après restauration |
| Cibles demo, controller, server et repo-server | Toutes UP |
| Métriques ArgoCD, répliques et mémoire | Présentes dans Prometheus |
| Trois règles du groupe tp4.gitops | Chargées, health=ok |
| Dashboard Grafana provisionné | 14 panneaux, retrouvé via API authentifiée |
| 14 requêtes PromQL du dashboard | Exécutées sans erreur |
| Charge HTTP | 1 240 requêtes en 180 s, environ 10 % de 500 volontaires |

## Scénarios réellement exécutés

| Scénario | Observation |
|---|---|
| 1 — CD | Commit 0bca969 : quatre répliques disponibles à 18:28:46, Synced / Healthy |
| 2 — Self-healing | Mise à une réplique par kubectl, retour automatique à quatre à 18:28:57 |
| 3 — Panne | Commit d48d249 : image inexistante ; Synced / Degraded observé à 18:30:52 |
| 5 — Alerting | DemoContainerBlocked Firing confirmé à 18:35:24 ; ArgoCDApplicationDegraded également Firing |
| 4 — Rollback | Auto-sync suspendu, rollback historique via API ArgoCD vers 0bca969 ; Healthy / OutOfSync à 18:35:35 |
| 4 — Retour GitOps | Revert f029849 et réactivation de l'auto-sync ; Synced / Healthy à 18:35:48 |
| 5 — Résolution | Absence de DemoContainerBlocked Firing confirmée à 18:36:09 |
| État final | Commit 61137a9 : image valide et deux répliques ; trois Applications Synced / Healthy |

Un test supplémentaire du drift à deux répliques a mesuré le retour automatique de une à deux en environ cinq secondes. Les preuves du parcours principal sont dans [preuves-validation.json](preuves-validation.json). Les sorties locales détaillées sont conservées dans artifacts/ (exclu de Git).

La répétition utilise le terminal et l'API ArgoCD pour le rollback. Aucune capture de l'interface n'est inventée. La démonstration UI demandée pendant la soutenance reste à effectuer avec le guide SOUTENANCE.md. L'API Alertmanager a été consultée après résolution : sa liste d'alertes TP4 était vide ; le passage Firing est prouvé par les réponses Prometheus enregistrées.

## Corrections issues de l'exécution

- Attente explicite de repo-server, Redis et des CRD avant les ressources dépendantes.
- Mot de passe Grafana aléatoire ignoré dans le diff et préservé lors des synchronisations.
- Suppression des sous-routes Alertmanager héritées afin d'éviter un récepteur null non défini.
- Webhook d'admission Prometheus Operator optionnel désactivé dans le profil local pour éviter le blocage des hooks Helm de certificats. L'Operator, les CRD, le scraping et l'évaluation des règles restent actifs.
- Port Grafana local 3001 car un autre Grafana occupait déjà 3000.
- Interruption DNS temporaire constatée puis résolue ; téléchargements et pushes repris.

Ces vérifications prouvent le fonctionnement dans ce laboratoire, sans prétendre à une qualification de production.
