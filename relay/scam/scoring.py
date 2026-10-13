

from __future__ import annotations

import re

from relay.scam.data import SYNTHETIC_NUMBERS

MAX_ANALYZED_CHARS = 20_000
EVIDENCE_MAX_CHARS = 40

# --------------------------------------------------------------------------
# Masking and number helpers
# --------------------------------------------------------------------------

_DIGIT_RUN = re.compile(r"\d{5,}")
_SHORT_DIGIT_RUN = re.compile(r"\d{3,}")


def mask_digits(value: str) -> str:
    """Keep the first 2 and last 2 digits of any run of 5+ digits.

    The middle digits become '*'. Example: 9876543210 -> 98******10
    """
    text = "" if value is None else str(value)

    def _mask(match: re.Match) -> str:
        run = match.group()
        return run[:2] + "*" * (len(run) - 4) + run[-2:]

    return _DIGIT_RUN.sub(_mask, text)


def normalize_number(number: str) -> str:
    """Strip spaces, dashes, a leading +91 or 0; return 10 digits if possible."""
    text = "" if number is None else str(number)
    cleaned = re.sub(r"[^\d+]", "", text)

    if cleaned.startswith("+91"):
        cleaned = cleaned[3:]

    cleaned = cleaned.replace("+", "")

    if len(cleaned) == 12 and cleaned.startswith("91"):
        cleaned = cleaned[2:]
    elif len(cleaned) == 11 and cleaned.startswith("0"):
        cleaned = cleaned[1:]

    return cleaned


def _mask_number(normalized: str) -> str:
    if not normalized:
        return ""

    if len(normalized) >= 5:
        return mask_digits(normalized)

    # Too short for mask_digits to hide anything: hide all of it.
    return "*" * len(normalized)


def check_number(number: str) -> dict:
    """Look a phone number up in the synthetic reputation list."""
    normalized = normalize_number(number)
    entry = SYNTHETIC_NUMBERS.get(normalized) if normalized else None

    return {
        "found": entry is not None,
        "number_masked": _mask_number(normalized),
        "reputation": entry["reputation"] if entry else "UNKNOWN",
        "reports": int(entry["reports"]) if entry else 0,
    }


# --------------------------------------------------------------------------
# Levels and actions (shared with the classifier in a later task)
# --------------------------------------------------------------------------


def level_for(score: int) -> str:
    """LOW below 25, MEDIUM 25-49, HIGH 50-74, CRITICAL 75 and above."""
    try:
        value = int(score)
    except (TypeError, ValueError):
        value = 0

    if value >= 75:
        return "CRITICAL"

    if value >= 50:
        return "HIGH"

    if value >= 25:
        return "MEDIUM"

    return "LOW"


def action_for(score: int) -> str:
    """HOLD_PAYMENTS from 70, WARN from 40, otherwise NONE."""
    try:
        value = int(score)
    except (TypeError, ValueError):
        value = 0

    if value >= 70:
        return "HOLD_PAYMENTS"

    if value >= 40:
        return "WARN"

    return "NONE"


# --------------------------------------------------------------------------
# Text preparation
# --------------------------------------------------------------------------

# Catches 'O T P', 'O.T.P' and 'o-t-p' (3+ single letters split by a separator).
_SPACED_LETTERS = re.compile(
    r"(?<![A-Za-z])(?:[A-Za-z][ \t.\-]){2,}[A-Za-z](?![A-Za-z])"
)
_SEPARATORS = re.compile(r"[ \t.\-]")


def _collapse_spaced_letters(text: str) -> str:
    return _SPACED_LETTERS.sub(
        lambda match: _SEPARATORS.sub("", match.group()),
        text,
    )


def _mask_evidence(snippet: str) -> str:
    """Make a short, safe snippet: one line, digits hidden, max 40 chars."""
    cleaned = " ".join(snippet.split())
    cleaned = _SHORT_DIGIT_RUN.sub(lambda m: "*" * len(m.group()), cleaned)

    if len(cleaned) > EVIDENCE_MAX_CHARS:
        cleaned = cleaned[: EVIDENCE_MAX_CHARS - 1].rstrip() + "\u2026"

    return cleaned


# --------------------------------------------------------------------------
# Signal rules (case-insensitive)
# --------------------------------------------------------------------------

_FLAGS = re.IGNORECASE


def _rx(*parts: str) -> re.Pattern:
    return re.compile("".join(parts), _FLAGS)


def _earliest(patterns: list[re.Pattern], text: str) -> re.Match | None:
    best = None

    for pattern in patterns:
        match = pattern.search(text)

        if match and (best is None or match.start() < best.start()):
            best = match

    return best


# ---- otp_request ---------------------------------------------------------

_SECRET = (
    r"(?:otp|one[\s-]?time[\s-]?(?:password|pin|code)|upi\s*pin|atm\s*pin|mpin|"
    r"pin(?!\s*code)(?:\s*number)?|cvv|cvc|password|passcode|"
    r"verification\s+code|security\s+code|card\s+number)"
)

_REQUEST_VERBS = (
    r"(?:share|send|tell|give|provide|read(?:\s+out)?|forward|confirm|verify|"
    r"reply(?:\s+with)?|submit|dictate|disclose|batao|bataiye|bhejo|bhejiye|"
    r"dijiye|bata\s+do|bhej\s+do|share\s+karo|send\s+karo)"
)

# 'share your OTP', 'send me the PIN', 'verify the CVV'
_OTP_VERB_FIRST = _rx(r"\b", _REQUEST_VERBS, r"\b[^.!?\n]{0,40}?\b", _SECRET, r"\b")

# 'OTP is required', 'PIN to verify', 'OTP batao'
_OTP_SECRET_FIRST = _rx(
    r"\b", _SECRET, r"\b[^.!?\n]{0,25}?\b",
    r"(?:required|needed|batao|bhejo|bataiye|bhejiye|dijiye|"
    r"to\s+(?:us|me|verify|confirm|unblock|activate|cancel|stop|avoid|claim|"
    r"proceed|continue|reactivate|release|complete))\b",
)

# 'what is your OTP'
_OTP_QUESTION = _rx(r"\b(?:what(?:'s|\s+is)|tell\s+me|give\s+me)\s+(?:your|the)\s+", _SECRET, r"\b")

# A real bank warning such as 'Do not share your OTP' must NOT count as a request.
_NEGATED_BEFORE = re.compile(
    r"(?:do\s*not|don'?t|never|not\s+to|should\s*not|shouldn'?t|must\s*not|mat|nahi|nahin)"
    r"[\s,]+(?:(?:ever|please|kindly|you|u)[\s,]+)*$",
    _FLAGS,
)
_NEGATION_WORD = re.compile(r"\b(?:not|never|don'?t|mat|nahi|nahin)\b", _FLAGS)


def _detect_otp_request(text: str) -> tuple[int, str] | None:
    candidates: list[re.Match] = []

    for match in _OTP_VERB_FIRST.finditer(text):
        prefix = text[max(0, match.start() - 30): match.start()]

        if _NEGATED_BEFORE.search(prefix):
            continue

        candidates.append(match)
        break

    for match in _OTP_SECRET_FIRST.finditer(text):
        if _NEGATION_WORD.search(match.group()):
            continue

        candidates.append(match)
        break

    question = _OTP_QUESTION.search(text)

    if question:
        candidates.append(question)

    if not candidates:
        return None

    first = min(candidates, key=lambda m: m.start())
    return 40, first.group()


# ---- impersonation -------------------------------------------------------

_ORGS = (
    r"(?:sbi|state\s+bank(?:\s+of\s+india)?|hdfc|icici|axis\s+bank|pnb|"
    r"punjab\s+national|kotak|bank\s+of\s+baroda|canara|rbi|"
    r"reserve\s+bank(?:\s+of\s+india)?|bank|police|cbi|enforcement\s+directorate|"
    r"customs|income\s+tax|tax\s+department|courier|fedex|dhl|blue\s*dart|"
    r"delhivery|india\s+post|government|govt|ministry|trai|npci|uidai|aadhaar|"
    r"amazon|flipkart|paytm|phonepe|google\s+pay|telecom|electricity\s+board|"
    r"cyber\s+(?:cell|crime))"
)

_CLAIM_PHRASE = (
    r"(?:this\s+is|calling\s+from|call(?:ing)?\s+you\s+from|speaking\s+from|"
    r"message\s+from|notice\s+from|alert\s+from|on\s+behalf\s+of|"
    r"(?:i\s+am|i'?m|we\s+are)\s+(?:calling|writing|messaging)\s+from)"
)

_IMPERSONATION_CLAIM = [
    _rx(r"\b", _CLAIM_PHRASE, r"\b[^.!?\n]{0,40}?\b", _ORGS, r"\b"),
    _rx(
        r"\b", _ORGS,
        r"\s+(?:officer|manager|executive|official|representative|department|"
        r"customer\s+(?:care|support)|helpdesk)\b",
    ),
]

# A bare brand name (like 'SBI') is only a weak hint: friends mention banks too.
_IMPERSONATION_BARE = _rx(
    r"\b(?:sbi|hdfc|icici|pnb|kotak|rbi|reserve\s+bank\s+of\s+india|cbi|"
    r"income\s+tax\s+department|customs\s+department|npci|uidai|trai|"
    r"enforcement\s+directorate|fedex|dhl|blue\s*dart|delhivery|india\s+post|"
    r"paytm|phonepe)\b"
)


def _detect_impersonation(text: str) -> tuple[int, str] | None:
    claim = _earliest(_IMPERSONATION_CLAIM, text)

    if claim:
        return 25, claim.group()

    bare = _IMPERSONATION_BARE.search(text)

    if bare:
        return 12, bare.group()

    return None


# ---- simple one-weight signals ------------------------------------------

_URGENCY = [
    _rx(
        r"\b(?:immediately|urgent(?:ly)?|right\s+now|asap|act\s+now|hurry|"
        r"without\s+delay|at\s+once|last\s+(?:chance|warning|reminder|date)|"
        r"final\s+(?:notice|warning|reminder)|expires?\s+(?:today|tonight|soon|in\s+\d+)|"
        r"within\s+\d+\s*(?:hours?|hrs?|minutes?|mins?)|today\s+only|"
        r"before\s+midnight|turant|jaldi)\b"
    ),
]

_PAYMENT_DEMAND = [
    _rx(
        r"\b(?:transfer|send|pay|deposit|remit|credit)\b[^.!?\n]{0,30}?"
        r"(?:\u20b9|\brs\b\.?\s*\d|\binr\b|\brupees?\b|\bupi\b|\bamount\b|"
        r"\bfees?\b|\bcharges?\b|\bfine\b|\bpenalty\b|\bdeposit\b)"
    ),
    _rx(
        r"\b(?:processing|registration|customs|clearance|delivery|release|"
        r"activation|insurance|refundable|security)\s+"
        r"(?:fee|fees|charge|charges|deposit|amount)\b"
    ),
    _rx(
        r"\b(?:upi\s+collect|collect\s+request|gift\s+cards?|"
        r"scan\s+(?:the\s+)?qr(?:\s+code)?|google\s+play\s+cards?|itunes\s+cards?|"
        r"crypto(?:currency)?\s+wallet|bitcoin|wire\s+transfer|western\s+union)\b"
    ),
]

_REMOTE_ACCESS = [
    _rx(
        r"\b(?:any\s*desk|team\s*viewer|quick\s*support|ammyy|rustdesk|supremo|"
        r"screen\s*shar(?:e|ing)|share\s+(?:your\s+)?screen|"
        r"remote\s+(?:access|desktop|support|control)|"
        r"install\s+(?:this\s+|the\s+)?(?:app|apk|software|application))\b"
    ),
    _rx(r"\.apk\b"),
]

_SUSPICIOUS_LINK = [
    _rx(r"\bhttp://\S+"),
    _rx(
        r"\b(?:bit\.ly|tinyurl\.com|t\.co|goo\.gl|cutt\.ly|rb\.gy|is\.gd|"
        r"shorturl\.at|ow\.ly|tiny\.cc|rebrand\.ly|s\.id)/\S*"
    ),
    _rx(r"https?://\d{1,3}(?:\.\d{1,3}){3}"),
    _rx(r"https?://\S*\.(?:xyz|top|click|buzz|icu|work|live|shop|monster|cfd|sbs)\b"),
    _rx(r"\bclick\s+(?:on\s+)?(?:the\s+|this\s+)?(?:link|here|below)\b"),
]

_PRIZE_LOTTERY = [
    _rx(
        r"\b(?:lottery|lucky\s+draw|jackpot|free\s+gift|kbc|"
        r"you\s+are\s+(?:the\s+)?(?:winner|selected)|"
        r"congratulations[^.!?\n]{0,30}?(?:won|winner|selected|prize|reward)|"
        r"claim\s+(?:your\s+)?(?:prize|reward|gift|cashback)|"
        r"cashback\s+(?:offer|reward))\b"
    ),
    _rx(
        r"\byou(?:'ve|\s+have)?\s+won\b[^.!?\n]{0,40}?"
        r"(?:\u20b9|\brs\b|\blakhs?\b|\bcrores?\b|\bprize\b|\blottery\b|\breward\b|"
        r"\bgift\b|\bcash\b|\biphone\b|\bcar\b|\bvoucher\b|\bcashback\b)"
    ),
]

_KYC_UPDATE = [
    _rx(
        r"\b(?:re-?kyc|kyc|update\s+(?:your\s+)?(?:pan|aadhaar|aadhar|bank\s+details)|"
        r"verify\s+(?:your\s+)?(?:account|identity|pan|aadhaar|aadhar)|"
        r"link\s+(?:your\s+)?(?:pan|aadhaar|aadhar)|"
        r"pan\s+(?:card\s+)?(?:suspended|blocked|expired))\b"
    ),
]

_THREAT = [
    _rx(
        r"\b(?:arrest(?:ed)?|warrant|legal\s+action|court\s+(?:case|notice|summons)|"
        r"fir|police\s+case|jail|digital\s+arrest|money\s+laundering|"
        r"case\s+(?:has\s+been\s+|is\s+|will\s+be\s+)?(?:registered|filed)|"
        r"account\s+(?:will\s+be\s+|has\s+been\s+|is\s+|gets\s+)?"
        r"(?:blocked|frozen|suspended|closed|deactivated)|"
        r"(?:sim|card|number|service|connection)\s+(?:will\s+be\s+|is\s+|has\s+been\s+)?"
        r"(?:blocked|suspended|disconnected|deactivated)|"
        r"illegal\s+(?:activity|parcel|transaction)|"
        r"giraftar|band\s+ho\s+jayega|block\s+ho\s+jayega)\b"
    ),
]


def _simple(weight: int, patterns: list[re.Pattern]):
    def detect(text: str) -> tuple[int, str] | None:
        match = _earliest(patterns, text)
        return (weight, match.group()) if match else None

    return detect


# name, detector. Order is only used to keep results stable.
_DETECTORS = [
    ("otp_request", _detect_otp_request),
    ("impersonation", _detect_impersonation),
    ("urgency", _simple(15, _URGENCY)),
    ("payment_demand", _simple(20, _PAYMENT_DEMAND)),
    ("remote_access", _simple(35, _REMOTE_ACCESS)),
    ("suspicious_link", _simple(20, _SUSPICIOUS_LINK)),
    ("prize_lottery", _simple(25, _PRIZE_LOTTERY)),
    ("kyc_update", _simple(20, _KYC_UPDATE)),
    ("threat", _simple(25, _THREAT)),
]

# Plain-language text per signal: used for the explanation and the advice.
_SIGNAL_TEXT = {
    "otp_request": (
        "asks for an OTP, PIN or password",
        "Never share an OTP, PIN, CVV or password with anyone, "
        "even if they say they are from your bank.",
    ),
    "impersonation": (
        "claims to come from a bank or an official body",
        "Hang up and call the official number on your card or the bank's website.",
    ),
    "urgency": (
        "pushes you to act in a hurry",
        "Scammers rush you. Take a few minutes and talk to a family member first.",
    ),
    "payment_demand": (
        "asks for money or a fee",
        "Do not send money or pay any fee because of a message or a call.",
    ),
    "remote_access": (
        "asks to control or share your phone screen",
        "Do not install apps or share your screen because someone asks you to.",
    ),
    "suspicious_link": (
        "contains a suspicious link",
        "Do not open links in unexpected messages.",
    ),
    "prize_lottery": (
        "promises a prize you never entered for",
        "You cannot win a prize in a draw you did not enter.",
    ),
    "kyc_update": (
        "asks for a KYC or ID update",
        "Banks do not ask you to update KYC through links or phone calls.",
    ),
    "threat": (
        "threatens arrest, blocking or legal action",
        "Police and courts do not threaten arrest over the phone or ask for payment.",
    ),
    "known_scam_sender": (
        "comes from a number reported as a scam",
        "Do not reply to this number. Block it.",
    ),
    "suspicious_sender": (
        "comes from a number with scam reports",
        "Be careful with this number and do not act on its message.",
    ),
}

_LEAD = {
    "LOW": "This message has a minor warning sign",
    "MEDIUM": "This message looks suspicious",
    "HIGH": "This message is very likely a scam",
    "CRITICAL": "This message is almost certainly a scam",
}


def _sender_signal(sender: str | None) -> tuple[str, int, str] | None:
    """Extra signal when the sender is a known bad number (synthetic list)."""
    if not sender:
        return None

    info = check_number(sender)

    if info["reputation"] == "KNOWN_SCAM":
        return "known_scam_sender", 40, f"sender {info['number_masked']} ({info['reports']} reports)"

    if info["reputation"] == "SUSPICIOUS":
        return "suspicious_sender", 15, f"sender {info['number_masked']} ({info['reports']} reports)"

    return None


def _explain(level: str, signals: list[dict]) -> str:
    if not signals:
        return "No common scam warning signs were found in this message."

    labels = [_SIGNAL_TEXT[s["name"]][0] for s in signals[:4]]
    extra = len(signals) - len(labels)

    if extra > 0:
        labels.append(f"shows {extra} more warning sign{'s' if extra > 1 else ''}")

    if len(labels) == 1:
        joined = labels[0]
    else:
        joined = ", ".join(labels[:-1]) + " and " + labels[-1]

    return f"{_LEAD[level]}: it {joined}."


def _advice(level: str, signals: list[dict]) -> list[str]:
    if not signals:
        return [
            "No action needed. If anything feels odd, "
            "check with a family member before you reply."
        ]

    lines: list[str] = []

    for signal in signals:
        text = _SIGNAL_TEXT[signal["name"]][1]

        if text not in lines:
            lines.append(text)

    if level in ("HIGH", "CRITICAL"):
        lines.append("Ask a trusted family member before you reply, click or pay.")

    return lines[:6]


def analyze_message_text(text: str, sender: str | None = None) -> dict:
    """Score a message for scam risk.

    Returns exactly: risk_score, risk_level, signals, explanation,
    recommended_action, advice.
    """
    raw = "" if text is None else str(text)
    scan_text = _collapse_spaced_letters(raw[:MAX_ANALYZED_CHARS])

    found: list[dict] = []

    for name, detector in _DETECTORS:
        hit = detector(scan_text)

        if hit:
            weight, snippet = hit
            found.append(
                {
                    "name": name,
                    "weight": weight,
                    "evidence": _mask_evidence(snippet),
                }
            )

    sender_hit = _sender_signal(sender)

    if sender_hit:
        name, weight, snippet = sender_hit
        found.append(
            {
                "name": name,
                "weight": weight,
                "evidence": _mask_evidence(snippet),
            }
        )

    found.sort(key=lambda s: (-s["weight"], s["name"]))

    total = sum(s["weight"] for s in found)
    names = {s["name"] for s in found}

    # Combination rule: asking for an OTP while posing as a bank is the
    # classic scam, so it always scores at least 85.
    if "otp_request" in names and "impersonation" in names:
        total = max(total, 85)

    score = min(100, total)
    level = level_for(score)

    return {
        "risk_score": score,
        "risk_level": level,
        "signals": found,
        "explanation": _explain(level, found),
        "recommended_action": action_for(score),
        "advice": _advice(level, found),
    }