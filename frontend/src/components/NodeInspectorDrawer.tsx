import React, { useState, useRef, useEffect } from 'react';
import {
  X,
  Copy,
  Check,
  GripHorizontal
} from 'lucide-react';
import { IncidentState } from '../types';

interface NodeInspectorDrawerProps {
  nodeId: string | null;
  onClose: () => void;
  state: IncidentState | null;
}

export const NodeInspectorDrawer: React.FC<NodeInspectorDrawerProps> = ({
  nodeId,
  onClose,
  state
}) => {
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'inputs' | 'telemetry'>('overview');

  // Draggable state: position within the canvas
  const [position, setPosition] = useState<{ x: number; y: number }>({ x: 24, y: 24 });
  const [isDragging, setIsDragging] = useState(false);
  const dragRef = useRef<{ startX: number; startY: number; initX: number; initY: number } | null>(null);

  // Drag event listeners
  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!dragRef.current) return;
      const dx = e.clientX - dragRef.current.startX;
      const dy = e.clientY - dragRef.current.startY;
      setPosition({
        x: Math.max(12, Math.min(window.innerWidth - 300, dragRef.current.initX + dx)),
        y: Math.max(12, Math.min(window.innerHeight - 300, dragRef.current.initY + dy))
      });
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      dragRef.current = null;
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging]);

  const handleMouseDown = (e: React.MouseEvent) => {
    // Only drag when clicking the header bar, not interactive buttons/tabs
    if ((e.target as HTMLElement).closest('button')) return;
    dragRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      initX: position.x,
      initY: position.y
    };
    setIsDragging(true);
  };

  if (!nodeId) return null;

  const service = state?.service || 'checkout-service';

  // Compute node-specific telemetry and context dynamically (handles single and parallel instances)
  const getNodeDetails = () => {
    // Handle parallel tool instances, e.g. "tool-metrics-1", "tool-metrics-2", etc.
    if (nodeId.startsWith('tool-metrics-') || nodeId.startsWith('tool-probe-')) {
      const parts = nodeId.split('-');
      const instanceNum = parts[parts.length - 1] || '1';
      const baseErr = state?.evidence?.metrics?.error_rate ?? 0.385;
      const jitterErr = Math.max(0.01, (baseErr + (parseInt(instanceNum, 10) - 2.5) * 0.008));
      const jitterLatency = (42.0 + parseInt(instanceNum, 10) * 4.2).toFixed(1);

      return {
        title: `Investigator Worker ${instanceNum}`,
        category: 'INVESTIGATION AGENT',
        model: `Investigation Agent · Prometheus MCP (Worker ${instanceNum})`,
        latency: `${jitterLatency}ms`,
        tokens: '280t',
        status: 'COMPLETED',
        description: `Autonomous Investigation Agent parallel probe #${instanceNum} monitoring error rate and connection saturation under load.`,
        inputs: {
          agent: 'InvestigationAgent',
          tool: 'get_metrics',
          service,
          worker_id: `async-worker-${instanceNum}`,
          concurrency: 25,
          time_window: '1m'
        },
        outputs: {
          worker: `async-worker-${instanceNum}`,
          error_rate: parseFloat(jitterErr.toFixed(4)),
          latency_p95_ms: parseFloat((1850 + parseInt(instanceNum, 10) * 15).toFixed(1)),
          db_pool_active: 5,
          db_pool_max: 5,
          requests_per_sec: 142.5
        }
      };
    }

    if (nodeId.startsWith('tool-logs-')) {
      const parts = nodeId.split('-');
      const instanceNum = parts[parts.length - 1] || '1';
      return {
        title: `Log Investigator ${instanceNum}`,
        category: 'INVESTIGATION AGENT',
        model: `Investigation Agent · AcmeCloud FastMCP (Partition ${instanceNum})`,
        latency: '62ms',
        tokens: '310t',
        status: 'COMPLETED',
        description: `Autonomous Investigation Agent log partition #${instanceNum} querying recent container exceptions.`,
        inputs: {
          tool_name: 'get_service_logs',
          service,
          partition: parseInt(instanceNum, 10),
          level: 'ERROR'
        },
        outputs: {
          partition: instanceNum,
          errors_captured: 3,
          sample: 'psycopg2.OperationalError: remaining connection slots are reserved'
        }
      };
    }

    switch (nodeId) {
      case 'ingest':
        return {
          title: 'Alert Ingestion',
          category: 'INGEST',
          model: 'PagerDuty Webhook / EventBridge',
          latency: '18ms',
          tokens: '84t',
          status: 'COMPLETED',
          description: 'Triggered by high 5xx rate and database timeout alert on production service.',
          inputs: {
            incident_id: state?.incident_id || 'INC-001',
            service,
            severity: state?.severity || 'P1',
            trigger: 'SLO Breach: error_rate > 5%'
          },
          outputs: {
            alert_id: 'alt_928f41',
            status: 'TRIGGERED',
            assigned_pipeline: 'aegis-closed-loop-v2'
          }
        };

      case 'triage':
        return {
          title: 'Jev Triage Engine',
          category: 'TRIAGE',
          model: 'typesafe-ai/jev (Vercel AI Gateway)',
          latency: '18.2ms',
          tokens: '120t',
          status: 'COMPLETED',
          description: 'Discriminative sub-25ms classification of incident severity and domain.',
          inputs: {
            service,
            symptoms: '5xx spike to 38.5% post-deployment v2.4.1',
            evaluator: 'typesafe-ai/jev'
          },
          outputs: {
            severity: 'P1',
            category: 'database',
            confidence: 0.96
          }
        };

      case 'tool-logs':
        return {
          title: 'Investigator: Logs & Traces',
          category: 'INVESTIGATION AGENT',
          model: 'Investigation Agent · AcmeCloud FastMCP',
          latency: '65ms',
          tokens: '310t',
          status: 'COMPLETED',
          description: 'Autonomous Investigation Agent probing recent 5xx stack traces and container database connection errors via FastMCP.',
          inputs: {
            agent: 'InvestigationAgent',
            tool: 'get_service_logs',
            service,
            limit: 100,
            level: 'ERROR'
          },
          outputs: {
            error_count: state?.evidence?.error_logs?.length || 3,
            logs: state?.evidence?.error_logs || [
              'psycopg2.OperationalError: remaining connection slots reserved',
              'sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 reached'
            ]
          }
        };

      case 'tool-metrics':
        return {
          title: 'Investigator: Telemetry & Metrics',
          category: 'INVESTIGATION AGENT',
          model: 'Investigation Agent · Prometheus MCP',
          latency: '54ms',
          tokens: '290t',
          status: 'COMPLETED',
          description: 'Autonomous Investigation Agent probing Prometheus timeseries for error rate, latency p95, and pool saturation.',
          inputs: {
            agent: 'InvestigationAgent',
            tool: 'get_metrics',
            service,
            metrics: ['error_rate', 'latency_p95_ms', 'db_pool_active']
          },
          outputs: state?.evidence?.metrics || {
            error_rate: 0.385,
            latency_p95_ms: 1850.0,
            db_pool_active: 5,
            db_pool_max: 5
          }
        };

      case 'docker-ps':
        return {
          title: 'Docker Runtime Investigator',
          category: 'INVESTIGATION AGENT',
          model: 'Docker Daemon MCP Tool',
          latency: '48ms',
          tokens: '210t',
          status: 'COMPLETED',
          description: 'Autonomous container daemon inspector querying live Docker containers, image tags, status, and port bindings.',
          inputs: {
            agent: 'InvestigationAgent',
            tool: 'docker_ps',
            all_containers: false
          },
          outputs: {
            container_count: 4,
            containers: [
              { name: 'acmecloud-checkout', image: 'acmecloud-checkout', status: 'Up (healthy)', ports: '0.0.0.0:8001->8000/tcp' },
              { name: 'acmecloud-postgres', image: 'postgres:16-alpine', status: 'Up (healthy)', ports: '0.0.0.0:5432->5432/tcp' },
              { name: 'acmecloud-prometheus', image: 'prom/prometheus:v2.51.0', status: 'Up', ports: '0.0.0.0:9090->9090/tcp' },
              { name: 'acmecloud-grafana', image: 'grafana/grafana:12.1.1', status: 'Up', ports: '0.0.0.0:3001->3000/tcp' }
            ]
          }
        };

      case 'knowledge':
        return {
          title: 'Runbook RAG & Jev',
          category: 'KNOWLEDGE',
          model: 'ChromaDB + typesafe-ai/jev Reranker',
          latency: '110ms',
          tokens: '620t',
          status: 'COMPLETED',
          description: 'Retrieved operational runbooks and scored candidate recovery SOPs via Jev.',
          inputs: {
            query: 'PostgreSQL connection pool exhaustion',
            top_k: 3
          },
          outputs: {
            top_match: state?.retrieved_runbooks?.[0]?.doc_id || 'RB-001',
            score: state?.retrieved_runbooks?.[0]?.score || 0.96
          }
        };

      case 'diagnose':
        return {
          title: 'AI Diagnostic Agent',
          category: 'REASONING',
          model: 'ai-reasoning',
          latency: '640ms',
          tokens: '850t',
          status: 'COMPLETED',
          description: 'Synthesized telemetry logs, metrics, and runbooks to diagnose root cause.',
          inputs: {
            service,
            symptoms: 'Pool limit=5 exhausted',
            runbook: 'RB-001'
          },
          outputs: state?.diagnosis || {
            root_cause: 'Misconfiguration in v2.4.1 reduced pool max size to 5, starving connections.',
            confidence: 0.95,
            recommended_action: 'rollback_deployment'
          }
        };

      case 'policy':
        return {
          title: 'Policy Guardrail',
          category: 'POLICY',
          model: 'Aegis PolicyEngine (OPA)',
          latency: '82ms',
          tokens: '140t',
          status: state?.approval_granted ? 'COMPLETED' : 'AWAITING APPROVAL',
          description: 'Evaluated remediation safety rules against production blast radius.',
          inputs: {
            action: 'rollback_deployment',
            target_service: service,
            target_version: '2.4.0'
          },
          outputs: state?.policy_evaluation || {
            action: 'rollback_deployment',
            risk_level: 'HIGH',
            decision: 'REQUIRE_APPROVAL',
            requires_approval: true
          }
        };

      case 'remediate':
        return {
          title: 'Remediation Engine',
          category: 'ACTION',
          model: 'AcmeCloud Docker / Rollback MCP',
          latency: '410ms',
          tokens: '320t',
          status: state?.remediation?.status === 'SUCCESS' ? 'COMPLETED' : 'IDLE',
          description: 'Executed atomic rollback of container image to stable baseline v2.4.0.',
          inputs: {
            action: 'rollback_deployment',
            service,
            target_version: '2.4.0'
          },
          outputs: state?.remediation || {
            status: 'SUCCESS',
            target_version: '2.4.0',
            message: 'Container reverted to v2.4.0'
          }
        };

      case 'verify':
        return {
          title: 'SLO Verification Agent',
          category: 'VERIFY',
          model: 'AcmeCloud Telemetry Prober',
          latency: '42.5ms',
          tokens: '540t',
          status: state?.status === 'RESOLVED' ? 'COMPLETED' : 'IDLE',
          description: 'Monitored post-remediation traffic to verify error rate and latency return to nominal SLO.',
          inputs: {
            service,
            probe_duration_sec: 30,
            threshold_error_rate: 0.01
          },
          outputs: state?.verification || {
            is_healthy: true,
            error_rate: 0.002,
            latency_ms: 42.5,
            service_version: '2.4.0'
          }
        };

      default:
        return {
          title: nodeId,
          category: 'PIPELINE NODE',
          model: 'Aegis Engine',
          latency: '30ms',
          tokens: '100t',
          status: 'COMPLETED',
          description: `Pipeline stage ${nodeId} execution.`,
          inputs: { nodeId, service },
          outputs: { status: 'OK' }
        };
    }
  };

  const details = getNodeDetails();

  const handleCopy = () => {
    const payload = JSON.stringify(
      activeTab === 'inputs' ? details.inputs : details.outputs,
      null,
      2
    );
    navigator.clipboard.writeText(payload);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      style={{ left: `${position.x}px`, top: `${position.y}px` }}
      className={`absolute z-50 w-[280px] h-[275px] flex flex-col rounded-xl bg-[#09090b]/95 border border-white/20 backdrop-blur-2xl shadow-[0_20px_50px_rgba(0,0,0,0.95)] animate-slide-fade overflow-hidden text-white font-sans select-none ring-1 ring-white/10 ${
        isDragging ? 'cursor-grabbing ring-white/40' : ''
      }`}
    >
      {/* 1. Draggable Header with Top-Left Live Micro-Animation */}
      <div
        onMouseDown={handleMouseDown}
        className="px-3 py-2 border-b border-white/10 flex items-center justify-between bg-[#121216]/90 cursor-grab active:cursor-grabbing shrink-0"
        title="Click and drag to move card around the canvas"
      >
        <div className="flex items-center gap-2 min-w-0">
          {/* Top-Left Sleek Radar / Pulse Micro-Animation */}
          <div className="relative flex items-center justify-center w-4 h-4 shrink-0">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-white/25 opacity-75 duration-1000" />
            <span className="absolute inline-flex h-3 w-3 rounded-full border border-white/40 animate-spin duration-3000" />
            <span className="relative inline-flex rounded-full h-1 w-1 bg-white shadow-[0_0_6px_rgba(255,255,255,1)]" />
          </div>

          {/* Node Category & Title */}
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1 text-[8px] font-mono tracking-wider text-zinc-400 font-semibold uppercase leading-none">
              <span>{details.category}</span>
              <span className="text-zinc-600">/</span>
              <span
                className={`px-1 py-0.2 rounded text-[7.5px] font-bold ${
                  details.status === 'COMPLETED'
                    ? 'text-white bg-white/10 border border-white/20'
                    : details.status === 'AWAITING APPROVAL'
                    ? 'text-white bg-white/20 border border-white/40 animate-pulse'
                    : 'text-zinc-400 bg-zinc-800'
                }`}
              >
                {details.status}
              </span>
            </div>
            <h3 className="text-[11px] font-bold text-white tracking-tight truncate mt-0.5">
              {details.title}
            </h3>
          </div>
        </div>

        {/* Drag Grip Handle & Close Button */}
        <div className="flex items-center gap-1 shrink-0 ml-1">
          <GripHorizontal className="w-3 h-3 text-zinc-500 hover:text-zinc-300 transition-colors" />
          <button
            onClick={onClose}
            className="p-0.5 rounded text-zinc-400 hover:text-white hover:bg-white/10 transition-colors"
            title="Close Inspector"
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* 2. Minimalist Monochrome Segmented Tabs */}
      <div className="px-2.5 py-1 border-b border-white/5 flex items-center gap-1 bg-[#09090b] shrink-0 text-[9.5px] font-mono">
        <button
          onClick={() => setActiveTab('overview')}
          className={`flex-1 py-0.5 rounded transition-all font-medium text-center ${
            activeTab === 'overview'
              ? 'bg-white text-black font-semibold shadow-sm'
              : 'text-zinc-400 hover:text-white hover:bg-white/5'
          }`}
        >
          Overview
        </button>
        <button
          onClick={() => setActiveTab('inputs')}
          className={`flex-1 py-0.5 rounded transition-all font-medium text-center ${
            activeTab === 'inputs'
              ? 'bg-white text-black font-semibold shadow-sm'
              : 'text-zinc-400 hover:text-white hover:bg-white/5'
          }`}
        >
          Params
        </button>
        <button
          onClick={() => setActiveTab('telemetry')}
          className={`flex-1 py-0.5 rounded transition-all font-medium text-center ${
            activeTab === 'telemetry'
              ? 'bg-white text-black font-semibold shadow-sm'
              : 'text-zinc-400 hover:text-white hover:bg-white/5'
          }`}
        >
          Result
        </button>
      </div>

      {/* 3. Compact Card Body: Strict Height & Internal Scroll */}
      <div className="flex-1 p-2.5 overflow-y-auto text-xs space-y-1.5">
        {/* TAB 1: OVERVIEW */}
        {activeTab === 'overview' && (
          <div className="space-y-1.5 animate-slide-fade">
            {/* 3-Column Minimalist Monochrome KPI Strip */}
            <div className="grid grid-cols-3 gap-1 text-center font-mono">
              <div className="p-1 rounded bg-white/[0.04] border border-white/10">
                <div className="text-[7.5px] text-zinc-500 uppercase">Latency</div>
                <div className="text-[10.5px] font-bold text-white mt-0.5">{details.latency}</div>
              </div>
              <div className="p-1 rounded bg-white/[0.04] border border-white/10">
                <div className="text-[7.5px] text-zinc-500 uppercase">Compute</div>
                <div className="text-[10.5px] font-bold text-white mt-0.5">{details.tokens}</div>
              </div>
              <div className="p-1 rounded bg-white/[0.04] border border-white/10">
                <div className="text-[7.5px] text-zinc-500 uppercase">State</div>
                <div className="text-[9.5px] font-bold text-white mt-0.5 truncate">
                  {details.status === 'COMPLETED' ? '100% OK' : details.status}
                </div>
              </div>
            </div>

            {/* Model & Source */}
            <div className="p-1 rounded bg-white/[0.04] border border-white/10 space-y-0.5">
              <div className="text-[7.5px] font-mono text-zinc-500 uppercase">Engine / Model</div>
              <div className="text-[9.5px] font-mono text-white truncate">{details.model}</div>
            </div>

            {/* Description */}
            <div className="p-1.5 rounded bg-white/[0.04] border border-white/10 text-[9.5px] text-zinc-300 leading-relaxed font-sans">
              {details.description}
            </div>
          </div>
        )}

        {/* TAB 2: INPUT PARAMETERS */}
        {activeTab === 'inputs' && (
          <div className="space-y-1 animate-slide-fade h-full flex flex-col">
            <div className="flex items-center justify-between text-[8.5px] font-mono text-zinc-400">
              <span className="uppercase">Call Arguments</span>
              <button
                onClick={handleCopy}
                className="flex items-center gap-1 text-[8.5px] text-zinc-400 hover:text-white transition-colors"
              >
                {copied ? <Check className="w-2.5 h-2.5 text-white" /> : <Copy className="w-2.5 h-2.5" />}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
            <div className="flex-1 p-1.5 rounded bg-black border border-white/10 font-mono text-[8.5px] text-zinc-200 overflow-auto">
              <pre className="whitespace-pre-wrap">{JSON.stringify(details.inputs, null, 2)}</pre>
            </div>
          </div>
        )}

        {/* TAB 3: RESULT TELEMETRY */}
        {activeTab === 'telemetry' && (
          <div className="space-y-1 animate-slide-fade h-full flex flex-col">
            <div className="flex items-center justify-between text-[8.5px] font-mono text-zinc-400">
              <span className="uppercase">Output Telemetry</span>
              <button
                onClick={handleCopy}
                className="flex items-center gap-1 text-[8.5px] text-zinc-400 hover:text-white transition-colors"
              >
                {copied ? <Check className="w-2.5 h-2.5 text-white" /> : <Copy className="w-2.5 h-2.5" />}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
            <div className="flex-1 p-1.5 rounded bg-black border border-white/10 font-mono text-[8.5px] text-white overflow-auto">
              <pre className="whitespace-pre-wrap">{JSON.stringify(details.outputs, null, 2)}</pre>
            </div>
          </div>
        )}
      </div>

      {/* 4. Minimalist Monochrome Footer */}
      <div className="px-2.5 py-1 border-t border-white/10 bg-[#121216]/60 flex items-center justify-between text-[8px] font-mono text-zinc-500 shrink-0">
        <span>Node: <code className="text-white">{nodeId}</code></span>
        <span className="text-zinc-400">Aegis FastMCP</span>
      </div>
    </div>
  );
};
