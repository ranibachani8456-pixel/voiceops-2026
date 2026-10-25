import hashlib
import json
import os
import re
import threading
from pathlib import Path

# Bound native embedding workers on Intel macOS; unrestricted BLAS/OpenMP
# parallelism can crash the process while embedding the full KB.
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('VECLIB_MAXIMUM_THREADS', '1')
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')

import numpy as np

# Bump when chunking/embedding representation changes to invalidate old indexes.
INDEX_FORMAT = 2


def document_parts(path):
    """Parse the official flat Markdown front matter without executing document content."""
    text = path.read_text(encoding='utf-8')
    metadata = {}
    match = re.match(r'\A---\s*\n(.*?)\n---\s*(?:\n|$)', text, re.S)
    if match:
        for line in match.group(1).splitlines():
            key, separator, value = line.partition(':')
            if separator:
                metadata[key.strip()] = value.strip().strip('\"\'')
        text = text[match.end():]
    return metadata, text


def load_chunks(directory):
    chunks = []
    for path in sorted(Path(directory).glob('*.md')):
        metadata, text = document_parts(path)
        if 'superseded' in path.name.lower() or metadata.get('status', '').lower() == 'superseded':
            continue
        title = metadata.get('title') or next(
            (line.lstrip('# ').strip() for line in text.splitlines() if line.startswith('#')), path.stem
        )
        version_match = re.search(r'_v(\d+)', path.stem)
        base = dict(
            filename=path.name, title=title, doc_id=metadata.get('doc_id'),
            doc_type=metadata.get('doc_type'), status=metadata.get('status', 'current'),
            version=metadata.get('version', version_match.group(1) if version_match else None),
            effective_from=metadata.get('effective_from'), language=metadata.get('language'),
        )
        heading = title
        for section in re.split(r'(?m)(?=^#{1,6} )', text):
            if not section.strip():
                continue
            if section.startswith('#'):
                heading = section.splitlines()[0].lstrip('# ').strip()
            section_match = re.search(r'\[([A-Z][A-Z0-9.-]*)\]', heading)
            section_id = section_match.group(1) if section_match else None
            # Keep policy tables and lists intact; overlap only within long sections.
            current = ''
            for block in re.split(r'\n\s*\n', section):
                if len(current) + len(block) > 1600 and current:
                    chunks.append(dict(base, heading=heading, section_id=section_id, text=current.strip()))
                    current = current[-220:] + '\n' + block
                else:
                    current += '\n' + block
            if current.strip():
                chunks.append(dict(base, heading=heading, section_id=section_id, text=current.strip()))
    for chunk in chunks:
        chunk['chunk_id'] = hashlib.sha256((chunk['filename'] + chunk['text']).encode()).hexdigest()[:20]
    return chunks


class RAG:
    def __init__(self, settings):
        self.s = settings
        self.model = None
        self.index = None
        self.chunks = []
        self.fingerprint = None
        self._lock = threading.RLock()

    def build(self, force=False):
        with self._lock:
            return self._build(force)

    def _build(self, force):
        kb_dir = self.s.dataset_dir / 'kb'
        chunks = load_chunks(kb_dir)
        if not chunks:
            raise ValueError(f'Official knowledge base missing or empty at {kb_dir}; configure DATASET_DIR to the extracted dataset root')
        os.environ.setdefault('HF_HOME', str((self.s.runtime_dir / 'huggingface').resolve()))
        import faiss
        from sentence_transformers import SentenceTransformer

        fingerprint = hashlib.sha256(json.dumps(
            dict(format=INDEX_FORMAT, model=self.s.embedding_model, chunks=chunks), sort_keys=True
        ).encode()).hexdigest()
        if not force and self.index is not None and fingerprint == self.fingerprint:
            return
        self.model = self.model or SentenceTransformer(self.s.embedding_model)
        folder = self.s.runtime_dir / 'index'
        folder.mkdir(parents=True, exist_ok=True)
        meta = folder / 'metadata.json'
        idx = folder / 'vectors.faiss'
        if not force and meta.exists() and idx.exists() and json.loads(meta.read_text()).get('fingerprint') == fingerprint:
            self.index = faiss.read_index(str(idx))
        else:
            # Repeated document titles give section chunks their document context.
            texts = [f"{c['title']}\n{c['heading']}\n{c['text']}" for c in chunks]
            vectors = np.asarray(self.model.encode(texts, normalize_embeddings=True), dtype='float32')
            self.index = faiss.IndexFlatIP(vectors.shape[1])
            self.index.add(vectors)
            faiss.write_index(self.index, str(idx))
            meta.write_text(json.dumps(dict(fingerprint=fingerprint, chunks=chunks), ensure_ascii=False))
        self.chunks = chunks
        self.fingerprint = fingerprint

    def search(self, question):
        with self._lock:
            self.build()
            vector = np.asarray(self.model.encode([question], normalize_embeddings=True), dtype='float32')
            scores, ids = self.index.search(vector, len(self.chunks))
            ranked = [dict(self.chunks[int(i)], score=float(score))
                      for score, i in zip(scores[0], ids[0]) if i >= 0 and score >= 0.25]
            primary = ranked[:self.s.top_k]
            # A broad question naming a document needs its conditions/exceptions,
            # not just its semantically closest section. Expand that parent document
            # with actual scored sibling sections, never synthesized policy text.
            def words(text):
                return {word.removesuffix('s') for word in re.findall(r'\w+', text.lower())}
            query_words = words(question)
            parents = {c['filename'] for c in primary
                       if len(words(c['title'])) >= 2 and words(c['title']) <= query_words}
            seen = {c['chunk_id'] for c in primary}
            siblings = [dict(c, retrieval_role='document_context') for c in ranked
                        if c['filename'] in parents and c['section_id'] and c['chunk_id'] not in seen]
            return [dict(c, retrieval_role='semantic_match') for c in primary] + siblings[:12]
