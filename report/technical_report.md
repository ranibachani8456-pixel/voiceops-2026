# VoiceOps 2026

ZentroMart AI Voice Customer Support Agent | Consulting & Analytics Club, IIT Guwahati x Gnani.ai | Submission snapshot: 25 October 2026

GitHub source: [https://github.com/ranibachani8456-pixel/voiceops-2026](https://github.com/ranibachani8456-pixel/voiceops-2026)

## 1. Overview and architecture

VoiceOps is a React/Vite/Tailwind support dashboard backed by FastAPI. It combines Gemini generation, official-document retrieval, conversation state, identity-checked synthetic order lookup, persisted human-support tickets and Gnani-only speech. Text flows through session state -> retrieval -> controlled generation/tools -> cited reply. Voice wraps that agent with STT and TTS. SQLite holds sessions, verified context and tickets; FAISS and JSON store vectors and metadata. No unnecessary cloud infrastructure is used.

The official dataset was validated and read without modification. The deployed local configuration points to the extracted dataset in Downloads; portable installations use DATASET_DIR=dataset. The official dataset, credentials, runtime databases and dependencies are excluded from the submission. The frozen business reference date is 20 October 2026.

## 2. Step 1 - baseline LLM

The official Google Gen AI SDK supplies a configurable Gemini model. Baseline mode excludes retrieval and support tools and uses isolated evaluation sessions. The agent discloses its AI identity, returns structured answer/decision/source identifiers, and must not invent policies or completed actions. Earlier real baseline introductions succeeded. Full baseline practice accuracy is not measured: later live verification hit daily quota exhaustion and provider availability/deadline failures. No successful score is inferred from those introductions.

## 3. Step 2 - official RAG

The index contains 20 current documents and 102 chunks. The 21st supplied document, pol_returns_v3_superseded.md, is excluded; front-matter status also excludes superseded content regardless of filename. Chunks retain document, title, version, effective date, type, official section IDs and stable chunk IDs. Current policies outrank guides, help, FAQs and marketing. Sentence Transformers all-MiniLM-L6-v2 produces normalized vectors, searched through FAISS inner product. Content/model fingerprints support persisted-index reuse and rebuilds.

Search selects five semantic candidates above 0.25 similarity, with up to twelve scored sibling sections when a query names a matching document. This preserves conditions and exceptions without hardcoding answers. A real return-policy question retrieved current v4 evidence and generated citations including RET-2, RET-3 and RET-8. Dataset/.env paths were verified after restarting the backend from a different directory. Long indivisible blocks can exceed the nominal chunk target; retrieval calibration remains limited.

## 4. Step 3 - conversation and real tools

Bounded history is separate from durable per-session order/issue state. The official lookup helper reads actual order/customer/item CSV records. An order ID alone reveals no private details; only a submitted phone suffix or delivery pincode unlocks that order. One retry is permitted; proofs are redacted before persistence. Order switching, separate sessions, reset and state reload are tested. The agent cannot execute cancellations or refunds.

Actual order 86035743 is shipped, Standard delivery, UPI, promised for 16 October. Verified controls apply CAN-2 to deny cancellation and REF-1/REF-2 to explain warehouse-receipt initiation and 1-3 business days after initiation for UPI. DEL-4 disallows unauthorized discretionary compensation. Required/requested handovers use SQLite create_ticket. Issue keys atomically deduplicate paraphrases, concurrent requests and retries. Actual ticket ZT-6996d5a9a319 was persisted and retrieved over HTTP after restart. The real helper/policy/storage workflow passed nine checks; this tool-only verification is not presented as a completed LLM chat.

## 5. Step 4 - Gnani speech and batch processing

Gnani's official SDK exclusively supplies STT and timbre-v2.5/Nalini/en-IN TTS. MediaRecorder records browser audio and standard HTML audio plays returned speech. Upload size/duration bounds, opaque filenames and path validation protect processing. The batch runner groups ordered conversation turns, preserves successful transcript/reply/source/tool/audio outputs, records failures and continues other files with a manifest.

The final one-attempt Gnani check succeeded: TTS generated a 143,404-byte 16 kHz WAV and STT returned "hello this is a voice of submission verification using gyani speech". Recognition errors are preserved rather than corrected into a claimed perfect transcript. This verifies speech adapters only, not microphone capture or the current full Gemini voice chain. ffmpeg and ffprobe are absent; tested 16 kHz WAV works directly, while browser WebM conversion remains unverified. A historical earlier-build batch output is included and labelled; it is not final official-data batch accuracy.

## 6. Evaluation methodology and actual results

Final health checks: backend and frontend proxy returned HTTP 200; the persisted index has 20 documents/102 chunks. The React production build passed. Pytest executed 34 tests: all passed, with one third-party TestClient deprecation warning. Tests mock external APIs while official-record cases exercise lookup, identity limits, session/order isolation, remembered policy context, persistence, failure recovery and ticket deduplication. These test counts are not semantic answer-accuracy scores.

All 52 official practice questions were evaluated through the existing cached RAG without Gemini calls. Forty-seven contain KB-section gold evidence. Any-gold-section retrieval hit rate was 33/47 (70.21%); all-gold-KB-section coverage was 16/47 (34.04%). Five questions without KB references were unscored, and product-row references were excluded. Matching uses official section IDs. Because document expansion is included, these are not strict recall@5 values and do not establish correctness of generated answers.

Baseline answer accuracy: not measured. RAG answer accuracy: not measured. Baseline-to-RAG improvement: not measured. Full official conversation success: not measured. A live conversation verified opening, identity gating and real order details; an earlier run also returned a correct cancellation answer. Remaining live turns were blocked by quota/503/504 errors. The latest saved live audit has five passing checks and one failed completion check. Existing real outputs/failures are included; no model retries were made in submission mode. The generation evaluator CLI and exact official-column command are documented for reproduction when provider capacity is available.

## 7. Challenges, limits and next steps

Intel macOS required compatible Python 3.12/PyTorch/NumPy versions and bounded native workers. Native FAISS shared-memory initialization requires execution outside the authoring tool sandbox. Model quota/outage and missing FFmpeg prevent complete final interactive voice/generation validation. Evidence-gated rules do not constitute a complete formal policy engine; overdue-refund business-day escalation and broad adversarial coverage remain unfinished. The synthetic identity flow and bearer sessions need authentication/retention controls before real public customer use.

Next steps after submission: restore Gemini capacity, rerun full baseline/RAG and multi-turn evaluations, install FFmpeg and verify microphone/WebM, expand policy coverage, and record the honest two-minute demo. Bonus capabilities are cited-source inspection, durable verified state, idempotent tickets and grouped batch manifests. No demo footage was recorded or fabricated. Source, setup/run commands, test evidence, real audio, technical report and demo guide are packaged for review.

Evidence: sample_outputs/submission_tests.xml, submission_health.json, submission_voice.json/.wav, submission_retrieval_evaluation.json/.csv, dataset_integration.json, step3_tools_verification.json and step3_verification.json. Code/runtime commands are in README.md. Official integration references: github.com/Gnani-AI-Mintlify/Gnani-Vachana and ai.google.dev/gemini-api/docs/function-calling.
