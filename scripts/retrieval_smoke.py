"""Technical retrieval check using explicitly labelled temporary test fixtures, never official data."""
from pathlib import Path
from tempfile import TemporaryDirectory
from backend.app.config import Settings
from backend.app.rag import RAG
import json
with TemporaryDirectory() as temp:
    root=Path(temp);(root/'kb').mkdir()
    (root/'kb'/'fixture.md').write_text('# Technical test fixture\n\nThis is a test document about blue bicycles, not an official ZentroMart policy.')
    (root/'kb'/'fixture_superseded.md').write_text('# Obsolete fixture\n\nA superseded bicycle document.')
    rag=RAG(Settings(dataset_dir=root,runtime_dir=Path('runtime/retrieval-smoke')))
    sources=rag.search('What does the technical fixture say about blue bicycles?')
    assert sources and all(s['filename']=='fixture.md' for s in sources)
    second=RAG(rag.s);second.build();assert second.chunks==rag.chunks
    result={'status':'passed','purpose':'Technical embedding, FAISS retrieval, source filtering and persisted index reload check; not official-data evaluation','sources':sources}
    Path('sample_outputs/retrieval_smoke.json').write_text(json.dumps(result,indent=2));print('Embedding, FAISS retrieval and reload passed')
