# Redteam Ledger

**可复现安全评测与回归证据台账**  
A detector evaluation ledger with frozen synthetic fixtures, paired comparisons, Wilson intervals, target-error accounting and CI regression gates.

[![CI](https://github.com/rodriguezrobertbfrkx6857-sudo/redteam-ledger/actions/workflows/ci.yml/badge.svg)](https://github.com/rodriguezrobertbfrkx6857-sudo/redteam-ledger/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.12-3776AB) ![TypeScript](https://img.shields.io/badge/TypeScript-React-3178C6) ![License](https://img.shields.io/badge/license-MIT-green)

![Workbench screenshot](docs/screenshot.png)

## 为什么做

只看拦截率会隐藏正常请求被误拦和目标服务出错。这个项目冻结数据集与评分器版本，分开记录 TP/FN/FP/TN/错误，并逐样本比较两次实验的改善和回归。

本项目是可运行、可扩展的安全工程作品集原型。没有宣称研究算法原创、生产认证、真实用户规模或未执行的大模型实验。核心差异在可检查的实现、失败行为和证据闭环。

## 已实现

- 36 条原创合成样本，包含中英文、角色伪装、编码、隐藏字符和正常引用攻击文本的负样本。
- keyword / normalized 两个基线与 Sentinel Gate HTTP 目标；有界线程池并发，目标地址只由服务端配置。
- 漏报率、误报率、precision、recall、Wilson 95% 区间、P95 延迟及类别混淆矩阵。
- 仅允许数据集哈希与 grader 版本一致的配对比较；目标错误不视为安全，门禁显式失败；CLI 可返回非零退出码。

## 本地启动

需要 Python 3.12+、uv、Node.js 22.12+。默认不需要模型密钥。

```bash
git clone https://github.com/rodriguezrobertbfrkx6857-sudo/redteam-ledger.git
cd redteam-ledger
uv sync --frozen
cd web
npm ci
npm run build
cd ..
uv run uvicorn app.main:app --host 127.0.0.1 --port 8114
```

浏览器访问 http://127.0.0.1:8114 ，API 文档位于 `/docs`。Windows 也可运行 `./run.ps1`。

Docker：`docker compose up --build`。Compose 仅将服务绑定到本机环回地址。镜像使用非 root 用户；数据存放在命名卷。Docker 构建与健康检查由 CI 执行，状态以 Actions 结果为准。

开发热更新：终端 A 启动上述后端命令并增加 `--reload`；终端 B 在 `web/` 执行 `npm run dev`，Vite 将 `/api` 代理至 8114。

## 三分钟演示

1. 运行 keyword 的 challenge 分区，保存结果作为基线。
2. 运行 normalized 的相同分区，查看漏报与误报的共同变化。
3. 选择前一次运行做配对比较，导出 JSON；也可启动 Sentinel Gate 后评测真实 HTTP 服务。

## 架构

```mermaid
flowchart LR
    FrozenCases --> DatasetHash
    DatasetHash --> BoundedWorkers
    BoundedWorkers --> TargetAdapter
    TargetAdapter --> PerCaseResult
    PerCaseResult --> ConfusionMatrix
    ConfusionMatrix --> WilsonInterval
    PerCaseResult --> PairedComparison
    PairedComparison --> RegressionGate
    RegressionGate --> StoredReport
```

技术栈：FastAPI / Pydantic、SQLite WAL、React 19 / TypeScript / Vite、pytest、Playwright、GitHub Actions。前后端同源发布，不需要独立代理即可运行。

目录：`app/` 核心逻辑与 API，`web/src/` 交互界面，`tests/` 单元/集成/对抗测试，`web/e2e/` 浏览器测试，`fixtures/` 合成演示数据，`docs/` 架构与验证证据。

## API

| 接口 | 约定 |
| --- | --- |
| `GET /api/dataset` | 查看合成样本与分区 |
| `GET / POST /api/runs` | 历史报告或新建评测 |
| `GET /api/runs/{id}` | 完整证据报告 |
| `POST /api/compare` | before + after → 逐样本改善/回归 |
| `GET /api/health` | 健康与版本 |
| `GET /api/audit` | 元数据审计记录与链校验 |

所有请求体限制为 128 KiB；领域模型拒绝未声明字段。错误使用标准 HTTP 状态码，UI 显式呈现错误。

## 验证

```bash
uv run ruff check app tests
uv run pytest --cov=app --cov-report=term-missing
cd web
npm run build
npx playwright install chromium
npm run test:e2e
```

浏览器测试使用独立 `data/e2e.sqlite3`，覆盖主工作流、审计与 390px 移动布局。可用 `UPDATE_SCREENSHOTS=1` 更新截图（PowerShell 使用 `$env:UPDATE_SCREENSHOTS='1'`）。

实际检查结果及局限见 [VALIDATION.md](docs/VALIDATION.md)。安全设计见 [SECURITY.md](SECURITY.md)。

## 边界与取舍

- 这是检测器评测，attack_miss_rate 不是大模型攻击成功率；没有声称完成真实模型越狱评测。
- 36 条合成样本不足以估计真实部署效果；challenge 是固定分区，不是第三方保密测试集。
- Wilson 区间只描述给定样本的二项比例估计，样本相关性与分布偏差仍然存在。
- P95 由本次目标调用墙钟时间得到，小样本性能指标不代表生产容量；基线门禁失败是有效实验结果。

审计使用 SHA256 链，可发现已保存事件的内容修改或重排；没有外部锚定，无法检测整链重写或尾部截断，因此不是防管理员篡改的不可变账本。

## 可扩展路线（尚未实现）

- [ ] 引入按模板家族分组的独立测试集，控制数据泄漏，并扩展到多轮与跨语言攻击。
- [ ] 增加独立的真实模型 canary 泄露评测任务，使用不同 grader 与任务标识，禁止与检测指标混比。
- [ ] 接入可授权的开放数据集，记录许可证、版本与污染检查；添加 paired bootstrap 和成本预算。

## 简历与讲解

见 [RESUME.md](docs/RESUME.md)：提供中文/英文讲解框架、可验证表述和面试问题。只写自己能复现和解释的功能；不要将原型描述为企业生产项目。

## 相关工作与资料

- [OWASP Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)：应用层威胁与防御背景。
- [NIST Adversarial ML Taxonomy](https://doi.org/10.6028/NIST.AI.100-2e2025)：威胁术语与分类。
- [Anthropic: Demystifying evals](https://www.anthropic.com/research/demystifying-evals-for-ai-agents)：评测与评分器设计背景。
- [NVIDIA garak](https://github.com/NVIDIA/garak)、[LLM Guard](https://github.com/protectai/llm-guard)、[Presidio](https://github.com/microsoft/presidio)：相邻领域成熟开源系统，适合后续对照与集成。本项目没有复制这些仓库的实现，也没有声称性能超过它们。
- [Ollama chat API](https://docs.ollama.com/api/chat)：可选本地模型协议。

同系列：[Sentinel Gate](https://github.com/rodriguezrobertbfrkx6857-sudo/sentinel-gate) · [Evidence RAG](https://github.com/rodriguezrobertbfrkx6857-sudo/evidence-rag) · [Agent Permit](https://github.com/rodriguezrobertbfrkx6857-sudo/agent-permit) · [Privacy Relay](https://github.com/rodriguezrobertbfrkx6857-sudo/privacy-relay)

## 许可证

代码 MIT。原创合成 fixtures 以 CC0-1.0 提供；依赖遵循各自许可证。仓库不包含第三方私有数据、模型权重或真实密钥。

## CLI 与真实服务联测

```bash
uv run python -m app.cli --target normalized --split challenge --output report.json
uv run python -m app.cli --target normalized --split challenge --output report.json --gate
```

`--gate` 失败返回 1；不要为了让 CI 变绿而隐去失败。默认门禁：漏报 ≤25%、误报 ≤15%、目标错误为 0。正常演示基线可能无法达标。

启动 Sentinel Gate 的 8111 端口后执行 `uv run python -m app.cli --target sentinel --split all --output report.json`。其他端口通过服务端 `SENTINEL_URL` 环境变量配置。

实际联测与失败分析：[EXPERIMENT.md](docs/EXPERIMENT.md)。
