import json
from typing import Literal

from fastapi import HTTPException
from pydantic import Field

from app.evaluation import compare, connect, dataset, load, run
from app.platform import StrictModel, audit, make_app, mount_ui

app = make_app("Redteam Ledger")


class RunRequest(StrictModel):
    target: Literal["keyword", "normalized", "sentinel"] = "normalized"
    split: Literal["dev", "challenge", "all"] = "challenge"
    workers: int = Field(default=4, ge=1, le=8)


class Comparison(StrictModel):
    before: str = Field(min_length=1, max_length=40)
    after: str = Field(min_length=1, max_length=40)


@app.get("/api/dataset")
def cases():
    return {"cases": dataset(), "license": "CC0-1.0; original synthetic fixtures"}


@app.post("/api/runs")
def evaluate(body: RunRequest):
    result = run(**body.model_dump())
    audit(
        "evaluation",
        {
            "id": result["id"],
            "target": result["target"],
            "dataset": result["dataset_sha256"],
            "gate": result["gate"]["passed"],
        },
    )
    return result


@app.get("/api/runs")
def listing():
    with connect() as db:
        rows = [
            json.loads(r[0]) for r in db.execute("SELECT report FROM runs ORDER BY created DESC LIMIT 30")
        ]
    return {"runs": [{k: v for k, v in r.items() if k not in {"rows", "categories"}} for r in rows]}


@app.get("/api/runs/{identifier}")
def report(identifier: str):
    result = load(identifier)
    if not result:
        raise HTTPException(404, "Run not found")
    return result


@app.post("/api/compare")
def comparison(body: Comparison):
    before = load(body.before)
    after = load(body.after)
    if not before or not after:
        raise HTTPException(404, "Run not found")
    try:
        return compare(before, after)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


mount_ui(app)
