# Midnight Editorial frontend verification

Verified 2026-10-26. Product source changes: frontend/src/main.jsx and frontend/src/style.css only. No backend, provider, dataset, dependency or API contract changes.

- Production build: PASS (`npm --prefix frontend run build`, Vite 6.4.5, 1573 modules).
- Live health: PASS, 20 indexed documents and 102 chunks.
- Session restoration and new conversation: PASS in browser.
- Text submission and processing controls: PASS.
- Live Gemini return-policy answer: PASS, citations RET-2 and RET-4; current pol_returns_v4.md excerpt expanded in browser.
- Live verified order lookup: PASS, official order 86035743, shipped; cancellation CAN-2, delivery DEL-4, refund REF-1/REF-2 rendered.
- Live escalation: PASS, ticket ZT-d47f517fdcb5 displayed. Read-only SQLite query confirmed this ID and order 86035743 persisted.
- Live WAV upload: PASS, sample_outputs/submission_voice.wav sent through the existing upload control; transcript rendered, contextual assistant response returned, audio controls rendered.
- Live returned audio: PASS, play control started playback; audio readyState=4, paused=false, currentTime advanced; centerpiece changed to speaking state.
- Recorded-output UI replay: PASS for long policy answer, eight citation disclosures, order, policy decision, ticket cards, and actual prerecorded Gnani WAV playback. Replay server was isolated on localhost:5189 and did not modify production APIs or data.
- Keyboard: PASS, Enter activated Evaluations and Conversation navigation; disabled empty-send control observed.
- Responsive layout: PASS at 1280, 768, and 390 CSS-pixel widths with document width equal to viewport width; additional narrow 319px embedded-browser view visually inspected.
- Direct microphone capture: INCOMPLETE. Clicking microphone did not resolve the embedded browser's getUserMedia request into recording or a rejection. No successful microphone recording is claimed. Browser WebM conversion also depends on existing FFmpeg availability, which was previously missing.
- Focus, error alert/dismissal, disabled controls and reduced-motion CSS implemented. No exhaustive screen-reader or automated accessibility audit performed.

Screenshots: desktop.png and mobile.png show the actual live frontend after session restoration. Latest-turn sources/audio/tool cards have the same existing non-persistent behavior after reload; message history persists.
