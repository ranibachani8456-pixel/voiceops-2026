# Evidence inventory

Final submission checks (25 October 2026):

- submission_health.json: actual backend/frontend-proxy HTTP 200, persisted 20-document/102-chunk index, missing ffmpeg/ffprobe. In-memory index counts can be zero immediately after restart because loading is lazy.
- submission_tests.xml: actual final pytest JUnit report, 34 passing tests. External generation/speech calls are mocked in unit tests.
- submission_voice.json and submission_voice.wav: one real final Gnani timbre-v2.5/Nalini/en-IN TTS-to-STT 16 kHz WAV round trip. Recognition errors are retained, including "voice of"/"gyani". No Gemini or microphone claim is attached to this check.
- submission_retrieval_evaluation.json/.csv: all 52 official practice questions processed by existing RAG, 47 with KB evidence. 33 any-section hits; 16 all-KB-section hits. Product-row evidence excluded. These are retrieval scores, NOT model answer accuracy.
- step3_tools_verification.json: actual official helper/policy/SQLite workflow, 9 passing checks and HTTP readback after restart of real ticket ZT-6996d5a9a319.
- step3_verification.json: incomplete real Gemini conversation, with actual recorded turns and provider failures. It is intentionally not marked passed. Initial/alternate attempt files preserve the audit trail.
- dataset_integration.json: successful earlier actual official return-policy answer/citations and restart verification.

Historical, earlier-build evidence:

- integration_smoke.json, http_chat_smoke.json, http_voice_smoke.json: real earlier provider/HTTP successes; not reruns of the final quota-blocked Gemini chain.
- batch_smoke/: actual earlier one-file audio batch, generated WAV and manifest. This was before official KB integration; its missing-KB warning is retained. Do not present it as final official-data batch accuracy.
- retrieval_smoke.json: explicitly labelled temporary technical fixture for index mechanics, not official company data or official evaluation.
- dashboard.png: historical actual rendered frontend screenshot.

No scores, speech or responses in these files were invented to substitute for failed live calls. Baseline/RAG generated-answer accuracy and improvement are not available. Raw official dataset tables, runtime SQLite databases and credentials are excluded from the submission.
