# Final submission checklist

Prepared 25 October 2026. No application architecture or new features were changed in submission mode.

## Included

- README with exact setup/run/evaluation/batch instructions and environment placeholders.
- Existing backend/frontend source, tests and locked frontend dependencies (package-lock.json, not node_modules).
- Maximum-four-page report, placed at ZIP root as report.pdf; editable report source under report/.
- 34 passing-test JUnit evidence; actual health, retrieval, Gnani audio, policy/source and ticket outputs.
- Explicit failed/live-blocked evaluation evidence and demo recording guide.

## Excluded

API keys/.env, official dataset documents/tables/archive, runtime SQLite/index/model cache/logs, virtual environments, node_modules, .git and fabricated demo footage. Citations and derived evaluation outputs are retained as review evidence, not raw dataset copies.

## Required manual steps

1. Replace team_name in the ZIP filename with the actual team name if required by the submission portal.
2. Use the published repository URL if the portal requests GitHub: https://github.com/ranibachani8456-pixel/voiceops-2026. Never upload the local .env or official dataset.
3. If demo.mp4 is mandatory, record the honest two-minute walkthrough from report/demo_script.md, then rerun scripts/package.py. No video exists in this package.
4. Upload the ZIP and any required GitHub/video links to the course portal before midnight Asia/Kolkata. Save the portal acknowledgement.

## Optional after deadline-critical upload

Install ffmpeg/ffprobe and test browser WebM; restore Gemini quota/capacity and run full generated-answer/multi-turn evaluation. Do not delay a required upload for these unresolved integrations.

## Local source-to-GitHub commands

For an independent copy, extract this ZIP into a fresh directory and configure your own Git name/email. The original repository is already published. Example commands for a new repository:

```sh
git init
git add README.md .env.example .gitignore requirements.txt run.py backend frontend scripts report sample_outputs IMPLEMENTATION_STATUS.md SUBMISSION_CHECKLIST.md report.pdf
git commit -m "Submit VoiceOps 2026 capstone"
git branch -M main
git remote add origin YOUR_EMPTY_GITHUB_REPOSITORY_URL
git push -u origin main
```

The repository URL is a placeholder; replace it with your own. No API credentials belong in Git. For verification, scan ZIP contents and retain the generated submission package check JSON/checksum outside the upload source.
