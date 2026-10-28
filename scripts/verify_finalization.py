"""Read-only checks for the published evidence archive; no Earth Engine calls."""
from pathlib import Path
import ast
import csv
import hashlib
import json
import re
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'outputs/final_evidence/step20a'
GOOD = ['W01', 'W02', 'W04', 'W05', 'W06', 'W07', 'W08', 'W10']

def rows(name):
    with (EVIDENCE / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

checks = []
def check(ok, label):
    if not ok:
        raise AssertionError(label)
    checks.append(label)

for rel, expected in json.loads((ROOT/'docs/evidence_checksums.json').read_text()).items():
    check(hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() == expected, 'Original evidence hash: ' + rel)
register = json.loads((EVIDENCE/'final_evidence_register.json').read_text())
p = register['primary_analysis']
check(p['GOOD_windows'] == GOOD, 'Exact eight GOOD windows')
check(p['threshold_defined_agricultural_pixels'] == 229729, 'Threshold mask count')
check(p['GOOD_window_supported_agricultural_pixels'] == 223600, 'Supported footprint count')
check(abs(223600*400/1e6 - p['GOOD_window_supported_agricultural_area_km2']) < 1e-9, 'Supported area from pixel count')
check(abs(229729*400/1e6 - p['threshold_defined_agricultural_area_km2']) < 1e-9, 'Threshold area from pixel count')
check(abs(100*223600/229729 - p['GOOD_window_supported_fraction_of_mask_pct']) < 1e-9, 'Coverage denominator')
s = {x['window']:x for x in rows('Table_01_final_seasonal_summary.csv')}
check([w for w,x in s.items() if x['EO_status']=='GOOD']==GOOD, 'Table 1 statuses')
check(s['W09']['EO_status']=='LIMITED', 'W09 remains LIMITED')
check(s['W03']['EO_status']=='MISSING' and all(s['W03'][k]=='' for k in ['Cw_median_cm','laiCw_median_g_m2','LAI_median_m2_m2','NDVI_median','NDMI_median']), 'W03 contains no EO interpolation')
fields={'Cw':'Cw_median_cm','laiCw':'laiCw_median_g_m2','LAI':'LAI_median_m2_m2','NDVI':'NDVI_median','NDMI':'NDMI_median'}
for x in rows('Table_02_temporal_correlations_GOOD.csv'):
    a=[float(s[w][fields[x['trait']]]) for w in GOOD]
    b=[float(s[w][fields[x['index']]]) for w in GOOD]
    check(int(x['n_GOOD_windows'])==8 and abs(np.corrcoef(a,b)[0,1]-float(x['Pearson_r']))<0.0002, 'Temporal correlation from rounded medians: '+x['trait']+'/'+x['index'])
for x in rows('Table_06_EO_hydroclimate_correlations.csv'):
    check(int(x['n_GOOD_windows'])==8, 'Hydroclimate sample size: '+x['EO_variable']+'/'+x['environmental_variable'])
spatial=next(x for x in rows('Table_03_spatial_correlation_summary_GOOD.csv') if x['trait']=='Cw' and x['index']=='NDMI')
check(float(spatial['Pearson_min'])==0.281 and float(spatial['Pearson_max'])==0.8646, 'Spatial extrema')
ru=rows('Table_04_RU_sensitivity.csv')
check(set(x['RU_threshold_pct'] for x in ru)=={'20','30','40'}, 'RU sensitivity thresholds')
check(max(float(x['max_absolute_median_shift_pct']) for x in ru)==1427.7, 'Maximum RU median shift')
for folder in ['src','scripts','config']:
    for path in (ROOT/folder).glob('*.py'):
        ast.parse(path.read_text(encoding='utf-8-sig'))
checks.append('Python source syntax')
for path in [ROOT/'README.md',*(ROOT/'docs').glob('*.md'),ROOT/'external/README.md']:
    for target in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
        if '://' in target or target.startswith('#'): continue
        check((path.parent/target.split('#')[0]).exists(),'Local Markdown link: '+target)
print(f'PASS: {len(checks)} checks. Original evidence unchanged; statuses, areas, correlations, syntax and documentation links verified.')
