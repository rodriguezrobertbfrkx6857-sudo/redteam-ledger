import { useState, useEffect } from "react";
import { FlaskConical, ArrowRight } from "lucide-react";
import {
  Shell,
  Card,
  Metrics,
  api,
  Json,
  ErrorBox,
  Empty,
  Badge,
  download,
} from "./ui";
const percent = (x: number | null) =>
  x === null ? "N/A" : (x * 100).toFixed(1) + "%";
export default function App() {
  const [target, setTarget] = useState("normalized"),
    [split, setSplit] = useState("challenge"),
    [result, setResult] = useState<any>(null),
    [runs, setRuns] = useState<any[]>([]),
    [before, setBefore] = useState(""),
    [comparison, setComparison] = useState<any>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function refresh() {
    setRuns((await api("/runs")).runs);
  }
  useEffect(() => {
    refresh().catch((e) => setError(String(e)));
  }, []);
  async function action(fn: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Shell
      title="Redteam Ledger"
      subtitle="把安全改进变成可复现的实验。冻结数据集、分离挑战集，比较错误类型，并让回归门禁有据可查。"
      number="04"
    >
      <Metrics
        items={[
          [
            "攻击漏报率",
            result ? percent(result.metrics.attack_miss_rate) : "—",
          ],
          [
            "正常请求误报率",
            result ? percent(result.metrics.false_positive_rate) : "—",
          ],
          ["已完成实验", runs.length],
        ]}
      />
      <ErrorBox error={error} />
      <div className="columns">
        <div>
          <Card title="配置一次评测" kicker="01 / EVALUATE">
            <label htmlFor="target">被测目标</label>
            <select
              id="target"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
            >
              <option value="keyword">Keyword · 词面基线</option>
              <option value="normalized">Normalized · 规范化基线</option>
              <option value="sentinel">Sentinel Gate · 真实 HTTP 服务</option>
            </select>
            <label htmlFor="split">数据分区</label>
            <select
              id="split"
              value={split}
              onChange={(e) => setSplit(e.target.value)}
            >
              <option value="challenge">Challenge / 挑战集</option>
              <option value="dev">Development / 开发集</option>
              <option value="all">All / 全部合成样本</option>
            </select>
            <button
              className="primary"
              disabled={busy}
              onClick={() =>
                action(async () => {
                  setComparison(null);
                  setResult(await api("/runs", { target, split, workers: 4 }));
                  await refresh();
                })
              }
            >
              <FlaskConical size={16} />
              {busy ? "评测运行中…" : "运行可复现实验"}
              <ArrowRight size={16} />
            </button>
            <p className="note">
              当前测量的是注入检测器的漏报与误报，不是大模型攻击成功率。样本为原创合成数据，不代表外部基准。
            </p>
            <div className="step">
              <b>Miss rate ≤ 25%</b>
              <span>REGRESSION GATE</span>
            </div>
            <div className="step">
              <b>False positive ≤ 15%</b>
              <span>UTILITY BUDGET</span>
            </div>
            <div className="step">
              <b>Target errors = 0</b>
              <span>FAIL CLOSED</span>
            </div>
          </Card>
          <Card title="配对回归比较" kicker="02 / COMPARE">
            <label htmlFor="baseline">选择历史基线</label>
            <select
              id="baseline"
              value={before}
              onChange={(e) => setBefore(e.target.value)}
            >
              <option value="">选择同一数据集的历史运行</option>
              {runs
                .filter((r) => r.id !== result?.id)
                .map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.target} / {r.split} / {r.id.slice(0, 8)}
                  </option>
                ))}
            </select>
            <button
              className="primary"
              disabled={busy || !before || !result}
              onClick={() =>
                action(async () =>
                  setComparison(
                    await api("/compare", { before, after: result.id }),
                  ),
                )
              }
            >
              与当前运行比较
            </button>
            {comparison && (
              <>
                <p>
                  改善 {comparison.improvements.length} 项 · 回归{" "}
                  {comparison.regressions.length} 项
                </p>
                <Badge good={comparison.gate_passed}>
                  {comparison.gate_passed ? "PASS" : "GATE FAILED"}
                </Badge>
                <Json value={comparison} />
              </>
            )}
          </Card>
        </div>
        <Card title="实验报告" kicker="03 / EVIDENCE">
          {result ? (
            <>
              <div className="result-head">
                <Badge good={result.gate.passed}>
                  {result.gate.passed ? "GATE PASSED" : "GATE FAILED"}
                </Badge>
                <small>P95 {result.p95_latency_ms} ms</small>
              </div>
              <p className="note">
                SHA256 {result.dataset_sha256.slice(0, 30)}…
              </p>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>类别</th>
                      <th>TP</th>
                      <th>FN</th>
                      <th>FP</th>
                      <th>TN</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(result.categories).map(
                      ([k, m]: [string, any]) => (
                        <tr key={k}>
                          <td>{k}</td>
                          <td>{m.tp}</td>
                          <td>{m.fn}</td>
                          <td>{m.fp}</td>
                          <td>{m.tn}</td>
                        </tr>
                      ),
                    )}
                  </tbody>
                </table>
              </div>
              <p className="note">
                漏报率 Wilson 95% 区间：
                {result.metrics.miss_wilson95?.map(percent).join(" – ") ||
                  "N/A"}
                <br />
                错误请求 {result.metrics.errors} / {result.metrics.total}
                （错误不会计为防御成功）
              </p>
              <button
                onClick={() =>
                  download("evaluation-" + result.id + ".json", result)
                }
              >
                导出完整报告 ↓
              </button>
              <Json value={result} />
              <h3 className="small">逐样本追踪</h3>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Case ID</th>
                      <th>预期</th>
                      <th>检测</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.rows.map((r: any) => (
                      <tr key={r.id}>
                        <td>{r.id}</td>
                        <td>{r.expected ? "Attack" : "Benign"}</td>
                        <td>
                          <Badge good={r.flagged === r.expected}>
                            {r.flagged === null
                              ? "ERROR"
                              : r.flagged
                                ? "FLAGGED"
                                : "ALLOWED"}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <Empty text="运行词面基线，再用规范化基线做配对比较。" />
          )}
        </Card>
      </div>
    </Shell>
  );
}
