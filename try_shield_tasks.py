from relay.scam.data import get_profile
from relay.scam.policy import (
    CASE_TRANSITIONS,
    FINAL_STATES,
    assess_payment,
    contact_at,
    evaluate_scam_action,
    validate_case_transition,
)
from relay.scam.scoring import analyze_message_text, check_number, mask_digits


def title(text: str) -> None:
    print()
    print("=" * 70)
    print(text)
    print("=" * 70)


# ---------------------------------------------------------------- TASK 1
title("TASK 1: scoring a message")

messages = [
    ("Scam: bank + OTP + threat",
     "This is SBI bank. Your account will be blocked today. "
     "Share your OTP immediately to unblock."),
    ("Real bank OTP text",
     "Your OTP is 482913. Do not share it with anyone."),
    ("Friendly family chat",
     "Hi Mom, I will call you after lunch. Did you take your medicines?"),
    ("Prize scam with link",
     "Congratulations! You have won Rs 25 lakh in KBC lucky draw. "
     "Click the link http://bit.ly/abc to claim your prize"),
    ("Hinglish scam",
     "SBI se bol raha hoon, abhi OTP batao warna account band ho jayega"),
]

for label, text in messages:
    result = analyze_message_text(text)
    names = [s["name"] for s in result["signals"]]
    print(f"\n{label}")
    print(f"  score {result['risk_score']:3}  level {result['risk_level']:8}"
          f"  action {result['recommended_action']}")
    print(f"  signals: {names}")
    print(f"  why: {result['explanation']}")

title("TASK 1: phone numbers and masking")

for number in ["+91 90000 00001", "9000000003", "9000000010", "9876543210", "abc"]:
    print(f"  {number!r:20} -> {check_number(number)}")

print(f"\n  mask_digits('call 9876543210 now') -> "
      f"{mask_digits('call 9876543210 now')!r}")

# ---------------------------------------------------------------- TASK 2
title("TASK 2: the case state machine")

print("A normal path (each step should be allowed):")
path = ["OPENED", "HELD", "AWAITING_FAMILY", "REJECTED"]
for current, nxt in zip(path, path[1:]):
    ok, message = validate_case_transition(current, nxt)
    print(f"  {current:16} -> {nxt:16} {ok}  ({message})")

print("\nIllegal moves (each should be refused):")
for current, nxt in [("HELD", "APPROVED"), ("REJECTED", "HELD"), ("OPENED", "OPENED")]:
    ok, message = validate_case_transition(current, nxt)
    print(f"  {current:16} -> {nxt:16} {ok}  ({message})")

print(f"\nFinal states (no way out): {sorted(FINAL_STATES)}")
print(f"Total states: {len(CASE_TRANSITIONS)}")

title("TASK 2: payment decisions (profile limit is Rs 10,000)")

profile = get_profile("user_savita")
cases = [
    ("High risk, Rs 25,000, new payee", 85, 25000, True),
    ("High risk, no payment",           85, None,  True),
    ("Low risk, exactly the limit",     10, 10000, True),
    ("Low risk, Rs 1 over the limit",   10, 10001, True),
    ("Low risk, over limit, known payee", 10, 10001, False),
    ("Medium risk, small payment",      45, 500,   False),
    ("Low risk, small payment",         10, 500,   False),
    ("Invalid: risk score 150",         150, 500,  False),
    ("Invalid: negative amount",        50, -5,    False),
]

for label, risk, amount, new_payee in cases:
    result = assess_payment(risk, amount, new_payee, profile)
    print(f"  {label:36} -> {result['decision']:5} ({result['risk']})")

title("TASK 2: which actions are allowed")

for action in ["ANALYZE_MESSAGE", "OPEN_CASE", "FAMILY_DECISION", "DELETE_EVERYTHING"]:
    result = evaluate_scam_action(action)
    print(f"  {action:18} -> {result['decision']:17} {result['reason']}")

title("TASK 2: trusted contacts in order")

for index in range(3):
    print(f"  contact {index}: {contact_at(profile, index)}")

# -------------------------------------------------------- BOTH TOGETHER
title("TASKS 1 + 2 TOGETHER: the demo story")

scam_text = ("This is SBI bank. Your account will be blocked today. "
             "Share your OTP immediately to unblock.")
analysis = analyze_message_text(scam_text)
decision = assess_payment(analysis["risk_score"], 25000, True, profile)

print(f"  1. Message scored {analysis['risk_score']} ({analysis['risk_level']}).")
print(f"  2. Savita tries to pay Rs 25,000 to a new payee.")
print(f"  3. Decision: {decision['decision']}")

for reason in decision["reasons"]:
    print(f"     - {reason}")

ok, _ = validate_case_transition("OPENED", "HELD")
print(f"  4. Case may move OPENED -> HELD: {ok}")
print(f"  5. First family contact to alert: {contact_at(profile, 0)['name']}")
print()