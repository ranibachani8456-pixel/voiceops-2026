"""Rebuild the official KB index using the same configuration as the backend."""
import json

from backend.app.config import settings
from backend.app.rag import RAG


def main():
    rag = RAG(settings)
    rag.build(force=True)
    report = {
        'dataset_path': str(settings.dataset_dir),
        'kb_path': str(settings.dataset_dir / 'kb'),
        'documents': len({c['filename'] for c in rag.chunks}),
        'chunks': len(rag.chunks),
        'indexed_files': sorted({c['filename'] for c in rag.chunks}),
        'index_path': str(settings.runtime_dir / 'index' / 'vectors.faiss'),
        'fingerprint': rag.fingerprint,
    }
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
