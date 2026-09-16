"use client";

import { useEffect, useState } from "react";
import AdminGuard from "@/components/AdminGuard";
import { api, AdminCostSummary, AdminUsageLog, AdminUserCost } from "@/lib/api";

export default function AdminCostsPage() {
  const [summary, setSummary] = useState<AdminCostSummary | null>(null);
  const [userCosts, setUserCosts] = useState<AdminUserCost[]>([]);
  const [logs, setLogs] = useState<AdminUsageLog[]>([]);
  const [days, setDays] = useState(30);
  const [endpointFilter, setEndpointFilter] = useState<string>("");
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");

  // Model settings
  const [modelSettings, setModelSettings] = useState({
    text_model: "gemini-3.5-flash",
    vision_model: "gemini-3.5-flash",
    vision_provider: "gemini",
  });
  const [savingSettings, setSavingSettings] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Inspector modal for prompt/response telemetry
  const [selectedLog, setSelectedLog] = useState<AdminUsageLog | null>(null);
  const [copiedField, setCopiedField] = useState<string | null>(null);

  const copyToClipboard = (text: string, field: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const loadData = async () => {
    setBusy(true);
    setError("");
    try {
      const [sumData, usersData, logsData, modelsData] = await Promise.all([
        api.adminCostSummary(days),
        api.adminUserCosts(days, endpointFilter || undefined),
        api.adminUsageLogs(50, endpointFilter || undefined),
        api.adminModelSettings(),
      ]);
      setSummary(sumData);
      setUserCosts(usersData);
      setLogs(logsData);
      setModelSettings(modelsData);
    } catch (err: any) {
      setError(err?.message || "Failed to load admin cost metrics");
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [days, endpointFilter]);

  const handleSaveModels = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingSettings(true);
    setSaveSuccess(false);
    try {
      await api.updateAdminModelSettings(modelSettings);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err: any) {
      alert("Failed to update models: " + err?.message);
    } finally {
      setSavingSettings(false);
    }
  };

  return (
    <AdminGuard>
      <div className="max-w-6xl mx-auto px-4 py-8 space-y-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
              AI Costs & Observability
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Real-time token telemetry, live model switcher, and user cost attribution.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="bg-white border border-slate-300 text-slate-700 text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value={1}>Last 24 hours</option>
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
            <button
              onClick={loadData}
              disabled={busy}
              className="px-3 py-1.5 bg-slate-900 text-white rounded-lg text-sm font-medium hover:bg-slate-800 disabled:opacity-50 transition"
            >
              {busy ? "Refreshing..." : "Refresh"}
            </button>
          </div>
        </div>

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
            {error}
          </div>
        )}

        {/* Global Live Model Switcher Card */}
        <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-950 text-white rounded-xl p-6 shadow-md">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
                Live Model & Provider Switcher
              </h2>
              <p className="text-xs text-slate-300 mt-0.5">
                Switch default AI models dynamically across all backend workers without restarting containers.
              </p>
            </div>
            {saveSuccess && (
              <span className="text-xs font-semibold px-2.5 py-1 bg-emerald-500/30 text-emerald-300 border border-emerald-500/50 rounded-full">
                Saved & Active
              </span>
            )}
          </div>

          <form onSubmit={handleSaveModels} className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Text & Narration Model
              </label>
              <select
                value={modelSettings.text_model}
                onChange={(e) =>
                  setModelSettings({ ...modelSettings, text_model: e.target.value })
                }
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:ring-2 focus:ring-emerald-400 focus:outline-none"
              >
                <option value="gemini-3.5-flash">Gemini 3.5 Flash ($0.075 / 1M)</option>
                <option value="gemini-2.0-flash">Gemini 2.0 Flash ($0.075 / 1M)</option>
                <option value="gemini-1.5-flash">Gemini 1.5 Flash ($0.075 / 1M)</option>
                <option value="gemini-1.5-pro">Gemini 1.5 Pro ($1.25 / 1M)</option>
                <option value="qwen2.5:3b">Local Ollama (qwen2.5:3b - Free)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Vision & OCR Model
              </label>
              <select
                value={modelSettings.vision_model}
                onChange={(e) =>
                  setModelSettings({ ...modelSettings, vision_model: e.target.value })
                }
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:ring-2 focus:ring-emerald-400 focus:outline-none"
              >
                <option value="gemini-3.5-flash">Gemini 3.5 Flash</option>
                <option value="gemini-2.0-flash">Gemini 2.0 Flash</option>
                <option value="gemini-1.5-flash">Gemini 1.5 Flash</option>
                <option value="qwen2.5vl:3b">Local Ollama (qwen2.5vl:3b)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Vision OCR Provider
              </label>
              <div className="flex gap-2">
                <select
                  value={modelSettings.vision_provider}
                  onChange={(e) =>
                    setModelSettings({ ...modelSettings, vision_provider: e.target.value })
                  }
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:ring-2 focus:ring-emerald-400 focus:outline-none"
                >
                  <option value="gemini">Gemini Cloud Vision</option>
                  <option value="ollama">Ollama Local Vision</option>
                  <option value="fallback">Fallback (Ollama → Gemini)</option>
                </select>
                <button
                  type="submit"
                  disabled={savingSettings}
                  className="px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-semibold rounded-lg text-sm transition disabled:opacity-50"
                >
                  {savingSettings ? "Saving..." : "Apply"}
                </button>
              </div>
            </div>
          </form>
        </div>

        {/* KPI Top Cards */}
        {summary && (
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <div className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                Today's Cost
              </div>
              <div className="mt-2 text-3xl font-extrabold text-slate-900">
                ${summary.today.cost_usd.toFixed(4)}
              </div>
              <div className="mt-1.5 flex items-center gap-1.5 text-[11px] font-mono">
                <span className="text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded" title="Input Prompt Cost">
                  In: ${(summary.today.prompt_cost_usd ?? 0).toFixed(4)}
                </span>
                <span className="text-amber-700 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded font-medium" title="Output Completion Cost">
                  Out: ${(summary.today.completion_cost_usd ?? 0).toFixed(4)}
                </span>
              </div>
              <div className="mt-1 text-[11px] text-slate-400">
                {summary.today.calls.toLocaleString()} calls today
              </div>
            </div>

            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <div className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                {days}-Day Spend
              </div>
              <div className="mt-2 text-3xl font-extrabold text-emerald-600">
                ${summary.period.cost_usd.toFixed(4)}
              </div>
              <div className="mt-1.5 flex items-center gap-1.5 text-[11px] font-mono">
                <span className="text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded" title="Period Input Cost">
                  In: ${(summary.period.prompt_cost_usd ?? 0).toFixed(4)}
                </span>
                <span className="text-amber-700 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded font-medium" title="Period Output Cost">
                  Out: ${(summary.period.completion_cost_usd ?? 0).toFixed(4)}
                </span>
              </div>
              <div className="mt-1 text-[11px] text-slate-400">
                {summary.period.calls.toLocaleString()} total API requests
              </div>
            </div>

            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <div className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                Total Tokens
              </div>
              <div className="mt-2 text-3xl font-extrabold text-slate-900">
                {summary.period.total_tokens.toLocaleString()}
              </div>
              <div className="mt-1 text-xs text-slate-500">
                Prompt: {summary.period.prompt_tokens.toLocaleString()} | Resp: {summary.period.completion_tokens.toLocaleString()}
              </div>
            </div>

            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <div className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                Avg Latency
              </div>
              <div className="mt-2 text-3xl font-extrabold text-indigo-600">
                {Math.round(summary.period.avg_latency_ms)} ms
              </div>
              <div className="mt-1 text-xs text-slate-500">
                End-to-end LLM round-trip
              </div>
            </div>
          </div>
        )}

        {/* Feature & Model Breakdown */}
        {summary && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <h3 className="font-semibold text-slate-900 text-sm mb-4">
                Cost Breakdown by Feature
              </h3>
              <div className="space-y-3">
                {summary.by_endpoint.length === 0 ? (
                  <p className="text-xs text-slate-400">No feature usage recorded yet.</p>
                ) : (
                  summary.by_endpoint.map((item) => {
                    const totalCost = summary.period.cost_usd || 1;
                    const pct = Math.min(100, Math.round((item.cost_usd / totalCost) * 100));
                    return (
                      <div key={item.endpoint} className="space-y-1">
                        <div className="flex justify-between text-xs font-medium text-slate-700">
                          <span className="capitalize">{item.endpoint.replace("_", " ")}</span>
                          <span>
                            ${item.cost_usd.toFixed(4)} ({item.calls} calls)
                          </span>
                        </div>
                        <div className="w-full bg-slate-100 rounded-full h-2">
                          <div
                            className="bg-emerald-500 h-2 rounded-full"
                            style={{ width: `${Math.max(5, pct)}%` }}
                          />
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <h3 className="font-semibold text-slate-900 text-sm mb-4">
                Cost by Model
              </h3>
              <div className="space-y-3">
                {summary.by_model.length === 0 ? (
                  <p className="text-xs text-slate-400">No model usage recorded yet.</p>
                ) : (
                  summary.by_model.map((item) => {
                    const totalCost = summary.period.cost_usd || 1;
                    const pct = Math.min(100, Math.round((item.cost_usd / totalCost) * 100));
                    return (
                      <div key={item.model_name} className="space-y-1">
                        <div className="flex justify-between text-xs font-medium text-slate-700">
                          <span>{item.model_name}</span>
                          <span>
                            ${item.cost_usd.toFixed(4)} ({item.total_tokens.toLocaleString()} tok)
                          </span>
                        </div>
                        <div className="w-full bg-slate-100 rounded-full h-2">
                          <div
                            className="bg-indigo-500 h-2 rounded-full"
                            style={{ width: `${Math.max(5, pct)}%` }}
                          />
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>
        )}

        {/* User Cost Leaderboard */}
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="font-semibold text-slate-900 text-base">
                User Cost Attribution & Ranking
              </h3>
              <p className="text-xs text-slate-500">
                Identify top spenders, heavy OCR consumers, or abusive traffic.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <select
                value={endpointFilter}
                onChange={(e) => setEndpointFilter(e.target.value)}
                className="bg-slate-50 border border-slate-300 text-slate-700 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none"
              >
                <option value="">All Features</option>
                <option value="ocr">OCR Only</option>
                <option value="narration">Narration Only</option>
                <option value="graph_grade">Graph Grade Only</option>
                <option value="correction">Corrections Only</option>
              </select>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500 text-xs font-semibold uppercase tracking-wider border-b border-slate-200">
                <tr>
                  <th className="px-5 py-3">Rank</th>
                  <th className="px-5 py-3">User Email</th>
                  <th className="px-5 py-3">API Requests</th>
                  <th className="px-5 py-3">Total Tokens</th>
                  <th className="px-5 py-3">Total Cost (USD)</th>
                  <th className="px-5 py-3">Last Active</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {userCosts.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-5 py-8 text-center text-slate-400 text-sm">
                      No user API consumption recorded in this period.
                    </td>
                  </tr>
                ) : (
                  userCosts.map((u, i) => (
                    <tr key={u.user_id + i} className="hover:bg-slate-50 transition">
                      <td className="px-5 py-3 font-semibold text-slate-400 text-xs">
                        #{i + 1}
                      </td>
                      <td className="px-5 py-3 font-medium text-slate-900">
                        {u.email}
                      </td>
                      <td className="px-5 py-3 text-slate-600">
                        {u.total_calls.toLocaleString()}
                      </td>
                      <td className="px-5 py-3 text-slate-600">
                        {u.total_tokens.toLocaleString()}
                      </td>
                      <td className="px-5 py-3 font-semibold text-emerald-600">
                        ${u.total_cost_usd.toFixed(4)}
                      </td>
                      <td className="px-5 py-3 text-slate-400 text-xs">
                        {u.last_active ? new Date(u.last_active).toLocaleString() : "—"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Real-time Logs Feed */}
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-200">
            <h3 className="font-semibold text-slate-900 text-base">
              Recent API Telemetry Feed
            </h3>
            <p className="text-xs text-slate-500">
              Live audit stream of the last 50 LLM / OCR requests.
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider border-b border-slate-200">
                <tr>
                  <th className="px-4 py-2.5">Time</th>
                  <th className="px-4 py-2.5">Endpoint</th>
                  <th className="px-4 py-2.5">Model</th>
                  <th className="px-4 py-2.5">User</th>
                  <th className="px-4 py-2.5">Tokens (In / Out)</th>
                  <th className="px-4 py-2.5">Cost (Total / Out)</th>
                  <th className="px-4 py-2.5">Latency</th>
                  <th className="px-4 py-2.5">Status</th>
                  <th className="px-4 py-2.5 text-right">Inspect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {logs.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="px-4 py-6 text-center text-slate-400 font-sans text-xs">
                      No logs recorded yet.
                    </td>
                  </tr>
                ) : (
                  logs.map((log) => (
                    <tr
                      key={log.id}
                      onClick={() => setSelectedLog(log)}
                      className="hover:bg-slate-50 transition cursor-pointer group"
                    >
                      <td className="px-4 py-2 text-slate-400">
                        {new Date(log.created_at).toLocaleTimeString()}
                      </td>
                      <td className="px-4 py-2 font-sans font-medium text-slate-700 capitalize">
                        {log.endpoint.replace(/_/g, " ")}
                      </td>
                      <td className="px-4 py-2 text-slate-600">{log.model_name}</td>
                      <td className="px-4 py-2 font-sans text-slate-600 truncate max-w-[140px]">
                        {log.email}
                      </td>
                      <td className="px-4 py-2 text-slate-700">
                        <div>{log.total_tokens.toLocaleString()}</div>
                        <div className="text-[10px] text-slate-400">
                          {log.prompt_tokens.toLocaleString()} in / {log.completion_tokens.toLocaleString()} out
                        </div>
                      </td>
                      <td className="px-4 py-2">
                        <div className="font-semibold text-emerald-600">
                          ${log.estimated_cost_usd.toFixed(5)}
                        </div>
                        <div className="text-[10px] text-amber-600 font-medium">
                          Out: ${(log.completion_cost_usd ?? 0).toFixed(5)}
                        </div>
                      </td>
                      <td className="px-4 py-2 text-slate-600">{log.latency_ms}ms</td>
                      <td className="px-4 py-2">
                        {log.success ? (
                          <span className="px-2 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded text-[10px] font-sans font-medium">
                            OK
                          </span>
                        ) : (
                          <span
                            title={log.error_message || "Error"}
                            className="px-2 py-0.5 bg-red-50 text-red-700 border border-red-200 rounded text-[10px] font-sans font-medium cursor-help"
                          >
                            FAIL
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-2 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedLog(log);
                          }}
                          className="px-2.5 py-1 bg-slate-100 hover:bg-indigo-50 hover:text-indigo-600 text-slate-600 rounded text-[11px] font-sans font-medium transition border border-slate-200"
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Modal: Prompt & Response Telemetry Inspector */}
        {selectedLog && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-150">
            <div
              className="bg-white w-full max-w-4xl max-h-[90vh] rounded-2xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Modal Header */}
              <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
                <div className="flex items-center gap-3">
                  <span className="px-2.5 py-1 bg-indigo-100 text-indigo-800 text-xs font-semibold rounded-md uppercase tracking-wider">
                    {selectedLog.endpoint.replace(/_/g, " ")}
                  </span>
                  <div>
                    <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                      <span>API Call Inspection</span>
                      <span className="text-xs font-mono font-normal text-slate-500">
                        ({selectedLog.model_name})
                      </span>
                    </h3>
                    <p className="text-xs text-slate-500">
                      Executed at {new Date(selectedLog.created_at).toLocaleString()} • Latency: {selectedLog.latency_ms}ms
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setSelectedLog(null)}
                  className="w-8 h-8 rounded-full flex items-center justify-center text-slate-400 hover:text-slate-600 hover:bg-slate-200/60 transition text-lg font-bold"
                >
                  ✕
                </button>
              </div>

              {/* Modal Cost & Telemetry Strip */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 px-6 py-3 bg-slate-100/70 border-b border-slate-200 font-mono text-xs">
                <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                  <div className="text-[10px] text-slate-500 uppercase tracking-wider font-sans">Total Cost</div>
                  <div className="text-sm font-bold text-emerald-600 mt-0.5">
                    ${selectedLog.estimated_cost_usd.toFixed(6)}
                  </div>
                </div>
                <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                  <div className="text-[10px] text-slate-500 uppercase tracking-wider font-sans">Output Cost (Completion)</div>
                  <div className="text-sm font-bold text-amber-600 mt-0.5">
                    ${(selectedLog.completion_cost_usd ?? 0).toFixed(6)}
                  </div>
                  <div className="text-[10px] text-slate-400 font-sans">
                    {selectedLog.completion_tokens.toLocaleString()} tokens
                  </div>
                </div>
                <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                  <div className="text-[10px] text-slate-500 uppercase tracking-wider font-sans">Input Cost (Prompt)</div>
                  <div className="text-sm font-bold text-slate-700 mt-0.5">
                    ${(selectedLog.prompt_cost_usd ?? 0).toFixed(6)}
                  </div>
                  <div className="text-[10px] text-slate-400 font-sans">
                    {selectedLog.prompt_tokens.toLocaleString()} tokens
                  </div>
                </div>
                <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                  <div className="text-[10px] text-slate-500 uppercase tracking-wider font-sans">Status / Latency</div>
                  <div className="text-sm font-bold mt-0.5 flex items-center gap-1.5">
                    <span className={selectedLog.success ? "text-emerald-600" : "text-red-600"}>
                      {selectedLog.success ? "SUCCESS" : "FAILED"}
                    </span>
                    <span className="text-slate-400 font-normal">({selectedLog.latency_ms}ms)</span>
                  </div>
                </div>
              </div>

              {/* Error alert if any */}
              {selectedLog.error_message && (
                <div className="mx-6 mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
                  <span className="font-bold">Error:</span> {selectedLog.error_message}
                </div>
              )}

              {/* Prompt & Response Scrollable Viewers */}
              <div className="flex-1 overflow-y-auto p-6 space-y-5">
                {/* Prompt Section */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-blue-500" />
                      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 font-sans">
                        Prompt Sent to AI (Input)
                      </h4>
                      <span className="text-[11px] text-slate-400 font-mono">
                        ({selectedLog.prompt_text ? `${selectedLog.prompt_text.length.toLocaleString()} chars` : "0 chars"})
                      </span>
                    </div>
                    {selectedLog.prompt_text && (
                      <button
                        onClick={() => copyToClipboard(selectedLog.prompt_text || "", "prompt")}
                        className="px-2.5 py-1 text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 rounded transition font-sans flex items-center gap-1"
                      >
                        {copiedField === "prompt" ? "✓ Copied!" : "Copy Prompt"}
                      </button>
                    )}
                  </div>
                  <div className="bg-slate-900 text-slate-100 p-4 rounded-xl font-mono text-xs overflow-x-auto max-h-64 overflow-y-auto whitespace-pre-wrap leading-relaxed border border-slate-800 selection:bg-indigo-600">
                    {selectedLog.prompt_text || (
                      <span className="text-slate-500 italic">No prompt text recorded for this call.</span>
                    )}
                  </div>
                </div>

                {/* Response Section */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-emerald-500" />
                      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 font-sans">
                        Raw AI Response (Output)
                      </h4>
                      <span className="text-[11px] text-slate-400 font-mono">
                        ({selectedLog.response_text ? `${selectedLog.response_text.length.toLocaleString()} chars` : "0 chars"})
                      </span>
                    </div>
                    {selectedLog.response_text && (
                      <button
                        onClick={() => copyToClipboard(selectedLog.response_text || "", "response")}
                        className="px-2.5 py-1 text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 rounded transition font-sans flex items-center gap-1"
                      >
                        {copiedField === "response" ? "✓ Copied!" : "Copy Response"}
                      </button>
                    )}
                  </div>
                  <div className="bg-slate-900 text-emerald-400 p-4 rounded-xl font-mono text-xs overflow-x-auto max-h-64 overflow-y-auto whitespace-pre-wrap leading-relaxed border border-slate-800 selection:bg-emerald-700">
                    {selectedLog.response_text || (
                      <span className="text-slate-500 italic">No output text recorded for this call.</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Modal Footer */}
              <div className="px-6 py-3 bg-slate-50 border-t border-slate-200 flex justify-end">
                <button
                  onClick={() => setSelectedLog(null)}
                  className="px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs font-semibold transition"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AdminGuard>
  );
}
