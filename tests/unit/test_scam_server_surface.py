
from __future__ import annotations

import ast
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

ORIGINAL_TOOLS = {
    "clarify_delegation": "cda39e3f317db190",
    "assess_action_risk": "ef4ccfa9804c5fd2",
    "create_errand": "b613dd1c89480d82",
    "get_errand": "25c7dcdce6ee047c",
    "find_providers": "e619f86d641812b8",
    "propose_options": "96ca643582e57272",
    "select_provider": "f107297c17c40286",
    "approve_booking": "f60662859ddb29ad",
    "get_audit_log": "46cdeabebb20e810",
    "simulate_provider_failure_tool": "43ed7102b5c91122",
    "restore_provider": "96eda4da7f088aaa",
    "schedule_task_resume": "73457b27b17d5b56",
    "list_household_assets": "4e0b51c8c7bc0a50",
    "get_household_asset": "c3ea08e1721d1552",
    "check_warranty": "7a6e807cb2d44cdb",
    "troubleshoot_home_asset": "84d6a583b997a49a",
    "prepare_service_from_asset": "ec11cb60828c58f9",
}

# name -> list of (parameter, default source text or None when required)
NEW_TOOLS = {
    "analyze_message": [("text", None), ("sender", "None")],
    "check_number": [("number", None)],
    "assess_scam_risk": [
        ("owner_id", None),
        ("risk_score", None),
        ("amount", "None"),
        ("payee_is_new", "False"),
    ],
    "open_protection_case": [
        ("owner_id", None),
        ("risk_score", None),
        ("amount", None),
        ("payee_label", None),
        ("payee_is_new", None),
        ("signals", "None"),
        ("cooling_off_minutes", "None"),
    ],
    "alert_trusted_contact": [("case_id", None), ("owner_id", None)],
    "record_family_decision": [
        ("case_id", None),
        ("contact_id", None),
        ("approval_code", None),
        ("decision", None),
    ],
    "get_protection_case": [("case_id", None), ("owner_id", None)],
    "get_case_receipt": [("case_id", None), ("owner_id", None)],
    "get_family_inbox": [("case_id", None), ("contact_id", None)],
}


def server_tree() -> ast.Module:
    # utf-8-sig: server.py may start with a byte order mark
    return ast.parse((ROOT / "server.py").read_text(encoding="utf-8-sig"))


def decorated(tree: ast.Module, kind: str) -> list[ast.FunctionDef]:
    found = []

    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            for deco in node.decorator_list:
                if ast.unparse(deco).startswith(f"mcp.{kind}("):
                    found.append(node)

    return found


def tools_by_name() -> dict[str, ast.FunctionDef]:
    return {node.name: node for node in decorated(server_tree(), "tool")}


def signature(node: ast.FunctionDef) -> list[tuple[str, str | None]]:
    args = node.args.args
    defaults = [None] * (len(args) - len(node.args.defaults)) + [
        ast.unparse(d) for d in node.args.defaults
    ]

    return [(a.arg, d) for a, d in zip(args, defaults)]


# ------------------------------------------------------------------ counts


def test_there_are_exactly_26_tools():
    assert len(decorated(server_tree(), "tool")) == 26


def test_the_17_original_tools_are_still_present():
    assert set(ORIGINAL_TOOLS) <= set(tools_by_name())


def test_the_9_new_tools_are_present():
    assert set(NEW_TOOLS) <= set(tools_by_name())


def test_there_are_no_duplicate_tool_names():
    names = [n.name for n in decorated(server_tree(), "tool")]

    assert len(names) == len(set(names))


def test_original_tools_are_unchanged():
    tools = tools_by_name()

    for name, expected in ORIGINAL_TOOLS.items():
        actual = hashlib.sha256(ast.dump(tools[name]).encode()).hexdigest()[:16]
        assert actual == expected, f"{name} was modified"


# -------------------------------------------------------------- signatures


def test_new_tool_signatures_match_the_plan():
    tools = tools_by_name()

    for name, expected in NEW_TOOLS.items():
        assert signature(tools[name]) == expected, name


def test_every_new_tool_states_its_risk_tier():
    tools = tools_by_name()

    for name in NEW_TOOLS:
        assert "Risk tier:" in (ast.get_docstring(tools[name]) or ""), name


def test_record_family_decision_carries_the_warning():
    doc = " ".join(ast.get_docstring(tools_by_name()["record_family_decision"]).split())

    assert "Only the family member's device may call this with the approval code" in doc
    assert "must never call it on its own" in doc


def test_get_family_inbox_carries_the_warning():
    doc = " ".join(ast.get_docstring(tools_by_name()["get_family_inbox"]).split())

    assert "Simulated delivery channel" in doc
    assert "Not for use by the assistant" in doc


# --------------------------------------------- resources, prompts, health


def test_there_are_exactly_3_resources_and_2_prompts():
    tree = server_tree()

    assert len(decorated(tree, "resource")) == 3
    assert len(decorated(tree, "prompt")) == 2


def test_shield_resource_and_prompt_exist():
    tree = server_tree()
    resources = [ast.unparse(d) for n in decorated(tree, "resource") for d in n.decorator_list]
    prompts = [ast.unparse(d) for n in decorated(tree, "prompt") for d in n.decorator_list]

    assert any("relay://shield/profile/{owner_id}" in text for text in resources)
    assert any("protect_family_from_scam" in text for text in prompts)


def test_prompt_forbids_approving_and_asking_for_codes():
    prompt = next(n for n in decorated(server_tree(), "prompt") if n.name == "protect_family_from_scam")
    text = ast.unparse(prompt)

    assert "Never approve a payment" in text
    assert "never ask for OTPs or approval codes" in text
    assert [a.arg for a in prompt.args.args] == ["owner_id", "message"]


def test_health_route_reports_scam_shield():
    health = next(n for n in server_tree().body if isinstance(n, ast.AsyncFunctionDef) and n.name == "health")

    assert "scam_shield" in ast.unparse(health)


# ---------------------------------------------------------------- guardrails


def test_agent_tools_do_not_expose_family_tools():
    text = (ROOT / "relay" / "agent_tools.py").read_text(encoding="utf-8")

    for name in ("alert_trusted_contact", "record_family_decision", "get_family_inbox"):
        assert name not in text, name


def test_mcp_run_only_happens_under_the_main_guard():
    tree = server_tree()
    run_calls = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call) and ast.unparse(n.func) == "mcp.run"
    ]
    guarded = [
        n for node in tree.body
        if isinstance(node, ast.If) and ast.unparse(node.test).replace("'", '"') == '__name__ == "__main__"'
        for n in ast.walk(node)
        if isinstance(n, ast.Call) and ast.unparse(n.func) == "mcp.run"
    ]

    assert len(run_calls) == 1
    assert len(guarded) == 1


def test_env_example_documents_the_shield_secret():
    assert "RELAY_SHIELD_SECRET" in (ROOT / ".env.example").read_text(encoding="utf-8")