# BhashaKhata

BhashaKhata turns short Kirana shop recordings into editable transactions. The local demo supports cash sales, credit sales, and credit repayments.

## Run on Windows

From the project folder in PowerShell, run:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Put your own API key in the local .streamlit/secrets.toml file:

```toml
GNANI_API_KEY = "your-key-here"
```

Open the local URL printed by Streamlit. Select your interface and speech languages, allow microphone access, record a short clip, and click **Transcribe with Gnani**. Review the original transcript, correct or fill in the form, tick **I verified these details**, and click **Confirm and save**. Open an entry in Transaction history to reverse it. A reversal adds a linked audit entry.

For a fictional demo, record “Ramesh bought 2 rice for 125 rupees on credit,” then “Ramesh repaid 25 rupees.” The expected balance is ₹100. A negative balance represents net payments above the recorded credit. Use consistent customer spelling across transactions. Sales require a customer name, so enter a fictional walk-in label for an anonymous cash sale.

The parser recognizes a small set of command patterns. Use **Numbers and currency** for numeric output and fill in any blank or incorrect fields. Hindi and Telugu interface labels cover the core flow, and some help and error messages are in English. The ledger is saved in the ignored bhashakhata.sqlite3 file next to app.py. This build is for local use with fictional data. Hosted use requires durable storage, access controls, and a separate browser test.

## Test and evaluate

```powershell
python -m unittest -v
```

Automated tests mock Gnani. For live evaluation, check available credits in the [Gnani dashboard](https://app.gnani.ai/) first and use the labeled prompts in [SPEECH_EVALUATION.md](SPEECH_EVALUATION.md).

## Demo recording

Show a fictional credit sale from microphone to confirmation, a repayment, and the updated balance and history. Include an example that needs a manual correction. Report the measured live results and prepare the repository link, deployed demo link once available, and video for the competition submission.
