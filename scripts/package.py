"""Package the existing submission from an explicit allowlist; never export secrets/data."""
from pathlib import Path
import hashlib
import json
import zipfile

root = Path(__file__).resolve().parents[1]
allowed = ['README.md', '.env.example', '.gitignore', 'requirements.txt', 'run.py',
           'IMPLEMENTATION_STATUS.md', 'SUBMISSION_CHECKLIST.md', 'backend', 'frontend/src',
           'frontend/index.html', 'frontend/package.json', 'frontend/package-lock.json',
           'frontend/vite.config.js', 'scripts', 'report', 'sample_outputs']
# Include a demo only if the user actually recorded one.
if (root / 'demo.mp4').is_file():
    allowed.append('demo.mp4')
secrets = []
if (root / '.env').exists():
    for line in (root / '.env').read_text().splitlines():
        key, sep, value = line.partition('=')
        if sep and key in {'GEMINI_API_KEY', 'GNANI_API_KEY'} and value.strip():
            secrets.append(value.strip().strip('\"\'').encode())
raw_dataset_names = {'customers.csv', 'orders.csv', 'order_items.csv', 'products.csv',
                     'pincodes.csv', 'holidays.csv', 'support_logs.csv', 'questions.csv',
                     'conversations.csv', 'validate_dataset.py'}
archive_path = root / 'team_name_voiceops.zip'
with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as archive:
    for entry in allowed:
        path = root / entry
        for file in sorted(path.rglob('*')) if path.is_dir() else [path]:
            if not file.is_file() or any(p in {'__pycache__', '.pytest_cache', 'node_modules', '.git'} for p in file.parts):
                continue
            if file.suffix in {'.pyc', '.sqlite3', '.faiss', '.log', '.pem', '.key'} or file.name in raw_dataset_names:
                continue
            if file.name.startswith('.env') and file.name != '.env.example':
                continue
            payload = file.read_bytes()
            if any(secret in payload for secret in secrets):
                raise RuntimeError('Configured credential detected in submission file: ' + str(file.relative_to(root)))
            name = file.relative_to(root).as_posix()
            if name == 'report/report.pdf':
                name = 'report.pdf'
            archive.writestr(name, payload)
with zipfile.ZipFile(archive_path) as archive:
    assert archive.testzip() is None
    names = archive.namelist()
    assert {'README.md', '.env.example', 'requirements.txt', 'run.py', 'report.pdf'} <= set(names)
    assert not any(n == '.env' or n.startswith(('dataset/', 'runtime/', '.git/', '.venv', 'node_modules/')) for n in names)
    assert all(not any(secret in archive.read(name) for secret in secrets) for name in names)
report = {'archive': archive_path.name, 'files': len(names), 'bytes': archive_path.stat().st_size,
          'sha256': hashlib.sha256(archive_path.read_bytes()).hexdigest(),
          'zip_integrity': 'passed', 'configured_secret_scan': 'passed',
          'raw_official_dataset_excluded': True, 'runtime_and_dependencies_excluded': True,
          'demo_included': 'demo.mp4' in names, 'files_in_archive': names}
(root / 'submission_package_check.json').write_text(json.dumps(report, indent=2))
print(json.dumps({k: v for k, v in report.items() if k != 'files_in_archive'}, indent=2))
