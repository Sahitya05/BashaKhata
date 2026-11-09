# BhashaKhata
**AI-Powered Indian-Language Voice Ledger for Small Businesses**  
*Speak Your Business. Track Every Rupee.*

### The problem
Small shopkeepers often record sales, customer credit, and repayments in paper notebooks. Updating these records during a busy day takes attention away from customers, and missed entries make outstanding balances difficult to track. English-first accounting tools can add another barrier.

### Our solution
BhashaKhata turns short spoken transactions into a ledger entry that the shopkeeper checks before saving. Gnani Prisma is the central speech-recognition component. The app supports an Indian-language workflow with English, Hindi, and Telugu interface labels and optional Gemini translation for display.

A shopkeeper can say, “Ramesh ko 2 kilo rice diya, 130 rupees udhaar mein add karo.” The app preserves the original transcript and proposes fields for supported commands. The shopkeeper selects the customer, corrects any missing or uncertain details, and reviews the exact balance change.

### What makes it different
Our **Verified Voice Transaction Engine** follows **Speak → Review → Confirm → Save**. A supported correction such as “No, amount 130 ka badle 150 karo” updates the pending amount before confirmation. Recognition is a starting point; the shopkeeper remains in control of the financial record.

The ledger distinguishes customer credit, repayments, cash sales, shop borrowing, and money lent. It retains original transcripts and correction history, prevents duplicate saves, and records reversals as linked audit entries. Money is stored in integer paise. Customer balances and downloadable CSV reports make the saved records useful immediately.

### Working prototype and impact
Built with Python, Streamlit, Gnani REST integration, and SQLite, the local prototype includes microphone capture, editable transaction review, explicit save confirmation, customer accounts, and reports. Automated tests use fictional data and mocked APIs; real-world speech accuracy is not yet benchmarked. Hosted persistence and per-shop cloud authentication remain future work.

BhashaKhata aims to make everyday bookkeeping more approachable for small Indian businesses—especially shopkeepers who prefer speaking in their own language. Its practical focus is simple: less time writing accounts, clearer customer balances, and every saved transaction reviewed by the person who understands the business.

**Project repository:** https://github.com/Sahitya05/BashaKhata
