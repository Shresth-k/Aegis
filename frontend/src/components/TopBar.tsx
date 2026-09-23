import React from 'react';
import { Share2, Search, AlertCircle, Check, Flame, RotateCcw } from 'lucide-react';
import { IncidentState } from '../types';

interface TopBarProps {
  state: IncidentState | null;
  isRunning?: boolean;
  onShare?: () => void;
  userInitials?: string;
  incidents?: Array<{ incident_id: string; title: string; service: string; severity: string; status: string }>;
  currentIncidentId?: string;
  onSelectIncident?: (incidentId: string) => void;
  onInjectChaos?: () => void;
  onResetChaos?: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({
  state,
  isRunning = false,
  onShare,
  userInitials = 'SK',
  incidents = [],
  currentIncidentId = 'INC-001',
  onSelectIncident,
  onInjectChaos,
  onResetChaos
}) => {
  const status = state?.status || 'OPEN';
  const workflowBusy = isRunning || ['INVESTIGATING', 'PENDING_APPROVAL', 'REMEDIATING', 'VERIFYING'].includes(status);

  const getStatusBadge = () => {
    switch (status) {
      case 'PENDING_APPROVAL':
        return (
          <div className="bg-[#1e1e1e] text-[#ffffff] border border-[#3c3c3c] text-[11px] px-2.5 py-0.5 rounded-full font-medium flex items-center gap-1.5 shadow-sm">
            <span className="w-1.5 h-1.5 rounded-full bg-[#ffffff] animate-ping"></span>
            <span>Approval Required</span>
          </div>
        );
      case 'RESOLVED':
        return (
          <div className="bg-[#1e1e1e] text-[#ffffff] border border-[#3c3c3c] text-[11px] px-2.5 py-0.5 rounded-full font-medium flex items-center gap-1.5 shadow-sm">
            <Check className="w-3 h-3 text-[#ffffff]" />
            <span>Resolved</span>
          </div>
        );
      case 'INVESTIGATING':
      case 'REMEDIATING':
      case 'VERIFYING':
        return (
          <div className="bg-[#1e1e1e] text-[#ffffff] border border-[#4d4d4d] text-[11px] px-2.5 py-0.5 rounded-full font-medium flex items-center gap-1.5 shadow-sm">
            <span className="w-1.5 h-1.5 rounded-full bg-[#ffffff] animate-ping"></span>
            <span>{status}</span>
          </div>
        );
      default:
        return (
          <div className="bg-[#ffffff] text-[#000000] text-[11px] px-2.5 py-0.5 rounded-full font-semibold flex items-center gap-1.5 shadow-sm">
            <AlertCircle className="w-3 h-3" />
            <span>Open ({state?.severity || 'P1'})</span>
          </div>
        );
    }
  };

  return (
    <header className="h-14 bg-[#111111] border-b border-[#3c3c3c] flex items-center justify-between px-4 sm:px-6 shrink-0 select-none">
      {/* Breadcrumbs & Status */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 text-xs">
          <span className="text-[#a1a1aa] hover:text-[#ffffff] transition-colors cursor-default">
            Workflows
          </span>
          <span className="text-[#3c3c3c]">/</span>
          {incidents && incidents.length > 0 ? (
            <div className="relative">
              <select
                value={currentIncidentId}
                onChange={(e) => onSelectIncident?.(e.target.value)}
                className="bg-[#18181b] hover:bg-[#222226] border border-[#3c3c3c] text-[#ffffff] font-mono text-xs px-2 py-0.5 rounded cursor-pointer focus:outline-none focus:border-white/50 transition-colors"
              >
                {incidents.map((inc) => (
                  <option key={inc.incident_id} value={inc.incident_id} className="bg-[#18181b] text-white">
                    {inc.incident_id} ({inc.service})
                  </option>
                ))}
              </select>
            </div>
          ) : (
            <span className="text-[#a1a1aa] font-mono">
              {currentIncidentId || state?.incident_id || 'ITOPS-001'}
            </span>
          )}
          <span className="text-[#3c3c3c]">/</span>
          <span className="text-[#ffffff] font-medium">
            {state?.service || 'checkout-service'}
          </span>
        </div>

        {/* Live Status Pill */}
        {getStatusBadge()}
      </div>

      {/* Right Action Tools & Controls */}
      <div className="flex items-center gap-2 shrink-0">
        {/* Chaos Injection and Reset Buttons */}
        <button
          onClick={onInjectChaos}
          disabled={workflowBusy}
          className="bg-[#1e1e24] hover:bg-red-950/60 text-red-300 hover:text-red-200 border border-red-900/40 hover:border-red-700/60 text-xs px-2.5 py-1.5 rounded-lg font-mono flex items-center gap-1.5 transition-all shadow-sm active:scale-[0.98]"
          title="Inject Fault v2.4.1 (DB Connection Pool Starvation)"
        >
          <Flame className="w-3.5 h-3.5 text-red-400" />
          <span className="hidden md:inline">Inject Chaos (v2.4.1)</span>
        </button>

        <button
          onClick={onResetChaos}
          disabled={workflowBusy}
          className="bg-[#1e1e24] hover:bg-emerald-950/60 text-emerald-300 hover:text-emerald-200 border border-emerald-900/40 hover:border-emerald-700/60 text-xs px-2.5 py-1.5 rounded-lg font-mono flex items-center gap-1.5 transition-all shadow-sm active:scale-[0.98]"
          title="Reset Service to Healthy Baseline v2.4.0"
        >
          <RotateCcw className="w-3.5 h-3.5 text-emerald-400" />
          <span className="hidden md:inline">Reset Baseline (v2.4.0)</span>
        </button>

        {/* Search Bar */}
        <div className="relative hidden 2xl:flex items-center">
          <Search className="w-3.5 h-3.5 text-[#71717a] absolute left-3 pointer-events-none" />
          <input
            type="text"
            placeholder="Search..."
            className="bg-[#1e1e1e] border border-[#3c3c3c] text-[#ffffff] text-xs pl-8 pr-8 py-1.5 rounded-lg focus:outline-none focus:border-[#4d4d4d] w-36 placeholder:text-[#71717a] transition-all"
          />
        </div>

        {/* Share Button */}
        <button
          onClick={onShare}
          className="bg-[#1e1e1e] hover:bg-[#2a2a2a] text-[#ffffff] text-xs px-2.5 py-1.5 rounded-lg border border-[#3c3c3c] flex items-center gap-1.5 transition-all shrink-0 active:scale-[0.98]"
        >
          <Share2 className="w-3.5 h-3.5 text-[#a1a1aa]" />
          <span className="hidden md:inline">Share</span>
        </button>

        {/* User Avatar */}
        <div className="w-7 h-7 rounded-full bg-[#1e1e1e] border border-[#3c3c3c] flex items-center justify-center text-[11px] font-semibold text-[#ffffff] ml-0.5 shrink-0">
          {userInitials}
        </div>
      </div>
    </header>
  );
};
