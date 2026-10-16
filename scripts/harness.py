"""Offline human-gated stage runner. It never invokes Claude or accesses the network."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'.harness/state.json'
STAGES=(
    '01_datapath.md',
    '02_singlecore.md',
    '03_dualcore.md',
    '04_sharedmemory.md',
    '05_bonus.md',
    '06_delivery.md',
)


def load_state():
    data=json.loads(STATE.read_text(encoding='utf-8'))
    if type(data.get('stage')) is not int or not 1 <= data['stage'] <= len(STAGES)+1:
        raise SystemExit('Invalid harness state. Stop; do not auto-repair.')
    return data


def audit():
    lines=(ROOT/'contracts.sha256').read_text(encoding='utf-8').splitlines()
    problems=[]
    for line in lines:
        expected,rel=line.split('  ',1)
        path=ROOT/rel
        if not path.is_file():
            problems.append('MISSING '+rel)
        elif hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            problems.append('CHANGED '+rel)
    if problems:
        print('PROTECTED CONTRACT CHANGE DETECTED:')
        print('\n'.join('  '+x for x in problems))
        print('Stop and inspect. Do not silently rewrite tests or hash manifest.')
        return False
    print(f'Integrity OK: {len(lines)} protected files')
    return True


def verify(stage):
    if not audit():
        return False
    if stage>len(STAGES):
        stage=len(STAGES)
    modules=[f'tests.test_stage_{i:02d}' for i in range(1,stage+1)]
    print('Testing stages 01..%02d with %s' %(stage, sys.executable),flush=True)
    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}
    try:
        result=subprocess.run([sys.executable,'-B','-m','unittest','-v',*modules],cwd=ROOT,env=env,timeout=40,check=False)
    except subprocess.TimeoutExpired:
        print('Test timeout (40 seconds).')
        return False
    return result.returncode==0


def checkpoint_present(stage):
    marker=f'[STAGE {stage:02d}]'
    missing=[]
    for rel in ('PROGRESS.md','docs/EXPLANATIONS.md'):
        if marker not in (ROOT/rel).read_text(encoding='utf-8'):
            missing.append(rel)
    if missing:
        print('Missing the stage checkpoint '+marker+' in: '+', '.join(missing))
        print('Claude must explain the work before human approval.')
        return False
    return True


def main():
    p=argparse.ArgumentParser(description='Local, human-controlled CCEE 324 milestone harness')
    p.add_argument('command',choices=['status','task','verify','advance','audit'])
    args=p.parse_args()
    s=load_state(); stage=s['stage']
    if args.command=='status':
        print('Stage:', ('COMPLETE' if stage>len(STAGES) else f'{stage:02d} / {len(STAGES):02d} – {STAGES[stage-1]}'))
        print('Human-approved:', ', '.join(f'{x:02d}' for x in s['completed']) or 'none')
        print('Use `python scripts/harness.py task` for current work.')
        if os.getenv('ANTHROPIC_API_KEY'):
            print('COST WARNING: ANTHROPIC_API_KEY is set. Unset it if using Claude Pro login.')
        return 0
    if args.command=='task':
        if stage>len(STAGES):
            print('All milestones marked complete. No new task.')
        else:
            print((ROOT/'tasks'/STAGES[stage-1]).read_text(encoding='utf-8'))
        return 0
    if args.command=='audit':
        return 0 if audit() else 2
    if args.command=='verify':
        return 0 if verify(stage) else 1
    if stage>len(STAGES):
        print('Already complete.');return 0
    if not verify(stage):
        print('Stage FAILED its test gate; no advancement.');return 1
    if not checkpoint_present(stage):
        return 1
    expected=f'I APPROVE STAGE {stage:02d}'
    print(f'Inspect files and PROGRESS.md. To advance, type: {expected}')
    actual=input('Human approval: ').strip()
    if actual!=expected:
        print('No changes made.');return 1
    s['completed'].append(stage)
    s['stage']+=1
    STATE.write_text(json.dumps(s,indent=2)+'\n',encoding='utf-8')
    print('Advanced to:', 'COMPLETED' if s['stage']>len(STAGES) else STAGES[s['stage']-1])
    return 0

if __name__=='__main__':
    raise SystemExit(main())
