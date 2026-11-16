"""Verification fonctionnelle apres bootstrap et port-forward (stdlib uniquement)."""
import json
import urllib.parse
import urllib.request

BASE = 'http://127.0.0.1:9090'
def get(path):
    with urllib.request.urlopen(BASE + path, timeout=15) as response:
        data = json.load(response)
    if data.get('status') != 'success':
        raise RuntimeError(data)
    return data['data']

targets = get('/api/v1/targets')['activeTargets']
expected = ['demo','argocd-controller','argocd-server','argocd-repo-server']
for name in expected:
    matches = [t for t in targets if t.get('scrapePool','').startswith('serviceMonitor/monitoring/' + name + '/')]
    assert matches, f'Pas de cible : {name}'
    assert all(t['health'] == 'up' for t in matches), [(t['scrapeUrl'],t['lastError']) for t in matches]
    print(f'UP : {name} ({len(matches)} cibles)')
for expr in ['argocd_app_info{name="demo"}',
             'kube_deployment_spec_replicas{namespace="demo",deployment="demo"}',
             'container_memory_working_set_bytes{namespace="demo",container="demo"}']:
    result = get('/api/v1/query?' + urllib.parse.urlencode({'query':expr}))['result']
    assert result, f'Serie absente : {expr}'
    print('OK :',expr)
groups = get('/api/v1/rules')['groups']
rules = [r for g in groups if g['name']=='tp4.gitops' for r in g['rules']]
assert len(rules)==3, rules
assert all(r['health']=='ok' for r in rules), rules
print('OK : trois regles TP4 chargees et saines')
with urllib.request.urlopen('http://127.0.0.1:3001/api/health', timeout=15) as response:
    assert json.load(response)['database']=='ok'
print('OK : Grafana disponible')

with urllib.request.urlopen('http://127.0.0.1:9093/-/ready', timeout=15) as response:
    assert response.status == 200
assert get('/api/v1/alertmanagers')['activeAlertmanagers'], 'Aucun Alertmanager decouvert'
print('OK : Alertmanager pret et decouvert par Prometheus')
