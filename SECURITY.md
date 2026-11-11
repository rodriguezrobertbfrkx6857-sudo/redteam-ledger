# Security model

## Intended scope

Redteam Ledger is a single-user, local research workbench. Bind to loopback. Code publication on GitHub does not deploy a public service. Host/origin checks reduce browser-to-local attacks but do not provide user authentication. Except for Agent Permit's role-separated routes, APIs are local and unauthenticated. Before shared deployment, add identity, authorization, TLS, quotas, retention and tenant isolation.

## Trust boundaries

| Boundary | Control | Residual risk |
| --- | --- | --- |
| Browser → API | Local binding, trusted Host and Origin, strict body schema, 128 KiB limit | Local programs can still call the API; no global rate limit |
| Untrusted text → HTML | React text rendering; no raw HTML injection | Dependencies and browser extensions remain trusted |
| API → SQLite | Parameterized SQL, WAL, explicit write transactions | Local operator can read/modify DB; no at-rest encryption |
| Audit events → evidence | Metadata-only records, SHA256 chaining | No external anchor; truncation and complete rewrite undetectable |
| Server → optional model | Operator-controlled endpoint, bounded timeout, no redirects | Misconfigured endpoint or malicious provider still matters |

`TRUSTED_HOSTS` is an operator environment setting, comma-separated; defaults to localhost, 127.0.0.1 and testserver. Do not set a wildcard for a shared deployment. `APP_DB` chooses a local database path. Keep `data/`, `.env`, session capabilities and reviewer keys out of Git.

## Project-specific assumptions

- 这是检测器评测，attack_miss_rate 不是大模型攻击成功率；没有声称完成真实模型越狱评测。
- 36 条合成样本不足以估计真实部署效果；challenge 是固定分区，不是第三方保密测试集。
- Wilson 区间只描述给定样本的二项比例估计，样本相关性与分布偏差仍然存在。
- P95 由本次目标调用墙钟时间得到，小样本性能指标不代表生产容量；基线门禁失败是有效实验结果。

## Reporting

Use GitHub private vulnerability reporting if enabled. Otherwise open an issue containing only a minimal synthetic reproduction, never real secrets or customer data. This project does not claim production readiness or comprehensive LLM safety guarantees.
