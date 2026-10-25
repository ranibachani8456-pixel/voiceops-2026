# Step 3 verification - 25 October 2026

## Result

Implementation/control-flow verification passed. Full live Gemini conversation verification remains incomplete because of provider quota exhaustion and availability/deadline failures. No blocked generation turn is counted as passed; no replacement model replies were fabricated.

## Actual official record

Order **86035743** is **shipped**, Standard delivery, UPI, promised for **16 October 2026**, with 0 earlier contacts. The dataset reference date is 20 October 2026. Order status, amount and item joins were checked against the official CSVs and the supplied identity-gated helper. Verification values are derived only in memory and redacted before conversation/ticket persistence. The official dataset's SHA-256 content fingerprint remained unchanged.

## Implementation fixes

- Replaced the schema-mapping placeholder with a read-only adapter to the inspected official `tools/tools.py:lookup_order`. The helper source is executed without generating files inside the official dataset. Its ticket writer is not invoked; application tickets use SQLite.
- Added persistent session state for current order/issue, per-order verification attempts and safe verified snapshots. State survives history trimming, agent reload and backend restart. Switching orders cannot reuse another order's details.
- Enforced identity checks, one retry, current-message-only proof arguments, and per-turn tool-call idempotency. A model cannot guess verification values or consume two customer attempts by repeating one tool call.
- Removed verification fields from order results and redacted submitted proof before history, tool confirmation, ticket and response persistence.
- Added source-gated cancellation/refund decisions. A shipped order cannot be cancelled under CAN-2. For this prepaid UPI order, a refused/RTO parcel's refund begins on warehouse receipt (REF-1); the current REF-2 table gives 1 to 3 business days after initiation. No initiated refund is falsely claimed.
- Applied DEL-4's prohibition on discretionary compensation, with actual current policy evidence. Human requests and supported escalation conditions authorize ticket creation.
- Added atomic issue-scoped ticket idempotency across paraphrases, concurrent calls and provider retries. A distinct issue can have an identical summary without being merged. Success returns actual `ticket_id`, `created` and `reused` fields.
- Tightened missing-detail replies so the order ID is requested before asking for one verification value. Model context uses concise conversation text plus explicit verified state, rather than repeating old tool payloads.
- Provider quota errors now return HTTP 429; 503/504 availability/deadline failures are reported accurately. Session state and tickets remain durable after provider failure. Thinking effort is configurable; active local model is gemini-3-flash-preview with minimal thinking.

## Executed verification

| Verification | Actual result |
| --- | --- |
| Complete automated suite | **34 passed**, 1 third-party TestClient deprecation warning |
| Actual order/helper and item joins | Passed against official CSV records |
| Missing/malformed/unknown order IDs | Passed; no unverified private details |
| Two-attempt verification lock, guessed-proof rejection, duplicate tool call | Passed |
| Remembered cancellation/refund context after trimming and reload | Passed |
| Separate sessions, reset and switching orders | Passed |
| Exact/paraphrased/concurrent ticket deduplication | Passed |
| Model failure after ticket persistence and retry | Passed with simulated external failure |
| Repeat contact, legal/safety and unauthorized ticket guards | Passed with actual records and mocked generation |
| Independent real tool/policy/storage workflow | **9 checks passed**; no model responses generated or substituted |
| Actual persisted ticket retrieved over HTTP after backend restart | **HTTP 200**, matching ticket ID |
| Official dataset mutation check | Byte-for-byte unchanged |
| Full live Gemini conversation | **Incomplete / blocked** |

Automated tests mock external generation and assess actual application state, official records and policy evidence. They do not establish live model answer correctness for blocked turns. The independent workflow executes actual application tools and persists a real ticket in the application database, but is not represented as a completed LLM-generated chat.

## Actual tools and ticket

The real tool-only workflow called `lookup_order` without proof, then `lookup_order` with customer proof; `assess_order_policy`; and `create_ticket` twice. The second ticket call reused the first ID.

Actual ticket: **ZT-6996d5a9a319**. Database: `runtime/voiceops.sqlite3`. It belongs to order 86035743 and contains the delayed-order issue, verification/checks, intent and handover reason. It was read back from SQLite and through `GET /api/sessions/{session_id}` after backend restart. Official dataset files were not modified.

## Live generation evidence and blockers

The first run obtained actual Gemini replies for delayed-order clarification, order verification, correct order details and a correct CAN-2 cancellation refusal. It then failed on the refund turn with the original model's daily free-tier quota (HTTP 429). That run also exposed a clarification-format issue, subsequently fixed.

A fresh run on gemini-3-flash-preview confirmed the corrected one-question opening, identity gate and actual order details. Subsequent cancellation requests encountered provider 503/504 failures; retries eventually encountered quota exhaustion. The current live report has **5 passing checks and 1 failed completion check**; refund, compensation and handover generation were not completed. The alternate gemini-3.8-flash route also produced availability/deadline failures. These are not claimed as successful integrations.

Actual failed attempts are retained in `sample_outputs/step3_initial_attempt.json`, `step3_alternate_attempt.json`, and `step3_preview_initial_attempt.json`. The latest actual live run, provider failure records and resumable session IDs are in `sample_outputs/step3_verification.json`. Real tool/storage results are in `sample_outputs/step3_tools_verification.json`.

## Reproduce or resume

From the project root, with the backend running:

```sh
.venv312/bin/python -m pytest backend/tests -q
.venv312/bin/python -m scripts.verify_step3_tools
.venv312/bin/python -m scripts.verify_step3 --resume
```

Resume after model quota resets or a Gemini key/model with available capacity is configured and the backend restarted. Resume reuses recorded actual turns and persisted sessions instead of inventing or replaying successful answers. A fresh run is available without `--resume`. The live runner checks actual citations, persisted tickets, separate sessions, invalid IDs, retry limits and dataset integrity. Interrupted/failed runs cannot report full success.

Broad official conversation-set evaluation, overdue-refund business-day escalation and production-grade identity authentication remain outside the completed verification scope. The tested identity flow is the official synthetic training simulation.
