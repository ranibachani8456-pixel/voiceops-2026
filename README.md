# VoiceOps 2026 - ZentroMart AI Voice Customer Support

GitHub source: [https://github.com/ranibachani8456-pixel/voiceops-2026](https://github.com/ranibachani8456-pixel/voiceops-2026)

Capstone for Consulting & Analytics Club, IIT Guwahati x Gnani.ai. React/Vite/Tailwind frontend; FastAPI backend; Gemini baseline/conversation agent; Sentence Transformers + FAISS retrieval; identity-checked official order lookup; SQLite sessions/tickets; Gnani-only STT/TTS.

## Submission status - 25 October 2026

| Check | Verified result |
| --- | --- |
| Official dataset | Validator passed; source files unchanged |
| Knowledge base | 20 current documents, 102 persisted chunks; superseded returns v3 excluded |
| Automated suite | 34 passed; external generation/speech are mocked in unit tests |
| Real order/policy/ticket workflow | 9 checks passed; real ticket read over HTTP after restart |
| Frontend build / backend / frontend proxy | Build passed; both health endpoints HTTP 200 |
| Final Gnani voice check | One real TTS-to-STT 16 kHz WAV round trip passed; actual audio/transcript included |
| Retrieval-only practice evaluation | 52 processed; 33/47 any-gold-section hits (70.21%); 16/47 all-gold-KB-section hits (34.04%) |
| Baseline/RAG answer accuracy and improvement | Not measured; Gemini quota/503/504 prevented complete generation evaluation |
| Full current live multi-turn/voice chain | Not fully verified because of Gemini failures |
| Browser microphone/WebM | Not verified; ffmpeg/ffprobe missing on the authoring machine |
| Demo recording | Not recorded; demo guide supplied; no fabricated video |

Retrieval scores are **not answer accuracy**. Five questions had no KB-section reference and were not scored; product-row references were excluded. Retrieval uses TOP_K=5 semantic candidates plus existing document-context expansion, so these are not strict recall@5 figures. Detailed real outputs and failure evidence are under `sample_outputs/`. Read `report/technical_report.md` and the included PDF for limitations.

## Setup on a new machine

Use Python **3.12**, Node **20+**, and npm. Pinned ML versions were verified on Intel macOS. The official dataset and API credentials are deliberately excluded from this repository/ZIP.

```sh
python3.12 -m venv .venv312
source .venv312/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
npm --prefix frontend ci
```

Edit `.env` and configure:

```dotenv
GEMINI_API_KEY=your_key
GNANI_API_KEY=your_key
GEMINI_MODEL=gemini-3-flash-preview
GEMINI_THINKING_LEVEL=low
DATASET_DIR=dataset
RUNTIME_DIR=runtime
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
TTS_MODEL=timbre-v2.5
TTS_VOICE=Nalini
LANGUAGE=en-IN
```

Do not overwrite an already configured local `.env`, commit it, or include it in a submission. `GEMINI_THINKING_LEVEL` must be supported by the selected model; empty uses its default. The final local configuration uses minimal thinking. Gemini availability/quota is account-dependent; configuration presence does not imply a successful API call. `TOP_K`, `MAX_AUDIO_BYTES` (default 15 MiB), and `MAX_AUDIO_SECONDS` (default 60) are also configurable.

### Official dataset

Extract `Capstone_Project_Dataset_FTTT_2026.zip` so these paths exist:

```text
dataset/README.md
dataset/DATA_DICTIONARY.md
dataset/ZIP_SCHEMA.md
dataset/CHANGELOG.md
dataset/validate_dataset.py
dataset/kb/*.md
dataset/data/*.csv
dataset/practice/*.csv
dataset/tools/tools.py
```

If extraction creates a containing `Capstone_Project_Dataset_FTTT_2026/` folder, set `DATASET_DIR` to that containing folder instead. Absolute paths are supported. Paths and `.env` discovery are anchored to this project root, not the launch directory. On the author's machine the existing dataset is `/Users/ranib/Downloads/Capstone_Project_Dataset_FTTT_2026`; it is read in place and not included in the submission.

```sh
python dataset/validate_dataset.py
python -m scripts.rebuild_index
```

For an external dataset path, run its `validate_dataset.py` using that actual path. First embedding use downloads the configured Sentence Transformers model. Later runs reuse local cache/index; `HF_HUB_OFFLINE=1` can be set after a complete model download. Index loading is lazy after backend restart. An immediate health check may report zero in-memory indexed chunks while the validated persisted index still contains 102 chunks.

### FFmpeg

For browser WebM or non-16 kHz inputs, install **both ffmpeg and ffprobe** and place them on PATH, for example on macOS:

```sh
brew install ffmpeg
ffmpeg -version
ffprobe -version
```

They were absent at submission time. The tested 16 kHz mono WAV path works directly through soundfile without these binaries. Browser recording needs microphone permission and localhost/HTTPS. No browser speech-recognition/synthesis API is used.

## Run

From the project root, in two terminals:

```sh
.venv312/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

```sh
npm --prefix frontend run dev
```

Open http://localhost:5173. API docs: http://127.0.0.1:8000/docs. Health: http://127.0.0.1:8000/api/health. The frontend development proxy forwards `/api` to port 8000. The production frontend is checked with `npm --prefix frontend run build`; no public deployment is claimed.

## Tests and evaluation

```sh
.venv312/bin/python -m pytest backend/tests -q
npm --prefix frontend run build
.venv312/bin/python -m scripts.verify_step3_tools
```

The tool verification command creates a test session and actual SQLite ticket using an official synthetic order; it does not require a successful model reply. Unit tests use actual records for order/state tests and mock external APIs. If the official dataset is absent, official-record tests are skipped rather than counted as verified.

The existing full generation evaluator uses the actual official column names:

```sh
.venv312/bin/python -m scripts.evaluate --questions dataset/practice/questions.csv --id-column id --question-column question --decision-column expected_decision --decision-map '{"answer":"answer","clarify":"clarify","escalate":"escalate","refuse":"refuse"}'
```

For an external dataset, substitute its absolute practice-file path. This makes paid/quota-consuming API calls. It was **not rerun in submission mode** because provider quota/availability was already blocked. The CLI was checked with `--help`; available actual responses and failures were preserved. Its mapped decision agreement is not semantic answer accuracy and does not currently score all `acceptable_decisions` alternatives. Output: runtime/evaluation.json and .csv; dashboard displays these only after an actual run.

Current retrieval-only results are saved in `sample_outputs/submission_retrieval_evaluation.json` and .csv. All 52 official questions were passed through the existing cached `RAG.search(question)` without Gemini calls; matching uses official `gold_evidence` KB section IDs. Baseline answer accuracy, RAG answer accuracy and improvement are explicitly null.

For live Step 3 verification when provider capacity is available:

```sh
.venv312/bin/python -m scripts.verify_step3
```

The author's current saved session can be resumed with `--resume`; fresh installations should start without that flag because local SQLite state is excluded from the package. The runner records actual responses, citations, errors, tool results, identity limits, session isolation and duplicates; failed/interrupted runs are not reported as completed. Avoid repeatedly running it while quota is exhausted.

## Batch audio - submission command

```sh
.venv312/bin/python run.py --input_dir ./test_audio --output_dir ./outputs
```

Optional ordered-conversation metadata:

```sh
.venv312/bin/python run.py --input_dir ./test_audio --output_dir ./outputs --metadata ./turns.json
```

```json
[{"file":"turn1.wav","conversation_id":"call1","turn":1},{"file":"turn2.wav","conversation_id":"call1","turn":2}]
```

Without metadata each audio file gets a new session. WAV, MP3, WebM, OGG, M4A and FLAC are accepted subject to format/tool support. Every item saves JSON/text, transcript/reply/sources/tools when available, generated WAV on success, and error details on failure. `manifest.json` gives actual completion counts. Files are size/duration limited, path traversal is rejected, and failed items do not stop other items. Do not claim batch completion when Gemini is unavailable.

## Architecture and limitations

Text: browser -> FastAPI -> session state -> FAISS sources -> Gemini controlled workflow -> official identity-gated lookup / SQLite ticket -> cited reply. Voice wraps the same agent with Gnani STT and explicit timbre-v2.5 TTS. Retrieved documents/user content are untrusted data, not executable instructions. Current policies outrank FAQs/marketing; superseded files/statuses are excluded. Document/version/section metadata and content fingerprints support citations and rebuilds.

SQLite retains bounded history separately from verified order/issue state. Verification asks for one submitted phone suffix or pincode, permits one retry, and never exposes expected values. Ticket issue keys are atomic and deduplicate paraphrases/retries; genuinely separate issues use separate keys. The assistant cannot execute cancellations, refunds or discretionary compensation. Tested policy decisions are evidence-gated; this is not a complete formal policy engine. Overdue-refund business-day escalation and full official multi-turn evaluation remain incomplete. This synthetic verification flow, bearer sessions and opaque audio URLs require further authentication/retention controls before public customer deployment.

Endpoints: POST /api/sessions; GET/DELETE /api/sessions/{id}; POST /api/chat; POST /api/voice/turn (multipart `session_id`, `audio`); GET /api/audio/{name}; GET /api/health; GET /api/evaluations.

## Submission and GitHub

```sh
.venv312/bin/python scripts/package.py
```

Produces **team_name_voiceops.zip**, with the technical PDF at archive root as `report.pdf`. It excludes `.env`, keys, official dataset files, runtime databases/indexes/logs, virtual environments, node_modules and .git. Sample outputs are generated evaluation/test evidence, not raw dataset copies. Historical samples are labelled separately from final verification in `sample_outputs/README.md`.

No demo.mp4 exists: use `report/demo_script.md` to record an honest walkthrough if time permits. Do not stage or submit an invented video. The submission source is published at https://github.com/ranibachani8456-pixel/voiceops-2026. The official dataset and credentials are excluded. Follow `SUBMISSION_CHECKLIST.md` for final manual steps. Rename `team_name` to the actual team name if the portal requires it.

Official SDK references: https://github.com/Gnani-AI-Mintlify/Gnani-Vachana and https://ai.google.dev/gemini-api/docs/function-calling.
