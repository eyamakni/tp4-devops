"""Repetition REELLE des scenarios (commit/push, cluster, API ArgoCD).
Utiliser uniquement le cluster laboratoire kind-tp4-gitops.
Les actions UI sont reproduites via l'API ArgoCD, sans captures simulees.
"""
import base64
import json
import pathlib
import re
import ssl
import subprocess
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'apps/demo/overlays/dev/kustomization.yaml'
SSL = ssl._create_unverified_context()  # Certificat autosigne localhost uniquement.
EVIDENCE = []
TOKEN = None

def command(*args):
    r = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, encoding='utf-8')
    if r.returncode:
        raise RuntimeError(r.stderr)
    return r.stdout.strip()

def record(step, data):
    entry = {'time':datetime.now(timezone.utc).isoformat(), 'step':step, 'data':data}
    EVIDENCE.append(entry)
    print(json.dumps(entry, ensure_ascii=False), flush=True)
    folder = ROOT/'artifacts'
    folder.mkdir(exist_ok=True)
    (folder/'rehearsal.json').write_text(json.dumps(EVIDENCE, indent=2, ensure_ascii=False),encoding='utf-8')

def app():
    data = json.loads(command('kubectl','-n','argocd','get','application','demo','-o','json'))
    status = data.get('status',{})
    return {'sync':status.get('sync',{}).get('status'),
            'health':status.get('health',{}).get('status'),
            'revision':status.get('sync',{}).get('revision'),
            'history':status.get('history',[])}

def wait(label, predicate, timeout=300):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        if predicate():
            record(label,'OK')
            return
        time.sleep(5)
    raise TimeoutError(label)

def healthy():
    a=app()
    return a['sync']=='Synced' and a['health']=='Healthy'

def replicas(n):
    d=json.loads(command('kubectl','-n','demo','get','deployment','demo','-o','json'))
    return d['spec']['replicas']==n and d['status'].get('availableReplicas',0)==n

def commit(message):
    command('git','add','apps/demo/overlays/dev/kustomization.yaml')
    command('git','commit','-m',message)
    command('git','push','origin','main')
    sha=command('git','rev-parse','HEAD')
    record(message,sha)
    return sha

def modify(pattern,value):
    OVERLAY.write_text(re.sub(pattern,value,OVERLAY.read_text(encoding='utf-8')),encoding='utf-8')

def prom(expr):
    url='http://127.0.0.1:9090/api/v1/query?'+urllib.parse.urlencode({'query':expr})
    with urllib.request.urlopen(url,timeout=15) as r:
        return json.load(r)['data']['result']

def firing():
    return bool(prom('ALERTS{alertname="DemoContainerBlocked",alertstate="firing"}'))

def api(path, data):
    headers={'Content-Type':'application/json'}
    if TOKEN:
        headers['Authorization']='Bearer '+TOKEN
    req=urllib.request.Request('https://127.0.0.1:8080/api/v1/'+path,
                              data=json.dumps(data).encode(),headers=headers,method='POST')
    with urllib.request.urlopen(req,context=SSL,timeout=30) as r:
        return json.load(r)

def set_auto(enabled):
    policy={'prune':True,'selfHeal':True} if enabled else None
    patch=json.dumps({'spec':{'syncPolicy':{'automated':policy}}})
    command('kubectl','-n','argocd','patch','application','demo','--type=merge','-p',patch)

if __name__=='__main__':
    assert command('kubectl','config','current-context')=='kind-tp4-gitops', 'Mauvais cluster'
    assert not command('git','status','--porcelain'), 'Commiter les fichiers avant la repetition'
    assert healthy(), 'Attendre demo Synced/Healthy'
    original=OVERLAY.read_text(encoding='utf-8')
    secret=command('kubectl','-n','argocd','get','secret','argocd-initial-admin-secret',
                   '-o','jsonpath={.data.password}')
    password=base64.b64decode(secret).decode()
    TOKEN=api('session',{'username':'admin','password':password})['token']
    changed=False
    try:
        modify(r'count: \d+','count: 4')
        sha=commit('demo: scenario 1 quatre replicas')
        changed=True
        wait('scenario 1 CD',lambda: healthy() and app()['revision']==sha and replicas(4))
        record('scenario 1 etat',app())
        command('kubectl','-n','demo','scale','deployment/demo','--replicas=1')
        wait('scenario 2 self-healing',lambda: replicas(4))
        record('scenario 2 etat',app())
        modify(r'newTag: .*','newTag: tp4-image-inexistante')
        bad=commit('demo: scenario 3 image invalide')
        wait('scenario 3 Synced Degraded',lambda: app()['revision']==bad and app()['sync']=='Synced' and app()['health']=='Degraded')
        record('scenario 3 etat',app())
        wait('scenario 5 alerte Firing',firing,timeout=360)
        record('scenario 5 alerte',prom('ALERTS{alertname=~"DemoContainerBlocked|ArgoCDApplicationDegraded"}'))
        set_auto(False)
        stable=[h for h in app()['history'] if h['revision']==sha][-1]
        api('applications/demo/rollback',{'id':stable['id'],'prune':True})
        wait('scenario 4 rollback sain',lambda: app()['health']=='Healthy' and replicas(4))
        record('scenario 4 rollback API',app())
        command('git','revert','--no-edit',bad)
        command('git','push','origin','main')
        set_auto(True)
        wait('scenario 4 retour GitOps',healthy)
        wait('scenario 5 alerte resolue',lambda: not firing(),timeout=180)
        record('scenario 5 resolution',prom('argocd_app_info{name="demo"}'))
    finally:
        # Retour a l'etat sain initial, meme en cas d'echec d'un scenario.
        if changed and OVERLAY.read_text(encoding='utf-8')!=original:
            OVERLAY.write_text(original,encoding='utf-8')
            commit('fix: terminer repetition avec configuration initiale saine')
        set_auto(True)
        wait('etat final sain',lambda: healthy() and replicas(2))
