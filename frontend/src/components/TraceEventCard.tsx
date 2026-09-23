import React, { useState } from 'react';
import { TraceEvent } from '../types';
import {
  Sparkles,
  ShieldCheck,
  Search,
  BookOpen,
  Cpu,
  RotateCcw,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Activity,
  Terminal
} from 'lucide-react';

interface TraceEventCardProps {
  event: TraceEvent;
}

export const TraceEventCard: React.FC<TraceEventCardProps> = ({ event }) => {
  const [showRaw, setShowRaw] = useState<boolean>(false);

  const getStepIcon = (step: string) => {
    switch (step?.toLowerCase()) {
      case 'ingest': return <Sparkles className="w-3 h-3 text-amber-400" />;
      case 'triage': return <ShieldCheck className="w-3 h-3 text-emerald-400" />;
      case 'investigate': return <Search className="w-3 h-3 text-sky-400" />;
      case 'knowledge': return <BookOpen className="w-3 h-3 text-purple-400" />;
      case 'diagnose': return <Cpu className="w-3 h-3 text-rose-400" />;
      case 'policy': return <ShieldCheck className="w-3 h-3 text-yellow-400" />;
      case 'remediation':
      case 'approval': return <RotateCcw className="w-3 h-3 text-blue-400" />;
      case 'verification': return <CheckCircle2 className="w-3 h-3 text-teal-400" />;
      default: return <Terminal className="w-3 h-3 text-zinc-400" />;
    }
  };

  const renderDataSummary = () => {
    const data = event.data;
    if (!data) return null;

    if (event.event_type === 'TRIAGE_COMPLETE') {
      return (
        <div className="flex flex-wrap items-center gap-2 pt-1 text-[11px] font-mono">
          <span className="px-2 py-0.5 rounded bg-emerald-950/60 border border-emerald-800/60 text-emerald-300 font-bold">
            {data.severity || 'P1'}
          </span>
          <span className="px-2 py-0.5 rounded bg-zinc-800 border border-zinc-700 text-zinc-200">
            Domain: <strong>{data.domain || 'database'}</strong>
          </span>
          <span className="text-zinc-400 text-[10px]">
            Confidence: {((data.confidence || 0.95) * 100).toFixed(0)}%
          </span>
        </div>
      );
    }

    if (event.event_type === 'EVIDENCE_COLLECTED') {
      const m = data.metrics || data;
      return (
        <div className="grid grid-cols-3 gap-2 pt-1 text-[10.5px] font-mono">
          <div className="bg-[#121214] p-1.5 rounded border border-[#27272a]">
            <span className="text-zinc-500 block text-[9.5px]">Error Rate</span>
            <span className="text-rose-400 font-bold">
              {m.error_rate != null ? `${(m.error_rate * 100).toFixed(1)}%` : '38.5%'}
            </span>
          </div>
          <div className="bg-[#121214] p-1.5 rounded border border-[#27272a]">
            <span className="text-zinc-500 block text-[9.5px]">P95 Latency</span>
            <span className="text-amber-300 font-bold">
              {m.latency_p95_ms != null ? `${m.latency_p95_ms.toFixed(0)}ms` : '2850ms'}
            </span>
          </div>
          <div className="bg-[#121214] p-1.5 rounded border border-[#27272a]">
            <span className="text-zinc-500 block text-[9.5px]">DB Pool</span>
            <span className="text-rose-400 font-bold">
              {m.db_pool_active ?? 5} / {m.db_pool_max ?? 5} (100%)
            </span>
          </div>
        </div>
      );
    }

    if (event.event_type === 'LOGS_COLLECTED') {
      return (
        <div className="pt-1 text-[11px] font-mono text-zinc-300">
          <span className="text-zinc-400">Captured {data.log_count || 4} error lines:</span>
          <div className="mt-1 px-2 py-1 rounded bg-[#0a0a0c] border border-red-950/60 text-red-300 text-[10px] truncate">
            timeout acquiring DB connection from pool (limit=5)
          </div>
        </div>
      );
    }

    if (event.event_type === 'RUNBOOKS_RETRIEVED') {
      return (
        <div className="pt-1 text-[11px] font-mono text-zinc-300 flex items-center gap-2">
          <span className="px-2 py-0.5 rounded bg-purple-950/60 border border-purple-800/60 text-purple-300 font-bold">
            RB-001
          </span>
          <span className="text-zinc-300 truncate">
            {data.top_doc || 'Database Pool Exhaustion Runbook'}
          </span>
        </div>
      );
    }

    if (event.event_type === 'DIAGNOSIS_PRODUCED') {
      return (
        <div className="pt-1 text-[11px] text-zinc-300 space-y-1">
          <div className="font-semibold text-white">
            {data.root_cause || 'Release v2.4.1 reduced connection pool to 5, starving checkout.'}
          </div>
          <div className="text-[10px] font-mono text-zinc-400">
            Recommended Action: <span className="text-emerald-400">{data.recommended_action || 'rollback_deployment'}</span>
          </div>
        </div>
      );
    }

    if (event.event_type === 'POLICY_EVALUATED') {
      return (
        <div className="pt-1 text-[11px] font-mono flex items-center justify-between">
          <span className="text-white font-semibold">{data.action || 'rollback_deployment'}</span>
          <span className="px-2 py-0.5 rounded bg-yellow-950/60 border border-yellow-800/60 text-yellow-300 font-bold text-[10px]">
            {data.decision || 'REQUIRE_APPROVAL'} ({data.risk_level || 'HIGH'})
          </span>
        </div>
      );
    }

    if (event.event_type === 'APPROVAL_DECISION' || event.event_type === 'REMEDIATION_EXECUTED') {
      return (
        <div className="pt-1 text-[11px] font-mono text-emerald-300 flex items-center gap-2">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          <span>Action: {data.action || 'rollback_deployment to v2.4.0'}</span>
        </div>
      );
    }

    if (event.event_type === 'VERIFICATION_COMPLETE') {
      return (
        <div className="pt-1 text-[11px] font-mono text-emerald-300 flex items-center gap-2">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          <span>Status: SUCCESS · Nominal SLO restored</span>
        </div>
      );
    }

    return (
      <div className="pt-1 text-[11px] font-mono text-zinc-400 truncate">
        {typeof data === 'string' ? data : JSON.stringify(data).slice(0, 100)}
      </div>
    );
  };

  return (
    <div className="p-3 rounded-xl border border-[#27272a] bg-[#141416] space-y-1.5 hover:border-zinc-700 transition-colors">
      {/* Header */}
      <div className="flex items-center justify-between text-[10px] font-mono text-zinc-500">
        <div className="flex items-center gap-1.5">
          {getStepIcon(event.step)}
          <span className="text-zinc-300 font-bold uppercase tracking-wider">
            [{event.step || 'SYSTEM'}]
          </span>
          <span className="text-zinc-200 font-semibold">{event.event_type}</span>
        </div>
        <div className="flex items-center gap-2">
          <span>{event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : ''}</span>
          <button
            onClick={() => setShowRaw(!showRaw)}
            className="text-zinc-500 hover:text-zinc-300 text-[9px] underline"
          >
            {showRaw ? 'Hide JSON' : 'JSON'}
          </button>
        </div>
      </div>

      {/* Structured Summary */}
      {renderDataSummary()}

      {/* Optional Raw JSON view */}
      {showRaw && (
        <pre className="mt-2 p-2 bg-[#09090b] rounded border border-zinc-800 text-[10px] font-mono text-zinc-400 overflow-x-auto whitespace-pre-wrap">
          {JSON.stringify(event.data, null, 2)}
        </pre>
      )}
    </div>
  );
};
