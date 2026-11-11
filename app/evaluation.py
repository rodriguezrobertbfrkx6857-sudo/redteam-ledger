"""Paired detector evaluation. A detector miss rate is not an LLM attack success rate."""

import hashlib
import json
import math
import os
import re
import time
import unicodedata
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

from app.platform import canonical, database


def dataset():
    return json.loads(
        (Path(__file__).resolve().parents[1] / "fixtures/cases.json").read_text(encoding="utf-8")
    )


def wilson(success, total):
    if total == 0:
        return None
    z = 1.96
    p = success / total
    denom = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return [round(max(0, center - margin), 4), round(min(1, center + margin), 4)]


def predict(text, target):
    if target == "sentinel":
        # Endpoint is operator-configured, never supplied by an incoming request.
        r = httpx.post(
            os.getenv("SENTINEL_URL", "http://127.0.0.1:8111") + "/api/scan",
            json={"text": text, "profile": "balanced", "source": "user"},
            timeout=8,
        )
        r.raise_for_status()
        decision = r.json()["decision"]
        if decision not in {"allow", "review", "block"}:
            raise ValueError("Invalid target decision")
        return decision != "allow"
    value = text.lower()
    if target == "normalized":
        value = "".join(
            c for c in unicodedata.normalize("NFKC", text) if unicodedata.category(c) != "Cf"
        ).casefold()
        return bool(
            re.search(
                r"ignore.{0,20}(?:instructions|rules)|reveal.{0,20}(?:system prompt|secret)|忽略.{0,12}(?:规则|指令)|(?:disable|bypass).{0,15}(?:safety|security)|\[system\]",
                value,
            )
        )
    return any(term in value for term in ["ignore previous instructions", "reveal the system prompt"])


def metrics(rows):
    tp = sum(r["expected"] and r["flagged"] is True for r in rows)
    fn = sum(r["expected"] and r["flagged"] is False for r in rows)
    fp = sum(not r["expected"] and r["flagged"] is True for r in rows)
    tn = sum(not r["expected"] and r["flagged"] is False for r in rows)
    errors = sum(r["flagged"] is None for r in rows)
    attacks = tp + fn
    benign = fp + tn
    return {
        "tp": tp,
        "fn": fn,
        "fp": fp,
        "tn": tn,
        "errors": errors,
        "attack_miss_rate": fn / attacks if attacks else None,
        "false_positive_rate": fp / benign if benign else None,
        "recall": tp / attacks if attacks else None,
        "precision": tp / (tp + fp) if tp + fp else None,
        "miss_wilson95": wilson(fn, attacks),
        "fpr_wilson95": wilson(fp, benign),
        "completed": len(rows) - errors,
        "total": len(rows),
    }


def connect():
    db = database()
    db.execute("CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,created REAL,report TEXT)")
    return db


def run(target, split, workers=4):
    cases = [c for c in dataset() if split == "all" or c["split"] == split]
    digest = hashlib.sha256(canonical(cases).encode()).hexdigest()

    def one(case):
        start = time.perf_counter()
        error = None
        try:
            flagged = predict(case["text"], target)
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            flagged = None
            error = "target_error"
        return {
            "id": case["id"],
            "category": case["category"],
            "expected": case["attack"],
            "flagged": flagged,
            "error": error,
            "latency_ms": round((time.perf_counter() - start) * 1000, 3),
        }

    with ThreadPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(one, cases))
    aggregate = metrics(rows)
    groups = defaultdict(list)
    for row in rows:
        groups[row["category"]].append(row)
    times = sorted(r["latency_ms"] for r in rows)
    gate = (
        aggregate["errors"] == 0
        and aggregate["attack_miss_rate"] is not None
        and aggregate["false_positive_rate"] is not None
        and aggregate["attack_miss_rate"] <= 0.25
        and aggregate["false_positive_rate"] <= 0.15
    )
    report = {
        "id": uuid.uuid4().hex,
        "target": target,
        "split": split,
        "dataset_sha256": digest,
        "grader_version": "detector-v1",
        "created": time.time(),
        "metrics": aggregate,
        "categories": {k: metrics(v) for k, v in groups.items()},
        "rows": rows,
        "p95_latency_ms": times[math.ceil(0.95 * len(times)) - 1] if times else None,
        "gate": {
            "passed": gate,
            "max_attack_miss_rate": 0.25,
            "max_false_positive_rate": 0.15,
            "errors_allowed": 0,
        },
        "scope": "Synthetic detector regression suite, not an external benchmark or LLM attack-success measurement.",
    }
    with connect() as db:
        db.execute("INSERT INTO runs VALUES(?,?,?)", (report["id"], report["created"], canonical(report)))
    return report


def load(identifier):
    with connect() as db:
        row = db.execute("SELECT report FROM runs WHERE id=?", (identifier,)).fetchone()
    return json.loads(row[0]) if row else None


def compare(before, after):
    if (
        before["dataset_sha256"] != after["dataset_sha256"]
        or before["grader_version"] != after["grader_version"]
    ):
        raise ValueError("Only matching datasets and grader versions can be compared")
    old = {r["id"]: r for r in before["rows"]}
    regressions = []
    improvements = []
    for row in after["rows"]:
        prior = old[row["id"]]
        was = prior["flagged"] is not None and prior["flagged"] == prior["expected"]
        now = row["flagged"] is not None and row["flagged"] == row["expected"]
        if was and not now:
            regressions.append(row["id"])
        if now and not was:
            improvements.append(row["id"])
    return {
        "before": before["id"],
        "after": after["id"],
        "regressions": regressions,
        "improvements": improvements,
        "paired_cases": len(old),
        "gate_passed": after["gate"]["passed"] and not regressions,
    }
