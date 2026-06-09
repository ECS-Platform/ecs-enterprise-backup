import json
import sys
import pathlib
# Ensure project root is on sys.path when invoked from scripts/
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
from modules.frameworks.engines.framework_catalog import get_framework_controls, resolve_framework_name
from modules.frameworks.engines.framework_dashboards import build_framework_dashboard

def summarize(framework_slug):
    fw = resolve_framework_name(framework_slug)
    controls = get_framework_controls(fw)
    dash = build_framework_dashboard(fw, controls)
    lib = dash.get('control_library', [])
    total = len(lib)
    predefined = sum(1 for r in lib if r.get('predefined') == 'YES')
    tech_counts = {}
    for r in lib:
        tech_counts[r.get('technology','')] = tech_counts.get(r.get('technology',''),0) + 1
    sample = [ { 'control_id': r.get('control_id'), 'control_name': r.get('control_name'), 'technology': r.get('technology'), 'predefined': r.get('predefined'), 'query': r.get('query'), 'framework_coverage': r.get('framework_coverage') } for r in lib[:8] ]
    return { 'framework': fw, 'total': total, 'predefined': predefined, 'tech_counts': tech_counts, 'sample': sample }

if __name__ == '__main__':
    out = {
        'pci': summarize('PCI'),
        'nginx': summarize('Nginx Baseline')
    }
    print(json.dumps(out, indent=2))
