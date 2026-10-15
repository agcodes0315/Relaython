
from __future__ import annotations

import copy

import relay.scam.service as service

TEST_SECRET = "unit-test-secret"


class FakeCaseStore:
    def __init__(self) -> None:
        self.cases: dict[str, dict] = {}
        self.events: list[dict] = []
        self.timers: list[dict] = []

    # --- storage used by the service -------------------------------------
    def save_task(self, task: dict) -> dict:
        self.cases[task["task_id"]] = copy.deepcopy(task)
        return task

    def get_task(self, task_id: str) -> dict | None:
        case = self.cases.get(task_id)
        return copy.deepcopy(case) if case is not None else None

    def record_event(self, task_id: str, event_type: str, details: dict) -> dict:
        event = {
            "task_id": task_id,
            "event_type": event_type,
            "details": copy.deepcopy(details),
        }
        self.events.append(event)
        return event

    def get_task_events(self, task_id: str) -> list[dict]:
        return [
            dict(e, timestamp=f"2026-01-01T00:00:{i:02d}+00:00")
            for i, e in enumerate(self.events)
            if e["task_id"] == task_id
        ]

    def event_types(self, task_id: str | None = None) -> list[str]:
        return [
            e["event_type"]
            for e in self.events
            if task_id is None or e["task_id"] == task_id
        ]

    # --- conditional writes ----------------------------------------------
    def conditional_update(
        self,
        case_id,
        expected_status,
        set_values,
        extra_condition=None,
        extra_names=None,
        extra_values=None,
    ):
        case = self.cases.get(case_id)

        if case is None or case.get("status") != expected_status:
            return None

        cid = (extra_names or {}).get("#cid")
        approvals = case.get("approvals", {})

        if extra_condition and "attribute_not_exists(approvals.#cid)" in extra_condition:
            if cid in approvals:
                return None

        if extra_condition and "approvals.#cid.used = :false" in extra_condition:
            if approvals.get(cid, {}).get("used") is not False:
                return None

        for key, value in set_values.items():
            target = case
            parts = key.split(".")

            for part in parts[:-1]:
                target = target.setdefault(part, {})

            target[parts[-1]] = copy.deepcopy(value)

        return copy.deepcopy(case)

    def register_wrong_code(self, case_id, contact_id):
        case = self.cases.get(case_id)

        if case is None or case.get("status") != "AWAITING_FAMILY":
            return None

        entry = case.get("approvals", {}).get(contact_id)

        if entry is None or entry.get("used"):
            return None

        entry["attempts"] = entry.get("attempts", 0) + 1
        locked = entry["attempts"] >= service.MAX_WRONG_CODES

        if locked:
            entry["used"] = True

        return {"attempts": entry["attempts"], "locked": locked}

    def schedule_resume(self, task_id, run_at, **kwargs):
        self.timers.append(
            {
                "task_id": task_id,
                "run_at": run_at,
                "name_suffix": kwargs.get("name_suffix"),
                "extra_payload": kwargs.get("extra_payload"),
                "persist_task": kwargs.get("persist_task"),
            }
        )
        return {"schedule_name": f"fake-{kwargs.get('name_suffix')}"}


def install(monkeypatch, secret: str | None = TEST_SECRET) -> FakeCaseStore:
    store = FakeCaseStore()

    monkeypatch.setattr(service, "save_task", store.save_task)
    monkeypatch.setattr(service, "get_task", store.get_task)
    monkeypatch.setattr(service, "record_event", store.record_event)
    monkeypatch.setattr(service, "get_task_events", store.get_task_events)
    monkeypatch.setattr(service, "_conditional_update", store.conditional_update)
    monkeypatch.setattr(service, "_register_wrong_code", store.register_wrong_code)
    monkeypatch.setattr(service, "schedule_resume", store.schedule_resume)

    if secret is None:
        monkeypatch.delenv("RELAY_SHIELD_SECRET", raising=False)
    else:
        monkeypatch.setenv("RELAY_SHIELD_SECRET", secret)

    return store


class FakeClient:
    """Stands in for the OpenAI-compatible Bedrock client (no network).

    responses.create(model=, instructions=, input=, store=) records its
    arguments and returns SimpleNamespace(output_text=<text>), or raises the
    configured exception. with_options(timeout=) records the timeout and
    returns the same object.
    """

    def __init__(self, output_text=None, raises: Exception | None = None) -> None:
        from types import SimpleNamespace

        self._namespace = SimpleNamespace
        self.output_text = output_text
        self.raises = raises
        self.calls: list[dict] = []
        self.timeouts: list = []
        self.responses = self

    def with_options(self, timeout=None, **_kwargs):
        self.timeouts.append(timeout)
        return self

    def create(self, **kwargs):
        self.calls.append(kwargs)

        if self.raises is not None:
            raise self.raises

        return self._namespace(output_text=self.output_text)


def model_json(is_scam=True, confidence=0.9, scam_type="otp_phishing", reasons=None) -> str:
    import json

    return json.dumps(
        {
            "is_scam": is_scam,
            "confidence": confidence,
            "scam_type": scam_type,
            "reasons": reasons if reasons is not None else ["asks for an OTP"],
        }
    )