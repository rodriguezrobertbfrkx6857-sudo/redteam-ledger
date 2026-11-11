import pytest

from app.evaluation import compare, dataset, metrics, run, wilson


def test_confusion_matrix():
    rows = [
        {"expected": True, "flagged": True},
        {"expected": True, "flagged": False},
        {"expected": False, "flagged": True},
        {"expected": False, "flagged": False},
        {"expected": True, "flagged": None},
    ]
    result = metrics(rows)
    assert [result[k] for k in ["tp", "fn", "fp", "tn", "errors"]] == [1, 1, 1, 1, 1]
    assert result["attack_miss_rate"] == 0.5


def test_wilson_known():
    assert wilson(0, 10) == [0, 0.2775]
    assert wilson(10, 10) == [0.7225, 1]
    assert wilson(0, 0) is None


def test_empty_denominators():
    assert metrics([])["attack_miss_rate"] is None
    assert metrics([])["false_positive_rate"] is None


def test_deterministic_identity():
    a = run("keyword", "dev")
    b = run("keyword", "dev")
    assert a["dataset_sha256"] == b["dataset_sha256"]
    assert a["metrics"] == b["metrics"]
    assert a["id"] != b["id"]


def test_pair_and_mismatch():
    a = run("keyword", "challenge")
    b = run("normalized", "challenge")
    assert compare(a, b)["improvements"]
    with pytest.raises(ValueError):
        compare(a, run("normalized", "dev"))


def test_errors_fail_gate(monkeypatch):
    def fail(*args):
        raise ValueError("broken target")

    monkeypatch.setattr("app.evaluation.predict", fail)
    result = run("sentinel", "challenge")
    assert result["metrics"]["errors"] == result["metrics"]["total"]
    assert not result["gate"]["passed"]
    assert result["metrics"]["attack_miss_rate"] is None


def test_dataset_unique_and_both_classes():
    cases = dataset()
    assert len({c["id"] for c in cases}) == len(cases)
    for split in ["dev", "challenge"]:
        assert {c["attack"] for c in cases if c["split"] == split} == {True, False}


def test_api_roundtrip(client):
    report = client.post("/api/runs", json={"target": "normalized", "split": "dev"}).json()
    assert client.get("/api/runs/" + report["id"]).json() == report
    assert client.get("/api/runs/missing").status_code == 404
    assert client.post("/api/runs", json={"target": "http://localhost"}).status_code == 422


def test_api_mismatch(client):
    a = client.post("/api/runs", json={"split": "dev"}).json()
    b = client.post("/api/runs", json={"split": "challenge"}).json()
    assert client.post("/api/compare", json={"before": a["id"], "after": b["id"]}).status_code == 409
