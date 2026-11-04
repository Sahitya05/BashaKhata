# Project status

## November 4 rebuild

- Added independent accounts, settlement previews, borrowing and lending, verified
  corrections, reporting and append-only reversals. Backed up prior source and
  the local SQLite database before edits. Preserved the existing Gnani secrets.
- Verified the REST request contract against Gnani documentation. Owner reports
  roughly 4,500 credits left. Automated tests use mocks. Live audio and Azure
  translation are pending verification.
- Cloud persistence and shop access controls remain pending. See DEPLOYMENT.md
  and HACKATHON.md for deployment and submission preparation.

## November 4, 2026 repository inspection

- Tracked files were app.py, requirements.txt, and .gitignore. app.py had local changes and info.txt was untracked.
- The configured remote is https://github.com/Sahitya05/BashaKhata.git.
- The existing app had microphone capture, Prisma v3.0 REST integration, language and format settings, and vocabulary hints. The handoff reports prior live transcription success.
- The translation block had a misindented exception handler and depended on a rate-limited third-party translator.
- There was no ledger, extraction, confirmation flow, or automated test suite.

## Tested local milestone

- The original Gnani transcript feeds an editable form. Cash sales, credit sales, and repayments require a verification checkbox and a save action.
- The local SQLite ledger stores integer paise, ignores repeated saves of identical audio, and preserves original transcripts, confirmed details, and linked reversals.
- Replaced third-party whole-transcript translation with built-in labels for the core English, Hindi, and Telugu interface. Transcribe mode is the default because Gnani formats spoken numbers as digits in that mode.
- Seven automated tests passed with Python 3.12.7 and Streamlit 1.62.0. They cover a mocked voice-to-balance flow, confirmation, cancellation, corrections, extraction, validation, HTTP failures, duplicate saves, persistence, and recovery.
- Live microphone and Gnani validation remain pending. The remaining credit balance is unknown. SPEECH_EVALUATION.md has labeled recording prompts and no measured results yet.
- Hosted database, access controls, deployment, and independent browser verification remain pending.

## Rebuild verification

- Final command: python -m pytest -q. Result: 59 passed. The preceding run found a draft widget reset after amount correction, fixed and verified by the final run.
- The mocked four-recording flow reached INR 200, 280, 180 and 0 with all four entries preserved. No live calls were made.
- The local milestone is ready for commit. No push, public deployment, post or submission was performed.
