"""Conservative supported commands, not arbitrary-language understanding.

Names/products are captures, never a customer dictionary. Unsupported or ambiguous
sentences return no suggestions. The original transcript is never overwritten.
"""
import re
import unicodedata
from legacy_ledger import extract as legacy_extract

WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "twenty": 20,
    "thirty": 30, "forty": 40, "fifty": 50, "eighty": 80,
    "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पाँच": 5, "दस": 10,
    "बीस": 20, "तीस": 30, "पचास": 50, "अस्सी": 80,
    "ek": 1, "do": 2, "teen": 3, "bees": 20, "tees": 30,
    "ఒక": 1, "ఒకటి": 1, "రెండు": 2, "మూడు": 3, "నాలుగు": 4,
    "ఐదు": 5, "పది": 10, "ఇరవై": 20, "ముప్పై": 30, "యాభై": 50, "ఎనభై": 80,
}
SCALES = {"hundred": 100, "सौ": 100, "sau": 100, "వంద": 100, "వందల": 100,
          "thousand": 1000, "हजार": 1000, "వెయ్యి": 1000, "వేల": 1000}
NUM = r"[0-9]+(?:\.[0-9]{1,2})?"
CUR = r"(?:rupees?|rupaye|rupe|रुपये|रुपए|రూపాయలు)"
MONEY = rf"(?:₹\s*)?(?P<amount>{NUM})\s*{CUR}"
NAME = r"(?P<customer>[^\d,;.!?₹]+?)"

def normalize(text):
    text = "".join(str(unicodedata.decimal(c)) if c.isdecimal() else c for c in text)
    text = unicodedata.normalize("NFC", text).replace("\u200c", "").replace("\u200d", "")
    # Only normalize complete sequences from the deliberately limited vocabulary.
    tokens = "|".join(sorted([*WORDS, *SCALES], key=len, reverse=True))
    def number(match):
        total = current = 0
        for word in match.group().casefold().split():
            if word in WORDS:
                current += WORDS[word]
            elif SCALES[word] == 100:
                current = max(current, 1) * 100
            else:
                total += max(current, 1) * 1000
                current = 0
        return str(total + current)
    text = re.sub(rf"(?<!\w)(?:{tokens})(?:\s+(?:{tokens}))*(?!\w)", number, text, flags=re.I)
    return " ".join(text.split()).rstrip(".। ")

PATTERNS = [
    ("credit", rf"{NAME}\s+(?:bought|took)\s+(?P<product>.+?)\s+(?:worth|for)\s+{MONEY}\s+on credit"),
    ("repayment", rf"{NAME}\s+(?:paid(?: back)?|repaid)\s+{MONEY}"),
    ("settlement", rf"{NAME}\s+cleared (?:his |her |the )?(?:remaining debt|remaining amount|remaining credit)"),
    ("cash", rf"(?:Record a |record )?cash sale of\s+{MONEY}"),
    ("borrow", rf"I borrowed\s+{MONEY}\s+from\s+{NAME}"),
    ("payback", rf"I paid\s+{NAME}\s+{MONEY}"),
    ("lend", rf"I lent\s+{MONEY}\s+to\s+{NAME}"),
    ("credit", rf"Add\s+{MONEY}\s+to\s+{NAME}'s credit"),
    ("credit", rf"{NAME}\s+ko\s+{MONEY}\s+udhaar (?:mein )?(?:add karo|likho)"),
    ("credit", rf"{NAME}\s+को\s+{MONEY}\s+उधार (?:लिखो|में जोड़ो)"),
    ("credit", rf"{NAME}\s*కి\s+{MONEY}\s+బాకీ రాయి"),
    ("repayment", rf"{NAME}\s+{MONEY}\s+(?:చెల్లించారు|తిరిగి ఇచ్చారు)"),
    ("credit", rf"{NAME}\s+ko\s+(?P<quantity>{NUM})\s+(?P<unit>kilo|kg|litre)\s+(?P<product>.+?)\s+diya,?\s*{MONEY}\s+udhaar mein add karo"),
    ("credit", rf"{NAME}\s*కి\s+(?P<quantity>{NUM})\s+(?P<unit>కిలోల|kg)\s+(?P<product>.+?)\s+ఇచ్చాను[.]?\s*{MONEY}\s+బాకీలో పెట్టు"),
]

def extract(transcript):
    text = normalize(transcript)
    if re.search(r"\b(?:and|or|not|maybe|about|approximately|dollars?|euros?)\b| और | या | नहीं | లేదా | కాదు | మరియు |[$€]", text, re.I):
        return {}
    if len(re.findall(CUR + r"|₹", text, re.I)) > 1 and "₹" not in text:
        return {}
    old = legacy_extract(text)
    if old:
        return old
    for kind, pattern in PATTERNS:
        match = re.fullmatch(pattern, text, re.I)
        if match:
            result = {k: v.strip() for k, v in match.groupdict().items() if v}
            if result.get("customer", "").casefold() in {"customer", "someone", "i", "he", "she"}:
                result.pop("customer", None)
            result["kind"] = kind
            return result
    return {}

def correct_amount(text, current):
    """Only explicit replace-X-with-Y commands; require old value to match."""
    text = normalize(text)
    patterns = [rf"(?:No,? )?amount (?P<old>{NUM}) ka badle (?P<new>{NUM}) karo",
                rf"(?:No,? )?(?:change|Change) amount from (?P<old>{NUM}) to (?P<new>{NUM})"]
    for pattern in patterns:
        match = re.fullmatch(pattern, text, re.I)
        if match:
            from legacy_ledger import amount_paise
            if amount_paise(match["old"]) != amount_paise(current):
                raise ValueError("correction_mismatch")
            amount_paise(match["new"])
            return match["new"]
    raise ValueError("correction_unsupported")
