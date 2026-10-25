"""Inspect supplied data without assuming its dictionary. Does not approve a schema mapping."""
import argparse,csv,json,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('dataset',type=Path);a=p.parse_args();root=a.dataset.resolve()
for name in ['README.md','DATA_DICTIONARY.md','ZIP_SCHEMA.md','CHANGELOG.md']:
    file=root/name
    print('\n'+name+'\n'+(file.read_text() if file.exists() else 'MISSING'))
for file in sorted((root/'kb').glob('*.md')): print('\n'+file.name+'\n'+file.read_text())
for file in sorted((root/'data').glob('*.csv')):
    with file.open() as f:
        reader=csv.DictReader(f);rows=list(reader);print(file.name,json.dumps({'columns':reader.fieldnames,'records':len(rows)}))
for folder in ['tools','practice']:
    for file in sorted((root/folder).glob('*')):
        if file.is_file():print('\n'+str(file.relative_to(root))+'\n'+file.read_text())
validator=root/'validate_dataset.py'
if validator.exists():sys.exit(subprocess.call([sys.executable,str(validator)],cwd=root))
print('BLOCKED: official validator is missing');sys.exit(2)
