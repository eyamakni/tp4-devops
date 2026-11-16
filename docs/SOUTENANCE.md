# Les cinq scénarios — guide de soutenance

Préparer ArgoCD, Grafana, Prometheus et le terminal côte à côte. État initial : trois Applications Synced/Healthy, deux répliques demo. Grafana : 30 dernières minutes, rafraîchissement 5 s. Conserver les sorties et captures réelles dans artifacts/ (exclu de Git).

## 1. Déploiement continu

```powershell
powershell -File scripts/demo.ps1 scale -Replicas 4
git diff
git add apps/demo/overlays/dev/kustomization.yaml
git commit -m "demo: passer a quatre replicas"
git push origin main
kubectl -n demo get deployment -w
```

Commenter : Git définit quatre répliques. ArgoCD détecte le commit et applique le manifeste sans kubectl apply de notre part. Montrer le SHA et Desired/Available dans Grafana. Polling 30 s puis durée du rollout : la détection n'est pas littéralement instantanée.

Preuves : diff et commit, quatre répliques, Synced/Healthy.

## 2. Drift et self-healing

```powershell
powershell -File scripts/demo.ps1 drift
kubectl -n demo get deployment -w
```

Une réplique est forcée alors que Git en demande quatre. ArgoCD rétablit quatre via selfHeal sans nouveau commit. OutOfSync peut être trop bref pour une capture : consulter les événements. Variante facultative plus visible, avec interruption : kubectl -n demo delete deployment demo, puis attendre sa recréation.

## 3. Synced et Health sont indépendants

```powershell
powershell -File scripts/demo.ps1 break
git add apps/demo/overlays/dev/kustomization.yaml
git commit -m "demo: image invalide pour panne"
git push origin main
git rev-parse HEAD
kubectl -n demo get pods -w
kubectl -n demo describe deployment demo
```

Noter le SHA de panne pour le revert. Synced signifie conformité au manifeste Git. Les nouveaux pods passent ErrImagePull/ImagePullBackOff. Health peut être Progressing avant Degraded après le progressDeadline de 90 s. RollingUpdate peut garder des anciens pods disponibles : ne pas annoncer un arrêt total sans le constater.

Laisser la panne 4 à 5 min pour voir les alertes : 2 min d'état continu, plus les délais de scraping/évaluation. Une erreur de téléchargement ne compte pas comme un redémarrage du conteneur.

## 4. Historique et rollback dans l'UI

1. Application demo → App Details / Sync Policy : désactiver temporairement Automated Sync. Elle n'a pas de parent qui annulerait ce changement.
2. History and Rollback : choisir une révision stable précédant la panne, déclencher Rollback. ArgoCD interdit le rollback lorsque l'auto-sync est activé.
3. Constater Healthy. Git contient encore la mauvaise image : OutOfSync est possible.
4. Corriger Git avant de réactiver l'auto-sync :

```powershell
# Remplacer SHA_DU_COMMIT_DE_PANNE par le vrai SHA.
git revert --no-edit SHA_DU_COMMIT_DE_PANNE
git push origin main
```

5. Réactiver Automated Sync, Prune et Self Heal dans l'UI. Vérifier Synced/Healthy. La configuration souhaitée est aussi dans argocd/demo.yaml.

Le rollback UI restaure le cluster ; le revert corrige durablement la source de vérité. Réactiver l'auto-sync trop tôt redéploierait la panne.

## 5. Corrélation GitOps, métriques et alertes

Générer du trafic dans un terminal séparé :

```powershell
powershell -File scripts/load.ps1 -Seconds 180
```

Environ 10 % des requêtes sont des 500 volontaires via /error. Le port-forward d'un Service vise un seul pod : ce trafic n'est pas un benchmark distribué. Après un rollout, relancer le port-forward si le pod cible disparaît.

Réinjecter l'image invalide avec les commandes du scénario 3. Montrer :

- synchronisations en hausse et annotations GitOps ;
- état ArgoCD Synced puis Degraded ;
- Desired/Available et nouveaux pods bloqués ;
- Prometheus Alerts : Pending puis Firing pour DemoContainerBlocked ;
- Alertmanager : alerte active.

Corriger exclusivement par Git :

```powershell
powershell -File scripts/demo.ps1 restore
git add apps/demo/overlays/dev/kustomization.yaml
git commit -m "fix: restaurer image valide"
git push origin main
```

Attendre Synced/Healthy, l'absence de Firing actif puis la disparition dans Alertmanager. Le graphe conserve l'historique. Les séries des pods supprimés peuvent rester brièvement visibles. Revenir ensuite à deux répliques via scale -Replicas 2, commit et push.

## Captures et questions

Captures : dépôt, trois Applications saines, quatre répliques, drift réparé, Synced/Degraded, historique/rollback, dashboard de panne, Firing puis résolution.

- Pourquoi Pull ? Le contrôleur lit Git ; la livraison n'exige aucun kubeconfig côté développeur.
- Pourquoi superviser ArgoCD ? Un problème de livraison peut précéder ou expliquer un problème applicatif.
- Pourquoi un ServiceMonitor ne suffit-il pas ? Il faut l'Operator, un Prometheus qui le sélectionne et un Service dont labels/port correspondent.
- Pourquoi zéro redémarrage pendant ImagePullBackOff ? Le nouveau conteneur n'a pas encore démarré.
- Pourquoi temporiser deux minutes ? Éviter de traiter chaque transition brève comme une panne persistante.
