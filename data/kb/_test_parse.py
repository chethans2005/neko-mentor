import sys
sys.path.insert(0, 'data/kb')
import generate_kb
from pathlib import Path
p = Path('data/raw/Graceful_Degradation.raw.txt')
raw = p.read_text(encoding='utf-8')
print('RAW HEAD:', raw[:200])
res = generate_kb.parse_response(raw)
print('RESULT TYPE:', type(res), 'TRUTHY:', bool(res))
if res:
    import json
    print(json.dumps(res, indent=2)[:1000])