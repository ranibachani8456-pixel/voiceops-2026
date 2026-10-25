"""Regression tests for launch-directory-independent paths and official metadata."""
from pathlib import Path
import os
import subprocess
import sys

from backend.app.config import PROJECT_ROOT, Settings
from backend.app.rag import load_chunks


def test_relative_paths_resolve_from_project_root(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    settings = Settings(_env_file=None, dataset_dir='dataset', runtime_dir='runtime')
    assert settings.dataset_dir == PROJECT_ROOT / 'dataset'
    assert settings.runtime_dir == PROJECT_ROOT / 'runtime'


def test_env_file_loaded_after_restart_from_other_directory(tmp_path):
    # New interpreter proves both .env discovery and path resolution survive restart.
    env = {k: v for k, v in os.environ.items() if k not in {'DATASET_DIR', 'RUNTIME_DIR'}}
    env['PYTHONPATH'] = str(PROJECT_ROOT)
    code = 'from backend.app.config import settings; print(settings.dataset_dir); print(settings.runtime_dir)'
    result = subprocess.run([sys.executable, '-c', code], cwd=tmp_path, env=env,
                            check=True, capture_output=True, text=True)
    paths = result.stdout.splitlines()
    assert Path(paths[0]) == Settings().dataset_dir
    assert Path(paths[1]) == Settings().runtime_dir


def test_frontmatter_status_and_section_metadata(tmp_path):
    (tmp_path / 'policy.md').write_text('---\ndoc_id: TEST\ntitle: Test policy\ndoc_type: policy\nversion: 4.0\nstatus: current\neffective_from: 2026-08-01\n---\n# Test\n\n## [TEST-1] Window\n\nTechnical fixture only.')
    # Obsolete content is excluded even without "superseded" in its filename.
    (tmp_path / 'old.md').write_text('---\nstatus: superseded\n---\n# Old fixture')
    chunks = load_chunks(tmp_path)
    assert {c['filename'] for c in chunks} == {'policy.md'}
    section = next(c for c in chunks if c['section_id'] == 'TEST-1')
    assert section['doc_id'] == 'TEST'
    assert section['doc_type'] == 'policy'
    assert section['version'] == '4.0'
    assert section['status'] == 'current'
    assert section['effective_from'] == '2026-08-01'
    assert 'doc_id:' not in section['text']

def test_named_policy_question_keeps_conditions_and_exceptions(monkeypatch, tmp_path):
    import numpy as np
    from types import SimpleNamespace
    from backend.app.rag import RAG
    kb = tmp_path / 'kb'
    kb.mkdir()
    (kb / 'policy.md').write_text('# Test policy\n\n## [TEST-1] Scope\n\nTechnical fixture scope.\n\n## [TEST-2] Conditions\n\nTechnical fixture conditions.\n\n## [TEST-3] Exceptions\n\nTechnical fixture exception.')
    class Embedder:
        def __init__(self, *args, **kwargs):
            pass
        def encode(self, texts, **kwargs):
            return np.array([[1., 0.] for _ in texts], dtype='float32')
    monkeypatch.setitem(sys.modules, 'sentence_transformers', SimpleNamespace(SentenceTransformer=Embedder))
    rag = RAG(Settings(dataset_dir=tmp_path, runtime_dir=tmp_path / 'runtime', top_k=1))
    result = rag.search('What is the test policy?')
    assert {'TEST-1', 'TEST-2', 'TEST-3'} <= {c['section_id'] for c in result}
    assert any(c['retrieval_role'] == 'document_context' for c in result)
