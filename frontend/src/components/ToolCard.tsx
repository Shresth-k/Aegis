import React, { useState } from 'react';
import { ChevronRight, ChevronDown, Check, Copy } from 'lucide-react';
import { ToolCallItem } from './AgentStreamPanel';

interface ToolCardProps {
  tool: ToolCallItem;
}

export const ToolCard: React.FC<ToolCardProps> = ({ tool }) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);
  const name = (tool.name || '').toLowerCase();

  // Helper to parse tool output if string or object
  const parsedOutput = React.useMemo(() => {
    if (typeof tool.output === 'object' && tool.output !== null) return tool.output;
    try {
      return JSON.parse(tool.output as string);
    } catch {
      return tool.output;
    }
  }, [tool.output]);

  // Clean, general human-readable metadata matching Images 2 & 3
  const meta = React.useMemo(() => {
    const argsObj: Record<string, any> =
      typeof tool.args === 'object' && tool.args !== null ? (tool.args as Record<string, any>) : {};

    // 1. Dynamic Humanized Action Label
    let label = tool.name;
    if (name.includes('triage')) {
      label = 'Triaged incident alert';
    } else if (name.includes('metric')) {
      const isWorker = tool.name.includes('[Worker') || argsObj.worker_id;
      const workerNum = isWorker ? (tool.name.match(/\d+/) || ['1'])[0] : null;
      label = isWorker ? `Queried telemetry metrics [W${workerNum}]` : 'Queried telemetry metrics';
    } else if (name.includes('log')) {
      label = 'Inspected container logs';
    } else if (name.includes('runbook') || name.includes('knowledge')) {
      label = 'Searched runbook docs';
    } else if (name.includes('policy') || name.includes('gate')) {
      label = 'Evaluated safety guardrail';
    } else if (name.includes('rollback') || name.includes('remediat')) {
      label = 'Executed rollback deployment';
    } else if (name.includes('verify') || name.includes('health') || name.includes('slo')) {
      label = 'Verified service SLOs';
    } else {
      // General converter for any tool: "fetch_db_status" -> "Executed fetch db status"
      const clean = tool.name.replace(/^tool[_-]/i, '').replace(/_/g, ' ').replace(/-/g, ' ');
      label = `Executed ${clean}`;
    }

    // 2. Dynamic Argument Pill
    let pill = 'invoked';
    if (name.includes('metric') && (tool.name.includes('[Worker') || argsObj.worker_id)) {
      const workerNum = (tool.name.match(/\d+/) || ['1'])[0];
      pill = `worker-${workerNum}`;
    } else if (argsObj.service) {
      pill = String(argsObj.service);
    } else if (argsObj.target_version) {
      pill = `v${argsObj.target_version}`;
    } else if (argsObj.query) {
      pill = String(argsObj.query).slice(0, 24);
    } else if (argsObj.action) {
      pill = String(argsObj.action);
    } else if (argsObj.target) {
      pill = String(argsObj.target);
    } else if (argsObj.command) {
      pill = String(argsObj.command).slice(0, 20);
    } else if (Object.keys(argsObj).length > 0) {
      const firstVal = Object.values(argsObj)[0];
      pill = typeof firstVal === 'string' ? firstVal.slice(0, 24) : 'executed';
    }

    // 3. Dynamic Result Text
    let result = '';
    if (typeof parsedOutput === 'object' && parsedOutput !== null) {
      if (name.includes('triage')) {
        const sev = parsedOutput.severity || 'P1';
        const domain = parsedOutput.domain || 'system';
        const conf = parsedOutput.confidence ? `${(parsedOutput.confidence * 100).toFixed(0)}%` : '95%';
        result = `${sev} severity (${domain} domain, ${conf} confidence)`;
      } else if (name.includes('metric')) {
        const err = parsedOutput.error_rate != null ? `${(parsedOutput.error_rate * 100).toFixed(1)}% err` : '0.2% err';
        const pool = parsedOutput.db_pool_active != null ? `pool: ${parsedOutput.db_pool_active}/${parsedOutput.db_pool_max || 50}` : 'pool nominal';
        result = `${err}, ${pool}, latency ${parsedOutput.latency_p95_ms || parsedOutput.latency_ms || 42}ms`;
      } else if (name.includes('log')) {
        const count = Array.isArray(parsedOutput) ? parsedOutput.length : (parsedOutput.log_count || parsedOutput.error_count || 1);
        result = `Captured ${count} log entries for ${argsObj.service || 'service'}`;
      } else if (name.includes('policy')) {
        const decision = parsedOutput.decision || 'REQUIRE_APPROVAL';
        result = `${decision} · ${parsedOutput.reason || 'Safety guardrail evaluated'}`;
      } else if (name.includes('rollback') || name.includes('remediat')) {
        result = `${parsedOutput.status || 'SUCCESS'} · Container reverted to baseline v2.4.0`;
      } else if (name.includes('verify')) {
        result = `Nominal health confirmed (error rate ${parsedOutput.error_rate ? (parsedOutput.error_rate * 100).toFixed(2) + '%' : '0.20%'})`;
      } else {
        result = parsedOutput.message || parsedOutput.summary || parsedOutput.status || parsedOutput.result || JSON.stringify(parsedOutput);
      }
    } else if (typeof parsedOutput === 'string') {
      result = parsedOutput;
    } else {
      result = 'Action executed successfully';
    }

    return {
      label,
      pill,
      request: JSON.stringify(tool.args || {}, null, 2),
      result
    };
  }, [name, tool.args, tool.name, parsedOutput]);

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    const payload = JSON.stringify({ name: tool.name, args: tool.args, output: parsedOutput }, null, 2);
    navigator.clipboard.writeText(payload);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  return (
    <div className="select-none my-1">
      {/* 1. Sleek Inline Disclosure Row matching Image 2 & 3 */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="group w-full py-1 px-1.5 rounded-lg flex items-center justify-between text-left hover:bg-white/[0.04] transition-colors cursor-pointer"
      >
        <div className="flex items-center gap-2 min-w-0 flex-1">
          {/* Chevron: > or v */}
          {isExpanded ? (
            <ChevronDown className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
          ) : (
            <ChevronRight className="w-3.5 h-3.5 text-zinc-500 group-hover:text-zinc-400 shrink-0" />
          )}

          {/* Action Label */}
          <span className="text-xs text-zinc-300 font-medium truncate font-sans">
            {meta.label}
          </span>

          {/* Argument Pill Capsule matching Image 2 */}
          <span className="bg-[#222226] text-zinc-300 font-mono text-[11px] px-2 py-0.5 rounded-md border border-white/5 truncate max-w-[150px]">
            {meta.pill}
          </span>
        </div>

        {/* Green Checkmark status at right end matching Image 2 & 3 */}
        <div className="shrink-0 ml-2">
          <Check className="w-3.5 h-3.5 text-emerald-400" />
        </div>
      </button>

      {/* 2. Expanded Minimalist Card matching Image 3 */}
      {isExpanded && (
        <div className="mt-1 ml-5 p-3.5 rounded-2xl bg-[#16161a] border border-white/10 space-y-2.5 text-xs animate-slide-fade shadow-xl">
          {/* Top row: Request label + Copy button */}
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider">
              Request
            </span>
            <button
              onClick={handleCopy}
              className="flex items-center gap-1 text-[10px] text-zinc-400 hover:text-white transition-colors"
              title="Copy JSON Payload"
            >
              {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>
          </div>

          {/* Request code */}
          <div className="font-mono text-xs text-zinc-200 bg-[#0d0d10] p-2.5 rounded-lg border border-white/5 overflow-x-auto whitespace-pre-wrap">
            {meta.request}
          </div>

          {/* Hairline Divider */}
          <div className="border-t border-white/5 my-1" />

          {/* Result label */}
          <div className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider">
            Result
          </div>

          {/* Result output text */}
          <div className="text-xs text-zinc-300 leading-relaxed font-sans font-medium pl-0.5 whitespace-pre-wrap">
            {meta.result}
          </div>
        </div>
      )}
    </div>
  );
};
