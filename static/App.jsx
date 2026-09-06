import React, { useState } from 'react';

// Preset Scenarios Data
const PRESETS = [
    { id: 1, label: '⚡ DB Pool Exhaustion', text: 'Payment service experiencing high error rate and database connection acquisition timeout under load.' },
    { id: 2, label: '⚡ Bad Deployment', text: 'Immediate 100% error rate on payment requests following recent deployment release v2.4.1.' },
    { id: 3, label: '⚡ Memory Leak Spike', text: 'Gradually climbing response latency and high heap memory usage alerts on payment_service.' },
    { id: 4, label: '⚡ Gateway Timeout', text: 'Extreme latency spikes (30s) and gateway timeout errors when processing payment transactions.' },
    { id: 5, label: '⚡ Red-Herring Warning', text: 'Transient benign cache query warning in logs while overall service latency and error rates remain normal.' },
];

export default function App() {
    const [inputAlert, setInputAlert] = useState('');
    const [loading, setLoading] = useState(false);
    const [resultState, setResultState] = useState(null);
    const [benchmarkData, setBenchmarkData] = useState(null);
    const [activeStep, setActiveStep] = useState(0);

    // Apply Preset Scenario
    const applyPreset = (text) => {
        setInputAlert(text);
    };

    // Trigger AI Agent Investigation
    const handleInvestigate = async () => {
        if (!inputAlert.trim()) return;
        setLoading(true);
        setActiveStep(1);

        try {
            // Simulate step progress for visual feedback
            const stepInterval = setInterval(() => {
                setActiveStep((prev) => (prev < 6 ? prev + 1 : prev));
            }, 300);

            const res = await fetch('/api/v1/investigate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ raw_description: inputAlert })
            });

            clearInterval(stepInterval);
            const data = await res.json();
            setResultState(data);
            setActiveStep(6);
        } catch (err) {
            console.error("Investigation failed:", err);
        } finally {
            setLoading(false);
        }
    };

    // Trigger Benchmark Evaluation
    const runBenchmark = async () => {
        setLoading(true);
        try {
            const res = await fetch('/api/v1/benchmark');
            const data = await res.json();
            setBenchmarkData(data);
        } catch (err) {
            console.error("Benchmark failed:", err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="bg-[#0b0f19] text-gray-100 min-h-screen font-sans flex flex-col">
            <!-- Header -->
            <header className="border-b border-gray-800 bg-[#111827]/90 backdrop-blur sticky top-0 z-50 px-6 py-4 flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 font-bold text-xl">
                        🛡️
                    </div>
                    <div>
                        <h1 className="font-bold text-lg text-white">AI Incident Investigation Console (React.js)</h1>
                        <p className="text-xs text-gray-400">Agentic SRE Platform • LangGraph • MCP Tools</p>
                    </div>
                </div>
                <div className="flex items-center space-x-3">
                    <span className="px-3 py-1 rounded-full text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center">
                        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse mr-2"></span> System Active
                    </span>
                    <button onClick={runBenchmark} className="px-3 py-1.5 text-xs bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-lg border border-gray-700 transition">
                        📊 Run Benchmark (30 Evs)
                    </button>
                </div>
            </header>

            <!-- Main Workspace -->
            <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-8 space-y-8">
                <!-- Incident Alert Input Panel -->
                <section className="bg-[#111827] border border-gray-800 rounded-xl p-6 shadow-xl space-y-4">
                    <div className="flex justify-between items-center">
                        <h2 className="text-base font-semibold text-gray-200 flex items-center">
                            ⚠️ Trigger Incident Investigation
                        </h2>
                        <span className="text-xs text-gray-400">Select preset or paste raw alert</span>
                    </div>

                    <!-- Preset Chips -->
                    <div className="flex flex-wrap gap-2 pt-1">
                        {PRESETS.map((p) => (
                            <button key={p.id} onClick={() => applyPreset(p.text)} className="px-3 py-1.5 text-xs rounded-lg bg-gray-800 hover:bg-indigo-900/40 border border-gray-700 hover:border-indigo-500/50 text-gray-300 transition">
                                {p.label}
                            </button>
                        ))}
                    </div>

                    <!-- Input Area -->
                    <textarea
                        rows={3}
                        value={inputAlert}
                        onChange={(e) => setInputAlert(e.target.value)}
                        placeholder="e.g. Payment service experiencing high error rate and database connection acquisition timeout under load..."
                        className="w-full bg-[#0b0f19] border border-gray-800 rounded-lg p-3 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition"
                    />

                    <div className="flex justify-end">
                        <button onClick={handleInvestigate} disabled={loading} className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm rounded-lg shadow-lg shadow-indigo-600/30 transition flex items-center">
                            {loading ? "⚡ Investigating..." : "🚀 Start AI Investigation"}
                        </button>
                    </div>
                </section>

                <!-- LangGraph Workflow Trace Bar -->
                {activeStep > 0 && (
                    <section className="bg-[#111827] border border-gray-800 rounded-xl p-4">
                        <div className="grid grid-cols-6 gap-2 text-center text-xs font-medium">
                            {["1. Understand", "2. Plan", "3. Execute Tools", "4. Observe Evidence", "5. Evaluate Confidence", "6. RCA Report"].map((stepLabel, idx) => (
                                <div key={idx} className={`py-2 rounded-lg border transition ${idx + 1 <= activeStep ? "bg-indigo-600/20 text-indigo-300 border-indigo-500/50" : "bg-gray-800 text-gray-500 border-gray-700"}`}>
                                    {stepLabel}
                                </div>
                            ))}
                        </div>
                    </section>
                )}

                <!-- Results Dashboard -->
                {resultState && (
                    <>
                        <!-- Metrics Summary Grid -->
                        <section className="grid grid-cols-1 md:grid-cols-4 gap-4">
                            <div className="bg-[#111827] border border-gray-800 p-4 rounded-xl">
                                <p className="text-xs text-gray-400 font-medium">AFFECTED SERVICE</p>
                                <p className="text-xl font-bold text-white mt-1">{(resultState.affected_service || "Unknown").toUpperCase()}</p>
                            </div>
                            <div className="bg-[#111827] border border-gray-800 p-4 rounded-xl">
                                <p className="text-xs text-gray-400 font-medium">INVESTIGATION LOOPS</p>
                                <p className="text-xl font-bold text-indigo-400 mt-1">{resultState.iteration_count} / {resultState.max_iterations}</p>
                            </div>
                            <div className="bg-[#111827] border border-gray-800 p-4 rounded-xl">
                                <p className="text-xs text-gray-400 font-medium">CONFIDENCE SCORE</p>
                                <p className="text-xl font-bold text-emerald-400 mt-1">{(resultState.confidence_score * 100).toFixed(1)}%</p>
                            </div>
                            <div className="bg-[#111827] border border-gray-800 p-4 rounded-xl">
                                <p className="text-xs text-gray-400 font-medium">STATUS</p>
                                <p className="text-xl font-bold text-amber-400 mt-1">{(resultState.status || "COMPLETED").toUpperCase()}</p>
                            </div>
                        </section>

                        <!-- Main Panels Grid -->
                        <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            <!-- Left Column: Hypotheses & Tools -->
                            <div className="space-y-6">
                                <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 space-y-4">
                                    <h3 className="font-semibold text-sm text-gray-200">💡 Evaluated Hypotheses</h3>
                                    <div className="space-y-3">
                                        {resultState.hypotheses.map((h, i) => (
                                            <div key={i} className="bg-[#0b0f19] border border-gray-800 p-3 rounded-lg space-y-2">
                                                <p className="text-sm font-semibold text-indigo-300">{h.title}</p>
                                                <p className="text-xs text-gray-400">{h.description}</p>
                                                <div className="w-full bg-gray-800 h-2 rounded-full overflow-hidden">
                                                    <div className="bg-indigo-500 h-full" style={{ width: `${(h.confidence_score || 0) * 100}%` }}></div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 space-y-4">
                                    <h3 className="font-semibold text-sm text-gray-200">🛠️ Executed Tools Timeline</h3>
                                    <div className="flex flex-wrap gap-2 text-xs">
                                        {resultState.tools_called.map((t, idx) => (
                                            <span key={idx} className="px-3 py-1 rounded-lg bg-gray-800 border border-gray-700 text-gray-300">
                                                `{t}`
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            </div>

                            <!-- Right Column: Classified Evidence -->
                            <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 space-y-4">
                                <h3 className="font-semibold text-sm text-gray-200">📊 Classified Evidence Store</h3>
                                <div className="space-y-3 max-h-[420px] overflow-y-auto pr-1">
                                    {resultState.evidence.map((ev, i) => (
                                        <div key={i} className="bg-[#0b0f19] border border-gray-800 p-3 rounded-lg space-y-1">
                                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${ev.classification === 'supports' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'}`}>
                                                [{ev.classification.toUpperCase()}]
                                            </span>
                                            <p className="text-xs text-gray-200 mt-1">{ev.summary}</p>
                                            <p className="text-[10px] text-gray-500 font-mono">Source: {ev.citation}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </section>

                        <!-- Final RCA Report -->
                        {resultState.final_report && (
                            <section className="bg-[#111827] border border-gray-800 rounded-xl p-6 space-y-4">
                                <h2 className="text-lg font-bold text-emerald-400">📋 {resultState.final_report.title}</h2>
                                <div className="bg-[#0b0f19] border border-gray-800 p-4 rounded-lg">
                                    <h4 className="text-xs font-semibold text-gray-400 uppercase mb-2">Technical Root Cause Summary</h4>
                                    <p className="text-sm text-gray-200 leading-relaxed">{resultState.final_report.root_cause_summary || resultState.final_report.root_cause}</p>
                                </div>
                                <div>
                                    <h4 class="text-xs font-semibold text-gray-400 uppercase mb-2">Recommended Actions for Human SREs</h4>
                                    <div className="space-y-2">
                                        {(resultState.final_report.recommended_actions || []).map((act, i) => (
                                            <div key={i} className="bg-indigo-900/20 border border-indigo-500/30 text-indigo-200 text-xs p-3 rounded-lg">
                                                👉 <strong>Action Item:</strong> {act}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </section>
                        )}
                    </>
                )}

                <!-- Benchmark Results Panel -->
                {benchmarkData && (
                    <section className="bg-[#111827] border border-gray-800 rounded-xl p-6 space-y-4">
                        <h3 className="text-base font-bold text-indigo-400">📊 Benchmark Results (30 Ground-Truth Incidents)</h3>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                            <div className="bg-[#0b0f19] p-3 rounded-lg border border-gray-800">
                                <p class="text-xs text-gray-400">RC ACCURACY</p>
                                <p className="text-xl font-bold text-emerald-400">{benchmarkData.root_cause_accuracy_pct}%</p>
                            </div>
                            <div className="bg-[#0b0f19] p-3 rounded-lg border border-gray-800">
                                <p className="text-xs text-gray-400">RECALL</p>
                                <p className="text-xl font-bold text-indigo-400">{benchmarkData.retrieval_recall_pct}%</p>
                            </div>
                            <div className="bg-[#0b0f19] p-3 rounded-lg border border-gray-800">
                                <p className="text-xs text-gray-400">FALSE CONFIDENCE</p>
                                <p className="text-xl font-bold text-rose-400">{benchmarkData.false_confidence_rate_pct}%</p>
                            </div>
                            <div className="bg-[#0b0f19] p-3 rounded-lg border border-gray-800">
                                <p className="text-xs text-gray-400">AVG LATENCY</p>
                                <p className="text-xl font-bold text-amber-400">{benchmarkData.avg_latency_seconds}s</p>
                            </div>
                        </div>
                    </section>
                )}
            </main>
        </div>
    );
}
