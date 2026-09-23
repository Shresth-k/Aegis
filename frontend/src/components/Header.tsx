import React from 'react';
import { 
  ShieldAlert, 
  ShieldCheck, 
  Flame, 
  Play, 
  RotateCcw, 
  Activity, 
  Cpu, 
  Radio, 
  ChevronDown 
} from 'lucide-react';
import { IncidentState } from '../types';

interface HeaderProps {
  incidents: any[];
  selectedIncidentId: string;
  onSelectIncident: (id: string) => void;
  currentState: IncidentState | null;
  onRunIncident: () => void;
  onInjectChaos: () => void;
  onResetChaos: () => void;
  isRunning: boolean;
  isStreamLive: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  incidents,
  selectedIncidentId,
  onSelectIncident,
  currentState,
  onRunIncident,
  onInjectChaos,
  onResetChaos,
  isRunning,
  isStreamLive
}) => {
  const status = currentState?.status || 'OPEN';

  const getStatusBadge = () => {
    switch (status) {
      case 'RESOLVED':
        return (
          <div className="flex items-center gap-2 px-2.5 py-1 rounded bg-emerald-950/60 border border-emerald-500/30 text-emerald-400 font-mono text-xs glow-emerald">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>RESOLVED // NOMINAL</span>
          </div>
        );
      case 'PENDING_APPROVAL':
        return (
          <div className="flex items-center gap-2 px-2.5 py-1 rounded bg-amber-950/60 border border-amber-500/40 text-amber-300 font-mono text-xs glow-amber">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping"></span>
            <span>GATE // HITL APPROVAL REQUIRED</span>
          </div>
        );
      case 'INVESTIGATING':
      case 'REMEDIATING':
      case 'VERIFYING':
        return (
          <div className="flex items-center gap-2 px-2.5 py-1 rounded bg-cyan-950/60 border border-cyan-500/40 text-cyan-300 font-mono text-xs glow-cyan">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
            <span>{status} // AUTONOMOUS AGENT ACTIVE</span>
          </div>
        );
      case 'ESCALATED':
        return (
          <div className="flex items-center gap-2 px-2.5 py-1 rounded bg-red-950/60 border border-red-500/40 text-red-400 font-mono text-xs glow-red">
            <span className="w-2 h-2 rounded-full bg-red-400"></span>
            <span>ESCALATED TO HUMAN ON-CALL</span>
          </div>
        );
      default:
        return (
          <div className="flex items-center gap-2 px-2.5 py-1 rounded bg-red-950/40 border border-red-500/30 text-red-400 font-mono text-xs">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
            <span>OUTAGE DETECTED // SEV-1</span>
          </div>
        );
    }
  };

  const incidentOptions = incidents.length > 0 ? incidents : [
    { incident_id: 'INC-001', service: 'checkout-service', severity: 'P1' },
    { incident_id: 'ITOPS-001', service: 'checkout-service', severity: 'P1' }
  ];

  return (
    <header className="h-14 border-b border-[#1e1e28] bg-[#07070a]/90 backdrop-blur-md px-4 flex items-center justify-between z-30 shrink-0 select-none">
      {/* Brand & Incident Selector */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded bg-gradient-to-br from-emerald-500/20 to-zinc-900 border border-emerald-500/40 flex items-center justify-center text-emerald-400 shadow-sm">
            <ShieldAlert className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold tracking-wider text-sm text-zinc-100 font-mono">AEGIS</span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-800/80 text-zinc-400 border border-zinc-700/50">
                v0.1.0
              </span>
            </div>
            <div className="text-[10px] font-mono text-zinc-500 tracking-tight">
              Autonomous IT Operations & Incident Resolution
            </div>
          </div>
        </div>

        <div className="h-6 w-px bg-zinc-800" />

        {/* Incident Dropdown */}
        <div className="relative flex items-center">
          <div className="flex items-center gap-2 bg-[#0d0d14] border border-[#272738] hover:border-zinc-600 rounded px-2.5 py-1 text-xs font-mono transition-colors">
            <span className="text-zinc-500">INCIDENT:</span>
            <select
              value={selectedIncidentId}
              onChange={(e) => onSelectIncident(e.target.value)}
              className="bg-transparent text-emerald-400 font-bold focus:outline-none cursor-pointer pr-1"
            >
              {incidentOptions.map((inc) => (
                <option key={inc.incident_id} value={inc.incident_id} className="bg-[#0f0f18] text-zinc-200">
                  {inc.incident_id} - {inc.service} ({inc.severity})
                </option>
              ))}
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-zinc-500" />
          </div>
        </div>

        {/* Status Badge */}
        {getStatusBadge()}
      </div>

      {/* Telemetry Counters HUD */}
      <div className="hidden lg:flex items-center gap-6 font-mono text-xs">
        <div className="flex items-center gap-2">
          <Cpu className="w-3.5 h-3.5 text-zinc-500" />
          <span className="text-zinc-500">Triage:</span>
          <span className="text-emerald-400 font-bold">21.4ms</span>
        </div>
        <div className="flex items-center gap-2">
          <Activity className="w-3.5 h-3.5 text-zinc-500" />
          <span className="text-zinc-500">CoT Engine:</span>
          <span className="text-zinc-200 font-semibold">AI Reasoning Engine</span>
        </div>
        <div className="flex items-center gap-2">
          <Radio className={`w-3.5 h-3.5 ${isStreamLive ? 'text-emerald-400 animate-pulse' : 'text-zinc-600'}`} />
          <span className="text-zinc-500">Telemetry Stream:</span>
          <span className={isStreamLive ? 'text-emerald-400 font-semibold' : 'text-zinc-500'}>
            {isStreamLive ? 'ACTIVE' : 'IDLE'}
          </span>
        </div>
      </div>

      {/* Chaos Actions & Controls */}
      <div className="flex items-center gap-2">
        <button
          onClick={onInjectChaos}
          title="Simulate bad deployment v2.4.1 (DB pool starvation)"
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded bg-red-950/30 hover:bg-red-900/50 border border-red-500/40 text-red-300 hover:text-red-200 font-mono text-xs transition-all active:scale-[0.98]"
        >
          <Flame className="w-3.5 h-3.5 text-red-400" />
          <span>Inject Chaos v2.4.1</span>
        </button>

        <button
          onClick={onRunIncident}
          disabled={isRunning}
          title="Trigger Aegis Closed-Loop Resolution Graph"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/50 text-emerald-300 hover:text-emerald-200 font-mono text-xs transition-all active:scale-[0.98] glow-emerald disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Play className={`w-3.5 h-3.5 text-emerald-400 ${isRunning ? 'animate-spin' : ''}`} />
          <span>{isRunning ? 'Investigating...' : 'Run Aegis Auto-Heal'}</span>
        </button>

        <button
          onClick={onResetChaos}
          title="Reset AcmeCloud to healthy baseline v2.4.0"
          className="flex items-center gap-1.5 p-1.5 rounded bg-[#13131c] hover:bg-[#1c1c28] border border-zinc-700/60 text-zinc-400 hover:text-zinc-200 font-mono text-xs transition-colors"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>
      </div>
    </header>
  );
};
