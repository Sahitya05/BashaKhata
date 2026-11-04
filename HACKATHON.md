# BhashaKhata — submission preparation

**Subtitle:** AI-Powered Indian-Language Voice Ledger for Small Businesses.
**Tagline:** Speak Your Business. Track Every Rupee.

## Project explanation draft

BhashaKhata helps a kirana shopkeeper record customer credit and repayments from
short spoken transactions. Gnani Prisma v3.0 supplies the original transcript.
A conservative multilingual parser proposes details, then the shopkeeper
selects the exact account, edits the draft, reviews the balance effect and
explicitly confirms it. SQLite appends the verified record using integer paise.
Original transcripts and linked reversals remain available for review.

The local MVP also separates money borrowed by the shop from customer credit
and money lent, supports full customer-credit settlement from the current
balance, and protects against duplicate saves. Optional Azure Translator provides
display translations; it never controls accounting amounts or direction.

The distinctive mechanism is the **Verified Voice Transaction Engine**. An
explicit supported correction such as “No, amount 130 ka badle 150 karo” changes
the pending amount and preserves both the original transcript and correction.
Nothing is saved until the shopkeeper confirms the final preview.

This is a reviewed customer ledger, not audited double-entry accounting. Broad
arbitrary-language extraction, hosted persistence and per-shop cloud access
controls are not complete. Real speech accuracy has not yet been measured.

## Technical architecture

Microphone -> `speech.py` (Gnani REST) -> original transcript -> `extraction.py`
-> editable Streamlit draft -> immutable confirmation preview -> `ledger.py`
-> SQLite accounts and append-only transactions -> ledger and CSV reports.

`translation.py` independently sends the transcript to official Azure Translator
when configured. `i18n.py` supplies built-in English, Hindi and Telugu UI labels.
Tests use fictional records and mocked API responses; no speech credits are used.

## 60-second demonstration plan

- 0–5s: Introduce a fictional shop and the verification workflow.
- 5–17s: Record “Ramesh ko 2 kilo rice diya, 130 rupees udhaar mein add karo.”
  Show the real Gnani transcript. If translation is configured, show its output;
  otherwise clearly show that it is unavailable.
- 17–30s: Create a fictional account. Record the supported correction
  “No, amount 130 ka badle 150 karo.” Review the ₹150 preview and confirm.
- 30–43s: Record “Ramesh paid 50 rupees.” Explicitly select the existing account;
  review ₹150 -> ₹100 and confirm.
- 43–53s: Open the ledger and show both records and the ₹100 balance.
- 53–60s: Show original/correction history and the Telugu interface. State
  the tested scope and remaining limitations.

Rehearse with actual microphone recordings first. If recognition fails, show the
correction honestly. Do not present offline text entry or mocked tests as live
speech. A separate Telugu clip can use “రమేష్ కి రెండు వందల రూపాయలు బాకీ రాయి.”
Use a fresh fictional account so balances are reproducible.

## Contribution record — fill with actual work

- Member 1: name, implementation responsibilities, tests/demo work actually done.
- Member 2: name, implementation responsibilities, tests/demo work actually done.
- Disclose AI-assisted implementation where requested. Do not invent contributions.

## Public post draft — revise after genuine live demonstration

We’re building BhashaKhata, an Indian-language voice ledger for kirana stores.
Using Gnani Prisma, a shopkeeper can speak a supported transaction, review its
details, correct a pending amount and confirm the balance update. Our local MVP
preserves transaction history and separates customer credit from shop borrowing.

Watch our genuine demo: [ADD VIDEO LINK]
Tested scope and limitations: [ADD PROJECT LINK]
Tag Gnani AI’s official account.

#GnaniAI #GreatIndianAIInternshipChallenge

## Submission checklist

- [ ] Check model access in the owner's Gnani dashboard.
- [ ] Complete live Hindi, Telugu and code-mixed evaluations with actual results.
- [ ] Record and publish the genuine demo video after owner approval.
- [ ] Fill both teammates' contributions accurately.
- [ ] Publish the approved LinkedIn or X post and retain its URL.
- [ ] Provide the model/API details and written explanation.
- [ ] Submit through the official programme process after owner approval.

Official challenge page checked November 4, 2026:
https://www.gnani.ai/internship
It lists a November 10, 2026, 11:59 PM IST deadline, a working Gnani-based app,
demo video, project explanation, model/API details, and nominated social posts.
The public post must exist before submission. The regional-language, mixed-voice,
and real-world utility categories fit the intended demo; awards are not guaranteed.
