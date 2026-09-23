import React, { useState } from 'react';
import { 
  AlertCircle, 
  Activity, 
  Cpu, 
  Play, 
  RotateCcw, 
  ChevronRight, 
  ChevronLeft,
  Search,
  CheckCircle2,
  Bot,
  Send,
  Sparkles,
  Server,
  Layers,
  Flame
} from 'lucide-react';
import { IncidentState } from '../types';

interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
  state: IncidentState | null;
  onInjectChaos: () => void;
  onResetChaos: () => void;
  isLoadingChaos: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isOpen,
  onToggle,
  state,
  onInjectChaos,
  onResetChaos,
  isLoadingChaos
}) => {
  const [activeTab, setActiveTab] = useState<'alerts' | 'workflows' | 'diagnosis'>('alerts');
  const [diagnosisQuery, setDiagnosisQuery] = useState('');
  const [aiChat, setAiChat] = useState<{ role: 'user' | 'ai'; text: string; time: string }[]>([
    {
      role: 'ai',
      text: 'Aegis Ops AI standing by. Ask me about system topology, connection pool limits, runbook RB-001, or diagnosis rationale.',
      time: '17:14'
    }
  ]);

  const handleSendDiagnosisQuery = (queryText?: string) => {
    const text = queryText || diagnosisQuery;
    if (!text.trim()) return;

    const userMsg = { role: 'user' as const, text: text.trim(), time: 'Just now' };
    setAiChat((prev) => [...prev, userMsg]);
    if (!queryText) setDiagnosisQuery('');

    // Generate smart context-aware SRE diagnosis reply
    setTimeout(() => {
      const q = text.toLowerCase();
      let reply = '';
      if (q.includes('bottleneck') || q.includes('cause') || q.includes('pool')) {
        reply = 'The bottleneck is caused by release v2.4.1 setting DB_CONNECTION_POOL=5 on checkout-service. Under 100 RPS traffic, connection acquisition times out after 2000ms, triggering HTTP 500 bursts (38.5% error rate). Baseline v2.4.0 allocated 50 connections with nominal 0.02% error rate.';
      } else if (q.includes('runbook') || q.includes('rb-001')) {
        reply = 'Runbook RB-001: "Postgres Connection Pool Starvation". Prescribes immediate rollback to previous release tag (v2.4.0) if error rate exceeds 5% and connection pool utilization remains at 100% for > 60 seconds.';
      } else if (q.includes('metric') || q.includes('latency') || q.includes('stats')) {
        reply = 'Current Telemetry:\n• P95 Latency: 2,850ms (Normal: 42ms)\n• Error Rate: 38.5% (Threshold: 5.0%)\n• DB Pool: 5/5 connections saturated (100%)\n• Traffic: 100 RPS steady load';
      } else if (q.includes('policy') || q.includes('approval')) {
        reply = 'Policy Guardrail PROD_ROLLBACK_APPROVAL mandates human operator authorization before executing container recreate operations in production. Risk level is classified as HIGH_RISK.';
      } else {
        reply = `Service '${state?.service || 'checkout-service'}' is currently in state '${state?.status || 'OPEN'}'. The autonomous resolution DAG has identified root cause in release v2.4.1 and generated a rollback remediation plan.`;
      }

      setAiChat((prev) => [...prev, { role: 'ai', text: reply, time: 'Just now' }]);
    }, 450);
  };

  return (
    <aside
      className={`h-screen bg-[#050507] border-r border-zinc-800/80 flex flex-col justify-between shrink-0 transition-all duration-300 ease-in-out relative z-30 select-none ${
        isOpen ? 'w-80' : 'w-14'
      }`}
    >
      {/* 1. Header with Brand & Slide Toggle */}
      <div className="h-14 px-3.5 border-b border-zinc-800/80 flex items-center justify-between shrink-0">
        {isOpen ? (
          <>
            <div className="flex items-center gap-2">
              <div className="w-5 h-5 rounded-md bg-white text-black flex items-center justify-center font-bold text-xs">
                A
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-semibold tracking-wider text-white">AEGIS</span>
                <span className="text-[9px] bg-zinc-800 text-zinc-300 px-1 rounded font-mono">OPS</span>
              </div>
            </div>
            <button
              onClick={onToggle}
              title="Slide in panel"
              className="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800/60 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
          </>
        ) : (
          <button
            onClick={onToggle}
            title="Expand panel"
            className="w-full flex items-center justify-center p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800/60 transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* 2. Collapsed View Icon Rail */}
      {!isOpen && (
        <div className="flex-1 flex flex-col items-center py-4 gap-3">
          <button
            onClick={() => { onToggle(); setActiveTab('alerts'); }}
            title="Alerts & Incidents"
            className={`p-2.5 rounded-xl transition-all ${
              activeTab === 'alerts' ? 'bg-white text-black' : 'text-zinc-400 hover:text-white hover:bg-zinc-900'
            }`}
          >
            <AlertCircle className="w-4 h-4" />
          </button>

          <button
            onClick={() => { onToggle(); setActiveTab('workflows'); }}
            title="Workflows & Chaos"
            className={`p-2.5 rounded-xl transition-all ${
              activeTab === 'workflows' ? 'bg-white text-black' : 'text-zinc-400 hover:text-white hover:bg-zinc-900'
            }`}
          >
            <Activity className="w-4 h-4" />
          </button>

          <button
            onClick={() => { onToggle(); setActiveTab('diagnosis'); }}
            title="Diagnosis AI (Ask Ops)"
            className={`p-2.5 rounded-xl transition-all ${
              activeTab === 'diagnosis' ? 'bg-white text-black' : 'text-zinc-400 hover:text-white hover:bg-zinc-900'
            }`}
          >
            <Bot className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* 3. Expanded Panel Content */}
      {isOpen && (
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Tabs Navigation (Alerts, Workflows, Diagnosis) */}
          <div className="p-3 border-b border-zinc-900">
            <div className="grid grid-cols-3 gap-1 bg-[#0c0c0e] p-1 rounded-xl border border-zinc-800/60 text-[11px] font-medium">
              <button
                onClick={() => setActiveTab('alerts')}
                className={`py-1.5 rounded-lg flex items-center justify-center gap-1 transition-all ${
                  activeTab === 'alerts'
                    ? 'bg-zinc-800 text-white font-semibold shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                <AlertCircle className="w-3.5 h-3.5" />
                <span>Alerts</span>
              </button>

              <button
                onClick={() => setActiveTab('workflows')}
                className={`py-1.5 rounded-lg flex items-center justify-center gap-1 transition-all ${
                  activeTab === 'workflows'
                    ? 'bg-zinc-800 text-white font-semibold shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                <Activity className="w-3.5 h-3.5" />
                <span>Workflows</span>
              </button>

              <button
                onClick={() => setActiveTab('diagnosis')}
                className={`py-1.5 rounded-lg flex items-center justify-center gap-1 transition-all ${
                  activeTab === 'diagnosis'
                    ? 'bg-zinc-800 text-white font-semibold shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                <Bot className="w-3.5 h-3.5" />
                <span>Ops AI</span>
              </button>
            </div>
          </div>

          {/* Tab 1: Alerts & Incidents */}
          {activeTab === 'alerts' && (
            <div className="flex-1 overflow-y-auto p-3 space-y-3">
              <div className="flex items-center justify-between text-[11px] text-zinc-400 font-mono px-1">
                <span>ACTIVE INCIDENTS</span>
                <span className="bg-white text-black px-1.5 py-0.2 rounded font-bold text-[10px]">1 CRITICAL</span>
              </div>

              {/* Primary Active Incident Card */}
              <div className="bg-[#09090b] border border-zinc-800 rounded-2xl p-3.5 space-y-2.5 hover:border-zinc-700 transition-all">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs font-mono font-bold text-white">INC-001</span>
                    <span className="text-[10px] bg-white text-black font-mono font-bold px-1.5 py-0.2 rounded">
                      P1
                    </span>
                  </div>
                  <span className="text-[10px] text-zinc-500 font-mono">17:14:03 UTC</span>
                </div>

                <div>
                  <h5 className="text-xs font-semibold text-zinc-100">
                    {state?.title || 'High 5xx Error Rate on Checkout'}
                  </h5>
                  <p className="text-[11px] text-zinc-400 mt-0.5 leading-relaxed">
                    Connection pool exhaustion on <code className="text-zinc-200">{state?.service || 'checkout-service'}</code> after release v2.4.1.
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-2 pt-1">
                  <div className="bg-[#050507] border border-zinc-800/80 rounded-xl p-2">
                    <span className="text-[9px] text-zinc-500 font-mono">5xx ERROR RATE</span>
                    <p className="text-xs font-mono font-bold text-white mt-0.5">38.5%</p>
                  </div>
                  <div className="bg-[#050507] border border-zinc-800/80 rounded-xl p-2">
                    <span className="text-[9px] text-zinc-500 font-mono">P95 LATENCY</span>
                    <p className="text-xs font-mono font-bold text-white mt-0.5">2,850ms</p>
                  </div>
                </div>

                <div className="flex items-center justify-between text-[10px] text-zinc-500 font-mono pt-1 border-t border-zinc-900">
                  <span>Target: checkout-service</span>
                  <span className="text-white">Autopilot Active</span>
                </div>
              </div>

              {/* Historical Alert Item */}
              <div className="bg-[#09090b]/50 border border-zinc-900 rounded-xl p-3 space-y-1 opacity-70">
                <div className="flex items-center justify-between text-[11px] font-mono">
                  <span className="text-zinc-400">ALERT-098</span>
                  <span className="text-zinc-500 text-[10px]">Resolved</span>
                </div>
                <p className="text-xs text-zinc-300">Payment Gateway Latency Spike</p>
                <span className="text-[10px] text-zinc-500 font-mono">Auto-healed via circuit breaker</span>
              </div>
            </div>
          )}

          {/* Tab 2: Workflows & AcmeCloud Controls */}
          {activeTab === 'workflows' && (
            <div className="flex-1 overflow-y-auto p-3 space-y-4">
              {/* Active Workflow Summary */}
              <div className="space-y-2">
                <div className="text-[11px] text-zinc-400 font-mono px-1">ACTIVE WORKFLOW</div>
                <div className="bg-[#09090b] border border-zinc-800 rounded-2xl p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-white">ITOPS-001 // Auto-Heal</span>
                    <span className="text-[10px] border border-zinc-700 text-zinc-300 font-mono px-1.5 py-0.5 rounded">
                      6 NODES
                    </span>
                  </div>
                  <p className="text-[11px] text-zinc-400 leading-relaxed">
                    Closed-loop autonomous remediation: Ingest → Triage → Probe → CoT → Policy → Rollback.
                  </p>
                </div>
              </div>

              {/* AcmeCloud Chaos Controls */}
              <div className="space-y-2">
                <div className="text-[11px] text-zinc-400 font-mono px-1">ACMECLOUD CONTROLS</div>
                
                <button
                  onClick={onInjectChaos}
                  disabled={isLoadingChaos}
                  className="w-full bg-[#0c0c0e] hover:bg-zinc-900 text-white border border-zinc-800 hover:border-zinc-700 text-xs py-2 px-3 rounded-xl flex items-center justify-between font-medium transition-all shadow-sm disabled:opacity-50"
                >
                  <div className="flex items-center gap-2">
                    <Play className="w-3.5 h-3.5" />
                    <span>Inject Bad Release (v2.4.1)</span>
                  </div>
                  <span className="text-[10px] text-zinc-400 font-mono">100 RPS</span>
                </button>

                <button
                  onClick={onResetChaos}
                  disabled={isLoadingChaos}
                  className="w-full bg-[#09090b] hover:bg-zinc-900 text-zinc-400 hover:text-white border border-zinc-800 text-xs py-2 px-3 rounded-xl flex items-center gap-2 font-medium transition-all disabled:opacity-50"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Reset Nominal Baseline (v2.4.0)</span>
                </button>
              </div>

              {/* Target Services Topology */}
              <div className="space-y-2">
                <div className="text-[11px] text-zinc-400 font-mono px-1">MONITORED SERVICES</div>
                <div className="space-y-1.5">
                  <div className="bg-[#09090b] border border-zinc-800/80 rounded-xl p-2.5 flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <Server className="w-3.5 h-3.5 text-zinc-400" />
                      <span className="text-zinc-200">checkout-service</span>
                    </div>
                    <span className="text-[10px] font-mono text-zinc-400">Port 8080</span>
                  </div>
                  <div className="bg-[#09090b] border border-zinc-800/80 rounded-xl p-2.5 flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <Server className="w-3.5 h-3.5 text-zinc-400" />
                      <span className="text-zinc-200">postgres</span>
                    </div>
                    <span className="text-[10px] font-mono text-zinc-400">Port 5432</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Tab 3: Diagnosis AI (Ask Ops) */}
          {activeTab === 'diagnosis' && (
            <div className="flex-1 flex flex-col overflow-hidden">
              {/* Messages scroll area */}
              <div className="flex-1 overflow-y-auto p-3 space-y-2.5 text-xs">
                {aiChat.map((msg, idx) => (
                  <div
                    key={idx}
                    className={`p-3 rounded-2xl leading-relaxed ${
                      msg.role === 'user'
                        ? 'bg-zinc-800 text-white ml-6 border border-zinc-700'
                        : 'bg-[#09090b] text-zinc-300 mr-4 border border-zinc-800/80'
                    }`}
                  >
                    <div className="flex items-center justify-between text-[10px] text-zinc-500 font-mono mb-1">
                      <span>{msg.role === 'user' ? 'Operator' : 'Aegis Ops AI'}</span>
                      <span>{msg.time}</span>
                    </div>
                    <div className="whitespace-pre-line text-[11px]">{msg.text}</div>
                  </div>
                ))}
              </div>

              {/* Quick suggestion chips */}
              <div className="px-3 py-1.5 flex items-center gap-1.5 overflow-x-auto border-t border-zinc-900">
                <button
                  onClick={() => handleSendDiagnosisQuery('Explain current bottleneck')}
                  className="shrink-0 text-[10px] bg-zinc-900 hover:bg-zinc-800 text-zinc-300 border border-zinc-800 px-2 py-0.5 rounded-full transition-colors"
                >
                  Bottleneck?
                </button>
                <button
                  onClick={() => handleSendDiagnosisQuery('What does Runbook RB-001 say?')}
                  className="shrink-0 text-[10px] bg-zinc-900 hover:bg-zinc-800 text-zinc-300 border border-zinc-800 px-2 py-0.5 rounded-full transition-colors"
                >
                  Runbook RB-001
                </button>
                <button
                  onClick={() => handleSendDiagnosisQuery('Show current telemetry metrics')}
                  className="shrink-0 text-[10px] bg-zinc-900 hover:bg-zinc-800 text-zinc-300 border border-zinc-800 px-2 py-0.5 rounded-full transition-colors"
                >
                  Metrics
                </button>
              </div>

              {/* Input box */}
              <div className="p-3 border-t border-zinc-800/80 bg-[#050507]">
                <div className="bg-[#09090b] border border-zinc-800 rounded-xl p-1 flex items-center gap-1.5">
                  <input
                    type="text"
                    value={diagnosisQuery}
                    onChange={(e) => setDiagnosisQuery(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') handleSendDiagnosisQuery(); }}
                    placeholder="Ask about ops, runbooks, metrics..."
                    className="flex-1 bg-transparent text-xs text-white placeholder:text-zinc-500 px-2.5 focus:outline-none"
                  />
                  <button
                    onClick={() => handleSendDiagnosisQuery()}
                    className="w-7 h-7 rounded-lg bg-white text-black hover:bg-zinc-200 flex items-center justify-center transition-colors shrink-0"
                  >
                    <Send className="w-3 h-3" />
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 4. Footer System Status */}
      <div className="p-2.5 border-t border-zinc-800/80">
        <div className={`flex items-center ${isOpen ? 'justify-between px-1' : 'justify-center'}`}>
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-white"></span>
            </span>
            {isOpen && <span className="text-xs font-medium text-white">Aegis Online</span>}
          </div>
          {isOpen && (
            <span className="text-[10px] font-mono text-zinc-500">SLO 99.99%</span>
          )}
        </div>
      </div>
    </aside>
  );
};
