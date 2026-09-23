import React, { useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  Handle,
  Position,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeProps,
  BackgroundVariant
} from '@xyflow/react';
import { ThinkingOrb } from 'thinking-orbs';
import {
  Sparkles,
  ShieldCheck,
  Search,
  BookOpen,
  GitFork,
  Cpu,
  RotateCcw,
  CheckCircle2,
  Coins,
  Clock,
  Check,
  Terminal,
  Bot
} from 'lucide-react';
import { IncidentState } from '../types';
import { NodeInspectorDrawer } from './NodeInspectorDrawer';

interface WorkflowCanvasProps {
  state: IncidentState | null;
  onNodeSelect: (nodeId: string) => void;
  selectedNodeId: string | null;
  isRunning?: boolean;
  visibleNodeIds?: string[];
  activeNodeId?: string | null;
}

interface WorkflowNodeData extends Record<string, unknown> {
  nodeId: string;
  category: string;
  categoryIcon: 'ingest' | 'triage' | 'probe' | 'tool' | 'knowledge' | 'topology' | 'reasoning' | 'policy' | 'action' | 'verify';
  title: string;
  subtitle: string;
  tokens: string;
  latency: string;
  status: 'IDLE' | 'RUNNING' | 'DONE' | 'GATE';
  isActive?: boolean;
  onSelect: (id: string) => void;
  isSelected: boolean;
}

// Pixel-perfect node with real Aegis incident operational context & thinking-orbs
const ReferenceNode: React.FC<NodeProps<Node<WorkflowNodeData>>> = ({ data }) => {
  const { nodeId, category, categoryIcon, title, subtitle, tokens, latency, status, isActive, onSelect, isSelected } = data;

  const renderCategoryIcon = () => {
    const iconClass = "w-3 h-3 text-zinc-400";
    switch (categoryIcon) {
      case 'ingest': return <Sparkles className={iconClass} />;
      case 'triage': return <ShieldCheck className={iconClass} />;
      case 'probe': return <Search className={iconClass} />;
      case 'tool': return <Terminal className={iconClass} />;
      case 'knowledge': return <BookOpen className={iconClass} />;
      case 'topology': return <GitFork className={iconClass} />;
      case 'reasoning': return <Cpu className={iconClass} />;
      case 'policy': return <ShieldCheck className={iconClass} />;
      case 'action': return <RotateCcw className={iconClass} />;
      case 'verify': return <CheckCircle2 className={iconClass} />;
      default: return <Sparkles className={iconClass} />;
    }
  };

  return (
    <div
      onClick={() => onSelect(nodeId)}
      className={`relative w-[215px] rounded-xl p-3.5 bg-[#0d0d10] border transition-all duration-300 cursor-pointer select-none shadow-lg ${
        isActive
          ? 'border-white ring-1 ring-white/60 shadow-[0_0_24px_rgba(255,255,255,0.25)]'
          : isSelected
          ? 'border-white ring-1 ring-white/20 shadow-[0_0_24px_rgba(255,255,255,0.08)]'
          : status === 'GATE'
          ? 'border-white/80 ring-1 ring-white/40 shadow-[0_0_20px_rgba(255,255,255,0.15)]'
          : status === 'RUNNING'
          ? 'border-white/80 shadow-[0_0_20px_rgba(255,255,255,0.2)]'
          : 'border-[#26262b] hover:border-[#404048]'
      }`}
    >
      {/* Target Handle (Left) */}
      <Handle
        type="target"
        position={Position.Left}
        className="!w-2 !h-2 !bg-[#6e6e78] !border-none !rounded-full !-left-1"
      />

      {/* Top Header: Category Tag (Icon + Text) + Status Badge */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          {renderCategoryIcon()}
          <span className="text-[10px] font-mono tracking-wider text-zinc-400 font-semibold uppercase">
            {category}
          </span>
        </div>

        {/* Status Badge with ThinkingOrb for active execution */}
        {status === 'RUNNING' || isActive ? (
          <div className="flex items-center gap-1.5 bg-white/10 border border-white/20 px-1.5 py-0.5 rounded">
            <ThinkingOrb state="working" size={20} color="#ffffff" theme="dark" />
            <span className="text-[9px] font-mono text-white font-bold animate-pulse">
              RUNNING
            </span>
          </div>
        ) : status === 'GATE' ? (
          <span className="text-[9px] font-mono text-black bg-white font-bold px-1.5 py-0.5 rounded animate-pulse">
            GATE
          </span>
        ) : status === 'DONE' ? (
          <span className="text-[9px] font-mono text-zinc-300 bg-[#16161a] border border-[#323238] px-1.5 py-0.5 rounded flex items-center gap-1">
            <Check className="w-2.5 h-2.5 text-emerald-400" />
            DONE
          </span>
        ) : (
          <span className="text-[9px] font-mono text-zinc-500 bg-[#16161a] border border-[#26262b] px-1.5 py-0.5 rounded">
            IDLE
          </span>
        )}
      </div>

      {/* Middle: Title & Subtitle */}
      <div className="mt-2.5 mb-3 space-y-0.5">
        <h4 className="text-[13px] font-semibold text-white tracking-tight leading-snug truncate">
          {title}
        </h4>
        <p className="text-[10.5px] text-zinc-400 leading-normal truncate">
          {subtitle}
        </p>
      </div>

      {/* Bottom Footer: Tokens & Latency */}
      <div className="flex items-center justify-between pt-2 border-t border-[#1e1e24] text-[10px] font-mono text-zinc-500">
        <div className="flex items-center gap-1.5">
          <Coins className="w-3 h-3 text-zinc-500" />
          <span>{tokens}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Clock className="w-3 h-3 text-zinc-500" />
          <span>{latency}</span>
        </div>
      </div>

      {/* Source Handle (Right) */}
      <Handle
        type="source"
        position={Position.Right}
        className="!w-2 !h-2 !bg-[#6e6e78] !border-none !rounded-full !-right-1"
      />
    </div>
  );
};

const nodeTypes = {
  workflowNode: ReferenceNode
};

// Logical workflow stages mapping
export const getNodeStage = (id: string): number => {
  if (id === 'ingest') return 0;
  if (id === 'triage') return 1;
  if (id.startsWith('tool-') || id.includes('metrics') || id.includes('logs') || id.includes('probe')) return 2;
  if (id === 'knowledge') return 3;
  if (id === 'diagnose') return 4;
  if (id === 'policy') return 5;
  if (id === 'remediate') return 6;
  if (id === 'verify') return 7;
  return 2;
};

export const WorkflowCanvas: React.FC<WorkflowCanvasProps> = ({
  state,
  onNodeSelect,
  selectedNodeId = null,
  isRunning = false,
  visibleNodeIds = [],
  activeNodeId = null
}) => {
  const status = state?.status || 'OPEN';
  const service = state?.service || 'checkout-service';

  // Compute node statuses and dynamic DAG positioning
  const nodesData = useMemo(() => {
    const isTriageDone = visibleNodeIds.includes('tool-logs') || visibleNodeIds.includes('tool-metrics') || visibleNodeIds.includes('diagnose');
    const isProbeDone = visibleNodeIds.includes('knowledge') || visibleNodeIds.includes('diagnose');
    const isDiagDone = visibleNodeIds.includes('policy') || visibleNodeIds.includes('remediate') || visibleNodeIds.includes('verify');
    const isGateActive = visibleNodeIds.includes('policy') && !visibleNodeIds.includes('remediate');
    const isRemDone = visibleNodeIds.includes('verify');
    const isVerDone = status === 'RESOLVED' && visibleNodeIds.includes('verify');

    // Dynamic telemetry subtitles from actual incident state
    const errRateVal = state?.evidence?.metrics?.error_rate != null
      ? `${(state.evidence.metrics.error_rate * 100).toFixed(1)}%`
      : '38.5%';
    const poolActiveVal = state?.evidence?.metrics?.db_pool_active ?? 5;
    const poolMaxVal = state?.evidence?.metrics?.db_pool_max ?? 5;
    const logCountVal = state?.evidence?.error_logs?.length ?? 4;
    const topRunbook = state?.retrieved_runbooks?.[0];
    const runbookSub = topRunbook
      ? `${topRunbook.doc_id} · ${(topRunbook.score * 100).toFixed(0)}% Match`
      : 'RB-001 DB Pool (96% Match)';
    const diagSub = state?.diagnosis?.recommended_action
      ? `Action: ${state.diagnosis.recommended_action}`
      : 'Root Cause CoT Synthesis';
    const policySub = state?.policy_evaluation
      ? `${state.policy_evaluation.action} · ${state.policy_evaluation.decision}`
      : 'PROD_ROLLBACK Gate · HITL';
    const remSub = state?.remediation
      ? `Reverted to ${state.remediation.parameters?.target_version || 'v2.4.0'}`
      : 'Revert to v2.4.0 Container';
    const verSub = state?.verification
      ? `SLO Nominal · ${(state.verification.error_rate * 100).toFixed(2)}% Err`
      : 'SLO Nominal · 0.02% Err';

    // Catalog of node definitions with their logical DAG stage
    interface NodeTemplate {
      id: string;
      stage: number;
      category: string;
      categoryIcon: 'ingest' | 'triage' | 'probe' | 'tool' | 'knowledge' | 'topology' | 'reasoning' | 'policy' | 'action' | 'verify';
      title: string;
      subtitle: string;
      tokens: string;
      latency: string;
      status: 'IDLE' | 'RUNNING' | 'DONE' | 'GATE';
    }

    const staticTemplates: NodeTemplate[] = [
      {
        id: 'ingest',
        stage: 0,
        category: 'INGEST',
        categoryIcon: 'ingest',
        title: 'Alert Ingestion',
        subtitle: `Webhook · ${service} (${state?.severity || 'P1'})`,
        tokens: '84t',
        latency: '18ms',
        status: 'DONE'
      },
      {
        id: 'triage',
        stage: 1,
        category: 'TRIAGE',
        categoryIcon: 'triage',
        title: 'Jev Triage Engine',
        subtitle: 'Model: typesafe-ai/jev · 18ms',
        tokens: '120t',
        latency: '18.2ms',
        status: isTriageDone ? 'DONE' : activeNodeId === 'triage' ? 'RUNNING' : 'IDLE'
      },
      {
        id: 'tool-logs',
        stage: 2,
        category: 'INVESTIGATE',
        categoryIcon: 'probe',
        title: 'Investigator: Logs',
        subtitle: `AcmeCloud FastMCP · ${logCountVal} Error Logs`,
        tokens: '310t',
        latency: '65ms',
        status: isProbeDone ? 'DONE' : activeNodeId === 'tool-logs' ? 'RUNNING' : 'IDLE'
      },
      {
        id: 'tool-metrics',
        stage: 2,
        category: 'INVESTIGATE',
        categoryIcon: 'probe',
        title: 'Investigator: Metrics',
        subtitle: `Prometheus · ${errRateVal} 5xx · ${poolActiveVal}/${poolMaxVal} Pool`,
        tokens: '290t',
        latency: '54ms',
        status: isProbeDone ? 'DONE' : activeNodeId === 'tool-metrics' ? 'RUNNING' : 'IDLE'
      },
      {
        id: 'knowledge',
        stage: 3,
        category: 'KNOWLEDGE',
        categoryIcon: 'knowledge',
        title: 'Runbook RAG & Jev',
        subtitle: runbookSub,
        tokens: '620t',
        latency: '110ms',
        status: isDiagDone ? 'DONE' : activeNodeId === 'knowledge' ? 'RUNNING' : 'IDLE'
      },
      {
        id: 'diagnose',
        stage: 4,
        category: 'REASONING',
        categoryIcon: 'reasoning',
        title: 'AI Diagnostic Agent',
        subtitle: diagSub,
        tokens: '850t',
        latency: '640ms',
        status: isDiagDone ? 'DONE' : activeNodeId === 'diagnose' ? 'RUNNING' : 'IDLE'
      },
      {
        id: 'policy',
        stage: 5,
        category: 'POLICY',
        categoryIcon: 'policy',
        title: 'Policy Guardrail',
        subtitle: policySub,
        tokens: '140t',
        latency: '82ms',
        status: isRemDone ? 'DONE' : isGateActive ? 'GATE' : 'IDLE'
      },
      {
        id: 'remediate',
        stage: 6,
        category: 'ACTION',
        categoryIcon: 'action',
        title: 'Remediation Engine',
        subtitle: remSub,
        tokens: '320t',
        latency: '410ms',
        status: isRemDone ? 'DONE' : activeNodeId === 'remediate' ? 'RUNNING' : 'IDLE'
      },
      {
        id: 'verify',
        stage: 7,
        category: 'VERIFY',
        categoryIcon: 'verify',
        title: 'SLO Verification',
        subtitle: verSub,
        tokens: '540t',
        latency: '42.5ms',
        status: isVerDone ? 'DONE' : activeNodeId === 'verify' ? 'RUNNING' : 'IDLE'
      }
    ];

    // Resolver to handle both static and dynamic/parallel node templates
    const resolveNodeTemplate = (id: string): NodeTemplate => {
      const found = staticTemplates.find((t) => t.id === id);
      if (found) return found;

      const stage = getNodeStage(id);

      // Parallel tool probe instances (e.g., tool-metrics-1, tool-metrics-2, ...)
      if (id.startsWith('tool-metrics-') || id.startsWith('tool-probe-')) {
        const parts = id.split('-');
        const num = parts[parts.length - 1] || '1';
        return {
          id,
          stage,
          category: 'INVESTIGATOR',
          categoryIcon: 'probe',
          title: `Investigator Worker ${num}`,
          subtitle: `Parallel Probe #${num} · 38.5% Err`,
          tokens: '280t',
          latency: `${42 + parseInt(num, 10) * 4}ms`,
          status: 'DONE'
        };
      }

      // Parallel tool log collectors (e.g., tool-logs-1, tool-logs-2, ...)
      if (id.startsWith('tool-logs-')) {
        const parts = id.split('-');
        const num = parts[parts.length - 1] || '1';
        return {
          id,
          stage,
          category: 'INVESTIGATOR',
          categoryIcon: 'probe',
          title: `Log Investigator ${num}`,
          subtitle: `Partition #${num} · 3 Errors`,
          tokens: '310t',
          latency: '62ms',
          status: 'DONE'
        };
      }

      // Docker runtime inspection node
      if (id === 'docker-ps' || id.startsWith('docker-')) {
        return {
          id,
          stage: 2,
          category: 'INVESTIGATOR',
          categoryIcon: 'probe',
          title: 'Docker Investigator',
          subtitle: 'Host Docker Daemon · 4 Containers',
          tokens: '210t',
          latency: '48ms',
          status: 'DONE'
        };
      }

      return {
        id,
        stage,
        category: 'TOOL',
        categoryIcon: 'tool',
        title: id.replace(/^tool-/, 'Tool: '),
        subtitle: `Parallel Execution · ${service}`,
        tokens: '250t',
        latency: '50ms',
        status: 'DONE'
      };
    };

    // Filter to only visible nodes and resolve templates
    const activeNodes = visibleNodeIds.map(resolveNodeTemplate);
    if (activeNodes.length === 0) return [];

    // Group active nodes by logical stage to dynamically assign compact horizontal columns
    const uniqueStages = Array.from(new Set(activeNodes.map((n) => n.stage))).sort((a, b) => a - b);
    const stageToColMap = new Map<number, number>();
    uniqueStages.forEach((stage, idx) => {
      stageToColMap.set(stage, idx);
    });

    // Count how many nodes are in each stage for vertical spacing
    const stageCounts = new Map<number, number>();
    const stageIndexes = new Map<number, number>();
    activeNodes.forEach((n) => {
      stageCounts.set(n.stage, (stageCounts.get(n.stage) || 0) + 1);
    });

    return activeNodes.map((tpl) => {
      const colIdx = stageToColMap.get(tpl.stage) || 0;
      const countInStage = stageCounts.get(tpl.stage) || 1;
      const currentIndexInStage = stageIndexes.get(tpl.stage) || 0;
      stageIndexes.set(tpl.stage, currentIndexInStage + 1);

      // Compute dynamic X coordinate based on active column
      const x = 60 + colIdx * 270;

      // Compute dynamic Y coordinate (centered or stacked evenly for parallel fan-out)
      let y = 280;
      if (countInStage === 2) {
        y = currentIndexInStage === 0 ? 170 : 390;
      } else if (countInStage > 2) {
        const spacing = 135;
        const totalHeight = (countInStage - 1) * spacing;
        y = 280 - totalHeight / 2 + currentIndexInStage * spacing;
      }

      return {
        id: tpl.id,
        type: 'workflowNode',
        position: { x, y },
        data: {
          nodeId: tpl.id,
          category: tpl.category,
          categoryIcon: tpl.categoryIcon,
          title: tpl.title,
          subtitle: tpl.subtitle,
          tokens: tpl.tokens,
          latency: tpl.latency,
          status: tpl.status,
          isActive: activeNodeId === tpl.id,
          onSelect: onNodeSelect,
          isSelected: selectedNodeId === tpl.id
        }
      };
    });
  }, [status, service, state, selectedNodeId, onNodeSelect, visibleNodeIds, activeNodeId]);

  // Edges connecting active adjacent stages dynamically (supports parallel fan-out and fan-in)
  const edgesData: Edge[] = useMemo(() => {
    if (visibleNodeIds.length < 2) return [];

    const activeWithStages = visibleNodeIds.map((id) => ({
      id,
      stage: getNodeStage(id)
    }));

    const uniqueStages = Array.from(new Set(activeWithStages.map((n) => n.stage))).sort((a, b) => a - b);
    const edges: Edge[] = [];

    // Connect nodes in each active stage to all nodes in the next active stage
    for (let i = 0; i < uniqueStages.length - 1; i++) {
      const currentStage = uniqueStages[i];
      const nextStage = uniqueStages[i + 1];

      const fromNodes = activeWithStages.filter((n) => n.stage === currentStage);
      const toNodes = activeWithStages.filter((n) => n.stage === nextStage);

      for (const from of fromNodes) {
        for (const to of toNodes) {
          const edgeId = `e-${from.id}-${to.id}`;
          const isActivelyExecuting = from.id === activeNodeId || to.id === activeNodeId;

          edges.push({
            id: edgeId,
            source: from.id,
            target: to.id,
            animated: isActivelyExecuting,
            style: isActivelyExecuting
              ? { stroke: '#ffffff', strokeWidth: 2 }
              : { stroke: '#52525b', strokeWidth: 1.5, opacity: 0.6 }
          });
        }
      }
    }

    return edges;
  }, [visibleNodeIds, activeNodeId]);

  const [nodes, setNodes, onNodesChange] = useNodesState(nodesData);
  const [edges, setEdges, onEdgesChange] = useEdgesState(edgesData);

  React.useEffect(() => {
    setNodes(nodesData);
  }, [nodesData, setNodes]);

  React.useEffect(() => {
    setEdges(edgesData);
  }, [edgesData, setEdges]);

  // Helper for human-readable live step description
  const renderActiveStepDescription = (id: string) => {
    if (id.startsWith('tool-metrics-')) {
      const num = id.split('-').pop();
      return `Tool: get_metrics [Worker ${num} parallel]`;
    }
    if (id.startsWith('tool-logs-')) {
      const num = id.split('-').pop();
      return `Tool: get_service_logs [Worker ${num} parallel]`;
    }

    switch (id) {
      case 'ingest': return 'Ingesting alert webhook';
      case 'triage': return 'Jev Triage Engine (sub-25ms)';
      case 'tool-logs': return 'Tool: get_service_logs';
      case 'tool-metrics': return 'Tool: get_metrics';
      case 'docker-ps': return 'MCP Tool: docker_ps (Container Daemon)';
      case 'knowledge': return 'Runbook RAG (RB-001)';
      case 'diagnose': return 'AI Reasoning Synthesis';
      case 'policy': return 'Policy Guardrail (HITL Sign-off)';
      case 'remediate': return 'Remediation Engine (Rollback)';
      case 'verify': return 'SLO Verification (Nominal)';
      default: return id;
    }
  };

  return (
    <div className="relative flex-1 h-full bg-[#000000] overflow-hidden flex flex-col justify-between">
      {/* Subtle Radial Vignette for Depth */}
      <div 
        className="absolute inset-0 pointer-events-none z-0"
        style={{
          background: 'radial-gradient(circle at 50% 50%, rgba(24, 24, 28, 0.25) 0%, rgba(0, 0, 0, 0.95) 100%)'
        }}
      />

      {/* React Flow Interactive Canvas */}
      <div className="relative flex-1 w-full h-full z-10">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          onNodeClick={(_event, node) => onNodeSelect(node.id)}
          fitView
          fitViewOptions={{ padding: 0.15 }}
          minZoom={0.2}
          maxZoom={1.5}
          proOptions={{ hideAttribution: true }}
        >
          {/* Crisp, Highly Visible Micro-Dot Grid */}
          <Background
            variant={BackgroundVariant.Dots}
            gap={24}
            size={1.25}
            color="#44444c"
          />

          {/* Clean Monochrome Controls */}
          <Controls
            showInteractive={false}
            position="top-right"
            className="m-3"
          />
        </ReactFlow>

        {/* Empty State Overlay when no conversation has occurred */}
        {visibleNodeIds.length === 0 && (
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none z-20 px-6 text-center animate-fade-in">
            <div className="max-w-md p-6 rounded-2xl bg-[#0d0d10]/90 border border-[#26262b] backdrop-blur-md shadow-2xl space-y-3">
              <div className="w-10 h-10 rounded-full bg-[#18181b] border border-white/20 flex items-center justify-center mx-auto text-white">
                <Bot className="w-5 h-5 text-white" />
              </div>
              <h3 className="text-sm font-semibold text-white tracking-tight">
                Workflow Canvas Idle
              </h3>
              <p className="text-xs text-zinc-400 leading-relaxed">
                Waiting for conversation. Chat with Aegis to initiate investigation — nodes and execution flow will generate here in real time.
              </p>
            </div>
          </div>
        )}

        {/* Interactive Minimalist Black & White Square Node Inspector Drawer */}
        {selectedNodeId && (
          <NodeInspectorDrawer
            nodeId={selectedNodeId}
            onClose={() => onNodeSelect('')}
            state={state}
          />
        )}

        {/* Sleek Floating Mission Control HUD with Animated Border Beam */}
        <div className="absolute bottom-5 left-1/2 -translate-x-1/2 z-20 pointer-events-auto rounded-full p-[1px] overflow-hidden group shadow-[0_12px_36px_rgba(0,0,0,0.75)] select-none">
          {/* Animated rotating border beam */}
          <div
            className="absolute inset-[-150%] rounded-full opacity-60 group-hover:opacity-100 transition-opacity duration-500 animate-border-spin pointer-events-none"
            style={{
              background: 'conic-gradient(from 0deg at 50% 50%, transparent 0deg, rgba(255, 255, 255, 0.4) 45deg, rgba(16, 185, 129, 0.4) 80deg, transparent 130deg)',
            }}
          />

          {/* Inner HUD Capsule */}
          <div className="relative bg-[#0d0d10]/95 backdrop-blur-md rounded-full px-5 py-2 flex items-center gap-3.5 text-xs whitespace-nowrap">
            {/* Live Engine Status Indicator */}
            <div className="flex items-center gap-2">
              {status === 'RESOLVED' ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              ) : visibleNodeIds.length === 0 ? (
                <span className="w-2 h-2 rounded-full bg-zinc-600" />
              ) : status === 'OPEN' || isRunning || activeNodeId ? (
                <ThinkingOrb state="working" size={20} color="#ffffff" theme="dark" />
              ) : (
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              )}
              <span className="font-mono text-white font-bold text-[11px] tracking-wider uppercase">
                {visibleNodeIds.length === 0 ? 'IDLE' : status}
              </span>
            </div>

            <span className="w-[1px] h-3.5 bg-[#26262b]" />

            {/* Real-time ongoing step / focused node */}
            <div className="flex items-center gap-1.5 text-[11px] text-zinc-400">
              {visibleNodeIds.length === 0 ? (
                <span className="text-zinc-500">Awaiting conversation in chat</span>
              ) : activeNodeId ? (
                <>
                  <span className="text-zinc-500">Executing:</span>
                  <span className="text-white font-mono font-medium">{renderActiveStepDescription(activeNodeId)}</span>
                </>
              ) : status === 'RESOLVED' ? (
                <span className="text-zinc-300">
                  Service healthy · Restored to <code className="text-emerald-400 font-mono">v2.4.0</code>
                </span>
              ) : (
                <>
                  <span className="text-zinc-500">Focused:</span>
                  <span className="text-white font-medium capitalize">{selectedNodeId || 'None'}</span>
                </>
              )}
            </div>

            <span className="w-[1px] h-3.5 bg-[#26262b]" />

            {/* Target Version Badge */}
            <div className="flex items-center gap-1.5 text-[11px] font-mono text-zinc-400">
              <span>Target:</span>
              <span className="text-zinc-200 bg-[#16161a] border border-white/10 px-1.5 py-0.5 rounded font-bold">
                v2.4.0
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
