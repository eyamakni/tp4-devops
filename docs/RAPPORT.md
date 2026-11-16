# Rapport technique — TP4

## Objectif et choix

Construire une chaîne de livraison pull et rendre ses effets observables. L'API Python expose des compteurs HTTP et une somme/dénombrement de durée sans dépendance. Kustomize sépare socle et overlay. Le hash de la ConfigMap provoque un rollout lors d'une modification du code.

Trois Applications décrivent l'application métier, la stack Helm et les ressources de supervision. Le chart multi-source lit ses valeurs depuis Git. Les métriques ArgoCD distinguent conformité et santé. kube-state-metrics fournit désiré/réel ; le kubelet fournit CPU/mémoire ; l'API expose débit et erreurs.

## Couverture

| Exigence | Réalisation |
|---|---|
| SSOT et overlay | apps/demo/base et overlays/dev |
| Auto-sync, prune et self-healing | argocd/*.yaml |
| Historique et rollback | scénario 4 du guide |
| Stack déclarative | argocd/monitoring.yaml et monitoring/values.yaml |
| Trois composants ArgoCD et API | observability/servicemonitors.yaml |
| Dashboard exporté | observability/dashboards/tp4-gitops.json |
| Alerte persistante 2 min | observability/alerts.yaml |
| Cinq scénarios | docs/SOUTENANCE.md |

## Analyse

Après un commit, ArgoCD synchronise les ressources, puis les répliques convergent. Une modification directe constitue une dérive corrigée par selfHeal. Une image inexistante reste conforme à Git mais inexécutable : Synced n'implique pas Healthy. La progression temporisée évite de qualifier immédiatement un rollout en panne. Le rollback UI nécessite la suspension de l'auto-sync ; le revert Git assure une correction durable.

## Résultats

Consulter docs/VALIDATION.md pour les vérifications réellement exécutées. Les captures de soutenance doivent provenir du cluster et ne sont jamais remplacées par des résultats fictifs.

## Recul critique

Laboratoire local : données éphémères, aucune HA ni notification externe, projet ArgoCD default. Pour la production : versions maintenues, image applicative signée et fixée par digest, stockage persistant, SSO, projets/RBAC restrictifs, politiques réseau, secrets externes et récepteurs d'alerte. Les courbes par fenêtres de temps ne fournissent pas un journal exact des déploiements ; l'historique ArgoCD conserve le commit de référence.
