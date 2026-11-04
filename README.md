# BhashaKhata

A local voice ledger for kirana shops. Record a short transaction with Gnani
Prisma v3.0, review its proposed fields and exact balance effect, then confirm.
SQLite retains confirmed transactions and reversals across restarts.

```powershell
python -m pip install -r requirements-dev.txt
python -m streamlit run app.py
python -m pytest -q
```

Keep your existing `GNANI_API_KEY` in `.streamlit/secrets.toml`. For optional
translation, create a Translator resource in Azure Portal using the F0 tier.
Under **Keys and Endpoint**, copy a key and the resource region into
`AZURE_TRANSLATOR_KEY` and `AZURE_TRANSLATOR_REGION` in the same secrets file.
See `secrets.example.toml` for the format. Manual review works without Azure.

Start with **New voice transaction**. Select speech and display languages,
record one transaction, and transcribe. Select an account explicitly. Review
all fields and confirm the preview. For a fictional practice run, use manual
entry and the examples in [HACKATHON.md](HACKATHON.md). The supported-command
parser leaves unfamiliar phrases for manual review. Real audio evaluation
instructions are in [SPEECH_EVALUATION.md](SPEECH_EVALUATION.md).

The ledger file and credentials are ignored by Git. See
[DEPLOYMENT.md](DEPLOYMENT.md) for the remaining cloud requirements and
[PROJECT_STATUS.md](PROJECT_STATUS.md) for verification status.
