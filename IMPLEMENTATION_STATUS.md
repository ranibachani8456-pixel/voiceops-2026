# Final submission status - 25 October 2026

Submission mode: application development stopped. Only health/evaluation checks, documentation, sample evidence and packaging were performed in this mode. Application architecture and existing functionality were preserved.

## Verified

- Official dataset validated and unchanged; external source path is /Users/ranib/Downloads/Capstone_Project_Dataset_FTTT_2026. No raw dataset copy is packaged.
- Actual persisted Sentence Transformers/FAISS index: 20 current documents, 102 chunks; superseded returns v3 excluded. A prior real return-policy answer and restart verification are saved.
- Current backend and frontend proxy: HTTP 200. Index loads lazily; persisted counts and in-memory counts are distinct immediately after restart.
- Final React production build: passed (1,573 transformed modules).
- Final pytest run: 34 passed, one third-party TestClient deprecation warning; JUnit output included. Official-record tests use actual records; external APIs are mocked in unit tests.
- Real Step 3 helper/policy/SQLite workflow: nine checks passed. Actual ticket ZT-6996d5a9a319 persisted, duplicate request reused it, and HTTP readback passed after restart.
- Final Gnani check: exactly one actual TTS call and one STT call succeeded; timbre-v2.5, Nalini, en-IN, 143,404-byte 16 kHz WAV. Actual recognition errors retained in transcript.
- Retrieval-only evaluation: 52 official questions processed, 47 scored for KB evidence; any-gold hit 33/47 (70.21%), all-gold-KB coverage 16/47 (34.04%). Product-row references excluded. Not answer accuracy and not strict recall@5.

## Explicit limitations / missing artifacts

- Full current live Gemini conversation and current full voice chain remain incomplete: daily quota/503/504 failures. No Gemini retry was made in submission mode.
- Baseline generated-answer accuracy, RAG generated-answer accuracy, their improvement, and full conversation success are not measured. No scores were invented.
- ffmpeg and ffprobe are missing. Browser microphone/WebM conversion is unverified; the tested 16 kHz WAV adapter path works without them.
- No demo.mp4 was recorded; an honest recording guide is supplied.
- Broad adversarial/policy certification, overdue-refund business-day escalation and production authentication remain incomplete.
- GitHub source published at https://github.com/ranibachani8456-pixel/voiceops-2026. Portal upload and any mandatory demo recording remain manual steps.

## Deliverables

README.md; .env.example; requirements.txt; run.py; existing backend/frontend source and tests; report/report.pdf (ZIP root report.pdf); report/technical_report.md; report/step3_verification.md; report/demo_script.md; real sample_outputs; SUBMISSION_CHECKLIST.md; team_name_voiceops.zip; external package audit submission_package_check.json.

Package creation uses an explicit allowlist, maps the report PDF to the archive root, excludes keys/.env/raw official data/runtime/dependencies/.git, verifies ZIP integrity, and scans all archived payloads for the configured credential values. The local credential file is retained only for the working application and is ignored by Git.
