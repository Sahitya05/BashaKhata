# Labeled prompts for live speech evaluation

These are recording scripts with expected labels. Audio collection and scoring are pending.

1. English credit sale. “Ramesh bought 2 rice for 125 rupees on credit.” Ramesh, rice, 2, 12500 paise, credit.
2. Hindi cash sale. “रमेश ने दो चावल के लिए अस्सी रुपये नकद।” रमेश, चावल, 2, 8000 paise, cash.
3. Telugu credit sale. “రమేష్ కొన్నది రెండు బియ్యం ధర ఎనభై రూపాయలు బాకీ.” రమేష్, బియ్యం, 2, 8000 paise, credit.
4. Hindi–English credit sale. “Ramesh ने two rice के लिए eighty रुपये उधार।” Ramesh, rice, 2, 8000 paise, credit.
5. English repayment. “Ramesh repaid 25 rupees.” Ramesh, 2500 paise, repayment.
6. Hindi repayment. “रमेश ने चुकाए पच्चीस रुपये।” रमेश, 2500 paise, repayment.
7. Telugu repayment. “రమేష్ తిరిగి చెల్లించారు ఇరవై ఐదు రూపాయలు.” రమేష్, 2500 paise, repayment.
8. Ambiguous English repayment. “Ramesh repaid either twenty or twenty-five rupees.” Leave extraction blank and cancel.

Record one short clip per prompt with fictional data. Log the date, clip ID, selected language and format, raw transcript, suggested fields, corrections, and outcome. Count an extraction success when every required field matches before editing, or when the ambiguous prompt remains blank. Report both the count over all attempted clips and API failures separately. Run a limited batch after checking account credits.

Live clips attempted: 0. Transcription and extraction success rates are unmeasured.
