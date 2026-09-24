import React from 'react';
import { Share2, Search, AlertCircle, Check, Server, Bot, ShoppingBag, ExternalLink } from 'lucide-react';
import { IncidentState } from '../types';

interface TopBarProps {
  state: IncidentState | null;
  isRunning?: boolean;
  onShare?: () => void;
  userInitials?: string;
  incidents?: Array<{ incident_id: string; title: string; service: string; severity: string; status: string }>;
  currentIncidentId?: string;
  onSelectIncident?: (incidentId: string) => void;
  activeView?: 'aegis' | 'acmecloud' | 'store';
  onToggleView?: (view: 'aegis' | 'acmecloud' | 'store') => void;
  acmecloudVersion?: string;
  acmecloudHealthy?: boolean;
}

export const TopBar: React.FC<TopBarProps> = ({
  state,
  isRunning = false,
  onShare,
  userInitials = 'SK',
  incidents = [],
  currentIncidentId = 'INC-001',
  onSelectIncident,
  activeView = 'aegis',
  onToggleView,
  acmecloudVersion = '2.4.0',
  acmecloudHealthy = true
}) => {
  const status = state?.status || 'OPEN';

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

      {/* Center View Switcher */}
      <div className="flex items-center bg-[#18181b] border border-[#2e2e34] rounded-lg p-0.5">
        <button
          onClick={() => onToggleView?.('aegis')}
          className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-mono transition-all cursor-pointer ${
            activeView === 'aegis'
              ? 'bg-[#27272a] text-white font-medium shadow-sm'
              : 'text-zinc-400 hover:text-zinc-200'
          }`}
        >
          <Bot className="w-3.5 h-3.5 text-zinc-300" />
          <span>Aegis SRE Copilot</span>
        </button>

        <button
          onClick={() => onToggleView?.('store')}
          className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-mono transition-all cursor-pointer ${
            activeView === 'store'
              ? 'bg-[#27272a] text-white font-medium shadow-sm'
              : 'text-zinc-400 hover:text-zinc-200'
          }`}
          title="Open Acme Hardware Store (Port 3002)"
        >
          <ShoppingBag className="w-3.5 h-3.5 text-zinc-300" />
          <span>Acme Store (Port 3002)</span>
        </button>

        <button
          onClick={() => onToggleView?.('acmecloud')}
          className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-mono transition-all cursor-pointer ${
            activeView === 'acmecloud'
              ? 'bg-[#27272a] text-white font-medium shadow-sm'
              : 'text-zinc-400 hover:text-zinc-200'
          }`}
          title="Open AcmeCloud Engineering Console"
        >
          <Server className="w-3.5 h-3.5 text-zinc-300" />
          <span>DevOps Console</span>
        </button>
      </div>

      {/* Right Action Tools & AcmeCloud Status Pill */}
      <div className="flex items-center gap-2 shrink-0">
        {/* AcmeCloud Infrastructure Status Pill */}
        <button
          onClick={() => onToggleView?.('acmecloud')}
          className={`flex items-center gap-2 px-2.5 py-1 rounded-lg border text-xs font-mono transition-all cursor-pointer ${
            acmecloudHealthy
              ? 'bg-[#16171d] hover:bg-[#1f2029] text-zinc-300 border-[#2f313f]'
              : 'bg-red-950/40 hover:bg-red-900/50 text-red-200 border-red-800/60'
          }`}
          title="Click to open AcmeCloud Console and manage build deployments"
        >
          <span
            className={`w-2 h-2 rounded-full ${
              acmecloudHealthy ? 'bg-emerald-400' : 'bg-red-400 animate-pulse'
            }`}
          />
          <span>AcmeCloud: v{acmecloudVersion}</span>
          <span className="text-[10px] uppercase font-bold tracking-wider opacity-75">
            [{acmecloudHealthy ? 'Healthy' : 'Fault'}]
          </span>
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
          className="bg-[#1e1e1e] hover:bg-[#2a2a2a] text-[#ffffff] text-xs px-2.5 py-1.5 rounded-lg border border-[#3c3c3c] flex items-center gap-1.5 transition-all shrink-0 active:scale-[0.98] cursor-pointer"
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

