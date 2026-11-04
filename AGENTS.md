# BhashaKhata development rules

- Extend the existing Streamlit and Python app. Preserve the Gnani transcription flow and check official REST documentation before changing request fields.
- Keep credentials in Streamlit secrets. Keep credentials, local ledgers, and real customer data out of Git and public demos.
- Preserve the original transcript. Leave uncertain fields blank and require explicit review and confirmation before saving.
- Store money in integer paise. Use durable request deduplication and append audit entries for reversals.
- Use fictional fixtures and mock Gnani in automated tests. Check credits before deliberate live evaluation and record actual results.
- Use durable storage and access controls before hosting the ledger.
- Run tests, inspect Git status and staged changes for secrets, and update PROJECT_STATUS.md before committing a milestone. Push only with authorization.
