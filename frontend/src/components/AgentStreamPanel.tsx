import React, { useState, useMemo, useRef, useEffect } from 'react';
import { ThinkingOrb } from 'thinking-orbs';
import {
  Terminal,
  Activity,
  Cpu,
  ShieldCheck,
  Check,
  X,
  ChevronRight,
  ArrowUp,
  Search,
  BrainCircuit,
  RotateCcw,
  Plus,
  Mic,
  BookOpen,
  Bot,
  CheckCircle2,
  AlertTriangle
} from 'lucide-react';
import { IncidentState, TraceEvent } from '../types';
import { MarkdownRenderer } from './MarkdownRenderer';
import { ToolCard } from './ToolCard';
import { ThinkingProcessCard } from './ThinkingProcessCard';
import { TraceEventCard } from './TraceEventCard';

export interface ToolCallItem {
  name: string;
  args: string | Record<string, any>;
  output: string | Record<string, any>;
}

export interface PolicyGateData {
  action: string;
  service?: string;
  target_version?: string;
  risk_level?: string;
  requires_approval?: boolean;
  reason?: string;
}

export interface ChatTurn {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  time: string;
  thinking?: string;
  durationSeconds?: number;
  toolCalls?: ToolCallItem[];
  toolCall?: ToolCallItem;
  policyGate?: PolicyGateData;
  status?: string;
  isStreaming?: boolean;
}

interface AgentStreamPanelProps {
  state: IncidentState | null;
  traces: TraceEvent[];
  selectedNodeId: string | null;
  onApprove: (approved: boolean, reason?: string) => void;
  isApproving: boolean;
  onSendMessage?: (msg: string) => void;
  visibleNodeIds?: string[];
  activeNodeId?: string | null;
  onChatResponse?: (data: any) => void;
}

export const AgentStreamPanel: React.FC<AgentStreamPanelProps> = ({
  state,
  traces,
  selectedNodeId,
  onApprove,
  isApproving,
  onSendMessage,
  visibleNodeIds = [],
  activeNodeId = null,
  onChatResponse
}) => {
  const [activeTab, setActiveTab] = useState<'stream' | 'agents' | 'logs'>('stream');
  const [filter, setFilter] = useState<'all' | 'reasoning' | 'tools' | 'gate'>('all');
  const [inputText, setInputText] = useState<string>('');
  const [showQuickActions, setShowQuickActions] = useState<boolean>(false);
  const [isCopilotThinking, setIsCopilotThinking] = useState<boolean>(false);
  const [collapsedTools, setCollapsedTools] = useState<Record<string, boolean>>({});
  const [collapsedThinking, setCollapsedThinking] = useState<Record<string, boolean>>({});

  // Initial clean ChatGPT-style stream (no pre-baked cards)
  const [chatMessages, setChatMessages] = useState<ChatTurn[]>([
    {
      id: 'welcome-1',
      role: 'assistant',
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      text: 'Aegis online. Standing by for incident **INC-001** (`checkout-service`).\n\nChat here to initiate an investigation, inspect telemetry, or instruct remediation.'
    }
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const status = state?.status || 'OPEN';

  // Toggle tool output collapse
  const toggleToolCollapse = (toolKey: string) => {
    setCollapsedTools((prev) => ({
      ...prev,
      [toolKey]: !prev[toolKey]
    }));
  };

  // Toggle thinking collapse
  const toggleThinkingCollapse = (msgId: string) => {
    setCollapsedThinking((prev) => ({
      ...prev,
      [msgId]: !prev[msgId]
    }));
  };

  // Find latest active policy gate for pinned bottom approval
  // MUST only hook if the most recent assistant message explicitly asked for approval
  // and the user has not yet replied to it.
  const latestPolicyGate = useMemo(() => {
    if (chatMessages.length === 0) return null;
    if (status === 'RESOLVED' || status === 'ESCALATED' || state?.approval_granted) return null;

    // Scan backwards from the latest message
    for (let i = chatMessages.length - 1; i >= 0; i--) {
      const msg = chatMessages[i];
      // If the latest message or any message after the gate is from the user,
      // the user has already replied or typed since the gate was posed.
      if (msg.role === 'user') {
        return null;
      }
      if (msg.role === 'assistant' && msg.policyGate) {
        return msg.policyGate;
      }
    }
    return null;
  }, [chatMessages, status, state?.approval_granted]);

  const isPendingApproval =
    Boolean(latestPolicyGate) &&
    status !== 'RESOLVED' &&
    status !== 'ESCALATED' &&
    status !== 'REMEDIATING' &&
    !state?.approval_granted &&
    !isApproving;

  // Dynamic Agent Mesh status based on live workflow execution
  const dynamicAgents = useMemo(() => {
    const isIngestDone = visibleNodeIds.includes('triage') || visibleNodeIds.includes('diagnose');
    const isTriageDone = visibleNodeIds.includes('tool-logs') || visibleNodeIds.includes('tool-metrics') || visibleNodeIds.includes('diagnose');
    const isProbeDone = visibleNodeIds.includes('knowledge') || visibleNodeIds.includes('diagnose');
    const isRagDone = visibleNodeIds.includes('diagnose') || visibleNodeIds.includes('policy');
    const isDiagDone = visibleNodeIds.includes('policy') || visibleNodeIds.includes('remediate');
    const isPolicyDone = status === 'RESOLVED' || visibleNodeIds.includes('remediate') || visibleNodeIds.includes('verify');

    const topRunbook = state?.retrieved_runbooks?.[0];
    const diagRootCause = state?.diagnosis?.root_cause;
    const policyDesc = state?.policy_evaluation?.reason || 'Enforces deterministic safety rule PROD_ROLLBACK_APPROVAL. Human sign-off required.';

    return [
      {
        id: 'ingest',
        name: 'Alert Ingest Agent',
        icon: Terminal,
        status: activeNodeId === 'ingest' ? 'RUNNING' : isIngestDone ? 'DONE' : visibleNodeIds.includes('ingest') ? 'RUNNING' : 'PENDING',
        desc: `Ingests alerts and creates incident context for ${state?.service || 'checkout-service'}.`,
        model: 'Webhook Receiver',
        latency: isIngestDone ? '18ms' : activeNodeId === 'ingest' ? 'Ingesting...' : 'Queued'
      },
      {
        id: 'triage',
        name: 'Jev Triage Engine',
        icon: ShieldCheck,
        status: activeNodeId === 'triage' ? 'RUNNING' : isTriageDone ? 'DONE' : visibleNodeIds.includes('triage') ? 'RUNNING' : 'PENDING',
        desc: `Sub-25ms SLA triage. Enriched topology dependency: ${state?.service || 'checkout'} → ${state?.evidence?.dependencies?.join(', ') || 'postgres:5432'}.`,
        model: 'Jev Heuristic Engine',
        latency: isTriageDone ? '21.4ms' : activeNodeId === 'triage' ? 'Evaluating...' : 'Queued'
      },
      {
        id: 'probe',
        name: 'Telemetry Probe Agent',
        icon: Search,
        status: (activeNodeId === 'tool-logs' || activeNodeId === 'tool-metrics') ? 'RUNNING' : isProbeDone ? 'DONE' : (visibleNodeIds.includes('tool-logs') || visibleNodeIds.includes('tool-metrics')) ? 'RUNNING' : 'PENDING',
        desc: 'Dispatched AcmeCloud FastMCP tools get_service_logs and get_metrics.',
        model: 'AcmeCloud FastMCP',
        latency: isProbeDone ? '119ms' : (activeNodeId === 'tool-logs' || activeNodeId === 'tool-metrics') ? 'Polling MCP...' : 'Queued'
      },
      {
        id: 'rag',
        name: 'Runbook Knowledge RAG',
        icon: BookOpen,
        status: activeNodeId === 'knowledge' ? 'RUNNING' : isRagDone ? 'DONE' : visibleNodeIds.includes('knowledge') ? 'RUNNING' : 'PENDING',
        desc: topRunbook
          ? `Matched Runbook ${topRunbook.doc_id} (${topRunbook.title}) with ${(topRunbook.score * 100).toFixed(0)}% confidence.`
          : 'Matched Runbook RB-001 (Database Pool Exhaustion) with 96% vector similarity.',
        model: 'ChromaDB Vector RAG',
        latency: isRagDone ? '110ms' : activeNodeId === 'knowledge' ? 'Vector Search...' : 'Queued'
      },
      {
        id: 'diagnose',
        name: 'AI Reasoning Engine',
        icon: Cpu,
        status: activeNodeId === 'diagnose' ? 'RUNNING' : isDiagDone ? 'DONE' : visibleNodeIds.includes('diagnose') ? 'RUNNING' : 'PENDING',
        desc: diagRootCause ? `Synthesized: ${diagRootCause}` : 'Synthesized root cause through multi-turn Chain-of-Thought reasoning.',
        model: 'AI Model (Reasoning)',
        latency: isDiagDone ? '640ms' : activeNodeId === 'diagnose' ? 'Synthesizing CoT...' : 'Queued'
      },
      {
        id: 'policy',
        name: 'Policy Guardrail',
        icon: ShieldCheck,
        status: isPendingApproval ? 'GATE' : isPolicyDone ? 'DONE' : activeNodeId === 'policy' ? 'RUNNING' : 'PENDING',
        desc: policyDesc,
        model: 'Aegis Policy Gate',
        latency: isPolicyDone ? '82ms' : isPendingApproval ? 'Awaiting Sign-off' : activeNodeId === 'policy' ? 'Evaluating Rule...' : 'Queued'
      },
      {
        id: 'remediate',
        name: 'Remediation Engine',
        icon: RotateCcw,
        status: status === 'RESOLVED' ? 'RESOLVED' : (status === 'REMEDIATING' || activeNodeId === 'remediate' || activeNodeId === 'verify') ? 'RUNNING' : 'PENDING',
        desc: state?.remediation?.message || 'Executes container rollback to v2.4.0 and monitors Prometheus SLO metrics.',
        model: 'Docker Compose / AcmeCloud',
        latency: status === 'RESOLVED' ? '410ms' : (status === 'REMEDIATING' || activeNodeId === 'remediate') ? 'Executing...' : 'Queued'
      },
      // Dynamically append any parallel workers or arbitrary custom agent nodes
      ...visibleNodeIds
        .filter((id) => id.includes('-') && (id.startsWith('tool-metrics-') || id.startsWith('tool-logs-') || id.startsWith('worker-')))
        .map((wId) => {
          const num = wId.split('-').pop() || '1';
          const isLogs = wId.includes('logs');
          return {
            id: wId,
            name: `Parallel Worker ${num} Agent`,
            icon: isLogs ? Terminal : Activity,
            status: activeNodeId === wId ? 'RUNNING' : 'DONE',
            desc: `Concurrent worker thread ${num} executing isolated telemetry probe partition.`,
            model: 'FastMCP Worker Partition',
            latency: '48ms'
          };
        })
    ];
  }, [visibleNodeIds, activeNodeId, status, state]);

  // Auto-scroll to bottom of chat when new messages appear
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, isCopilotThinking]);

  // Handle user submitting chat message to /api/chat/stream or /api/chat
  const handleSendText = async (textToSend: string) => {
    const text = textToSend.trim();
    if (!text) return;
    const sendStartTime = Date.now();

    const userTurn: ChatTurn = {
      id: `user-${Date.now()}`,
      role: 'user',
      text,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    };

    const assistantId = `assistant-${Date.now()}`;
    const placeholderTurn: ChatTurn = {
      id: assistantId,
      role: 'assistant',
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      text: '',
      thinking: '',
      toolCalls: [],
      isStreaming: true
    };

    setChatMessages((prev) => [...prev, userTurn, placeholderTurn]);
    setInputText('');
    setShowQuickActions(false);
    onSendMessage?.(text);
    setIsCopilotThinking(true);

    let accumulatedText = '';
    let accumulatedThinking = '';
    let currentTools: ToolCallItem[] = [];
    let currentPolicyGate: PolicyGateData | undefined = undefined;
    let currentStatus: string | undefined = undefined;

    try {
      const res = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          incident_id: state?.incident_id || 'INC-001',
          message: text,
          history: chatMessages.slice(-6).map((m) => ({
            role: m.role,
            text: m.text,
            thinking: m.thinking
          }))
        })
      });

      if (res.ok && res.body) {
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            const jsonStr = line.slice(6).trim();
            if (!jsonStr) continue;

            try {
              const ev = JSON.parse(jsonStr);

              if (ev.type === 'thinking') {
                accumulatedThinking = ev.thinking || '';
                setChatMessages((prev) =>
                  prev.map((m) => (m.id === assistantId ? { ...m, thinking: accumulatedThinking } : m))
                );
              } else if (ev.type === 'tool_start') {
                const exists = currentTools.some((t) => t.name === ev.name);
                if (!exists) {
                  currentTools = [
                    ...currentTools,
                    { name: ev.name, args: ev.args || {}, output: 'Executing tool on AcmeCloud...' }
                  ];
                  setChatMessages((prev) =>
                    prev.map((m) => (m.id === assistantId ? { ...m, toolCalls: [...currentTools] } : m))
                  );
                }
              } else if (ev.type === 'tool_result') {
                currentTools = currentTools.map((t) =>
                  t.name === ev.name ? { ...t, output: ev.output } : t
                );
                setChatMessages((prev) =>
                  prev.map((m) => (m.id === assistantId ? { ...m, toolCalls: [...currentTools] } : m))
                );
                onChatResponse?.({
                  tool_result: {
                    name: ev.name,
                    output: ev.output,
                    node: ev.node,
                    latency_ms: ev.latency_ms || ev.output?.latency_ms,
                    source: ev.source || ev.output?.source,
                    args: ev.args
                  }
                });
              } else if (ev.type === 'node_spawned') {
                if (ev.node_id) {
                  onChatResponse?.({ new_nodes: [ev.node_id] });
                }
              } else if (ev.type === 'text_delta') {
                accumulatedText += ev.delta || '';
                setChatMessages((prev) =>
                  prev.map((m) => (m.id === assistantId ? { ...m, text: accumulatedText } : m))
                );
              } else if (ev.type === 'done') {
                const elapsedSec = ev.duration_seconds || ((Date.now() - sendStartTime) / 1000);
                accumulatedText = ev.reply || accumulatedText;
                accumulatedThinking = ev.thinking || accumulatedThinking;
                currentPolicyGate = ev.policy_gate;
                currentStatus = ev.status;
                if (ev.tool_calls) currentTools = ev.tool_calls;

                setChatMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId
                      ? {
                          ...m,
                          text: accumulatedText,
                          thinking: accumulatedThinking,
                          durationSeconds: elapsedSec,
                          toolCalls: currentTools.length > 0 ? currentTools : undefined,
                          policyGate: currentPolicyGate,
                          status: currentStatus,
                          isStreaming: false
                        }
                      : m
                  )
                );

                onChatResponse?.({
                  reply: accumulatedText,
                  thinking: accumulatedThinking,
                  tool_calls: currentTools,
                  new_nodes: ev.new_nodes,
                  policy_gate: currentPolicyGate,
                  status: currentStatus
                });
              }
            } catch (parseErr) {
              console.warn('Error parsing SSE event:', parseErr);
            }
          }
        }
      } else {
        // Fallback to synchronous /api/chat with client typewriter
        const fallbackRes = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            incident_id: state?.incident_id || 'INC-001',
            message: text,
            history: chatMessages.slice(-6).map((m) => ({
              role: m.role,
              text: m.text,
              thinking: m.thinking
            }))
          })
        });

        if (fallbackRes.ok) {
          const data = await fallbackRes.json();
          const toolsList: ToolCallItem[] = data.tool_calls || (data.tool_call ? [data.tool_call] : []);
          
          setChatMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? {
                    ...m,
                    text: data.reply,
                    thinking: data.thinking,
                    durationSeconds: data.duration_seconds || ((Date.now() - sendStartTime) / 1000),
                    toolCalls: toolsList.length > 0 ? toolsList : undefined,
                    toolCall: data.tool_call,
                    policyGate: data.policy_gate,
                    status: data.status,
                    isStreaming: false
                  }
                : m
            )
          );
          onChatResponse?.(data);
        } else {
          throw new Error(`API error ${fallbackRes.status}`);
        }
      }
    } catch (err) {
      console.warn('Chat API error, falling back locally:', err);
      const q = text.toLowerCase();
      let replyText = `Aegis standing by for incident **${state?.incident_id || 'INC-001'}** on \`${state?.service || 'checkout-service'}\`. Current engine status: **${status}**.`;
      let thinking = 'Local fallback reasoning engine.';

      if (q.includes('start') || q.includes('investigate') || q.includes('what is wrong') || q.includes('what\'s wrong') || q.includes('heal')) {
        replyText = `**Autonomous Investigation Complete:**\n• **Triage**: High 5xx error rate classified as \`database\` saturation (P1).\n• **Root Cause**: \`v2.4.1\` reduced \`DB_CONNECTION_POOL=5\`, causing pool starvation under load.\n• **Policy Gate**: Rollback to \`v2.4.0\` requires operator authorization.`;
        thinking = 'Executed automated triage, telemetry probes, runbook matching, and policy guardrail.';
        const fallbackGate: PolicyGateData = {
          action: 'rollback_deployment',
          service: state?.service || 'checkout-service',
          target_version: '2.4.0',
          risk_level: 'HIGH',
          requires_approval: true,
          reason: 'Production rollback requires human authorization.'
        };
        setChatMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  text: replyText,
                  thinking,
                  policyGate: fallbackGate,
                  status: 'PENDING_APPROVAL',
                  isStreaming: false
                }
              : m
          )
        );
        onChatResponse?.({
          reply: replyText,
          thinking,
          new_nodes: ['ingest', 'triage', 'tool-logs', 'tool-metrics', 'knowledge', 'diagnose', 'policy'],
          policy_gate: fallbackGate,
          status: 'PENDING_APPROVAL'
        });
        return;
      }

      setChatMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? {
                ...m,
                text: replyText,
                thinking,
                isStreaming: false
              }
            : m
        )
      );
    } finally {
      setIsCopilotThinking(false);
    }
  };

  const handleSend = () => {
    handleSendText(inputText);
  };

  const handleQuickAction = (actionText: string) => {
    setShowQuickActions(false);
    handleSendText(actionText);
  };

  // Helper to render tool icon based on name
  const renderToolIcon = (toolName: string) => {
    const name = toolName.toLowerCase();
    if (name.includes('metric')) return <Activity className="w-3.5 h-3.5 text-zinc-300" />;
    if (name.includes('log')) return <Terminal className="w-3.5 h-3.5 text-zinc-300" />;
    if (name.includes('triage')) return <ShieldCheck className="w-3.5 h-3.5 text-zinc-300" />;
    if (name.includes('runbook') || name.includes('knowledge')) return <BookOpen className="w-3.5 h-3.5 text-zinc-300" />;
    if (name.includes('policy') || name.includes('gate')) return <ShieldCheck className="w-3.5 h-3.5 text-zinc-300" />;
    if (name.includes('rollback') || name.includes('remediat')) return <RotateCcw className="w-3.5 h-3.5 text-zinc-300" />;
    if (name.includes('verify') || name.includes('health')) return <CheckCircle2 className="w-3.5 h-3.5 text-zinc-300" />;
    return <Search className="w-3.5 h-3.5 text-zinc-300" />;
  };

  return (
    <aside className="w-[480px] xl:w-[540px] h-full bg-[#0d0d11]/80 backdrop-blur-2xl border-l border-white/[0.08] flex flex-col justify-between shrink-0 select-none relative z-20">
      {/* 1. Ultra-Minimal Header Navigation */}
      <div className="h-11 px-4 border-b border-white/[0.08] flex items-center justify-between shrink-0 bg-[#0e0e12]/60 backdrop-blur-xl">
        {/* Left: Minimal segmented tabs */}
        <div className="flex items-center gap-1 text-xs">
          <button
            onClick={() => setActiveTab('stream')}
            className={`px-2.5 py-1 rounded-md transition-all font-sans ${
              activeTab === 'stream'
                ? 'bg-white/[0.08] text-white font-semibold'
                : 'text-zinc-500 hover:text-zinc-300'
            }`}
          >
            Stream
          </button>
          <button
            onClick={() => setActiveTab('agents')}
            className={`px-2.5 py-1 rounded-md transition-all font-sans flex items-center gap-1.5 ${
              activeTab === 'agents'
                ? 'bg-white/[0.08] text-white font-semibold'
                : 'text-zinc-500 hover:text-zinc-300'
            }`}
          >
            <span>Agents</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          </button>
          <button
            onClick={() => setActiveTab('logs')}
            className={`px-2.5 py-1 rounded-md transition-all font-sans ${
              activeTab === 'logs'
                ? 'bg-white/[0.08] text-white font-semibold'
                : 'text-zinc-500 hover:text-zinc-300'
            }`}
          >
            Traces
          </button>
        </div>

        {/* Right: Minimalist Filter Chips */}
        {activeTab === 'stream' && (
          <div className="flex items-center gap-1 text-[10px] font-mono">
            {(['all', 'reasoning', 'tools', 'gate'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-2 py-0.5 rounded transition-all ${
                  filter === f
                    ? 'bg-white text-black font-semibold'
                    : 'text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.04]'
                }`}
              >
                {f === 'reasoning' ? 'CoT' : f}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* 2. Main Content Area by Active Tab */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4">
        {/* TAB A: INTERACTIVE CHAT STREAM (ChatGPT-style) */}
        {activeTab === 'stream' && (
          <div className="space-y-4">
            {chatMessages
              .filter((msg) => {
                if (filter === 'all') return true;
                if (filter === 'reasoning') return Boolean(msg.thinking);
                if (filter === 'tools') return Boolean((msg.toolCalls && msg.toolCalls.length > 0) || msg.toolCall);
                if (filter === 'gate') return Boolean(msg.policyGate);
                return true;
              })
              .map((msg) => {
                const tools = msg.toolCalls || (msg.toolCall ? [msg.toolCall] : []);
                const isUser = msg.role === 'user';
                const isThinkingCollapsed = collapsedThinking[msg.id] ?? false;

                return (
                  <div
                    key={msg.id}
                    className={`text-xs leading-relaxed animate-slide-fade transition-all ${
                      isUser
                        ? 'p-3 rounded-2xl bg-[#1c1c22] border border-white/5 text-white ml-8 shadow-sm'
                        : 'p-3.5 rounded-2xl bg-[#141418]/90 border border-white/[0.07] text-zinc-200 mr-1 shadow-sm space-y-2.5'
                    }`}
                  >
                    {/* Header */}
                    <div className="flex items-center justify-between text-[10px] text-zinc-500 font-mono">
                      <div className="flex items-center gap-1.5">
                        {isUser ? (
                          <span className="text-white font-semibold">Operator</span>
                        ) : (
                          <>
                            <div className="w-4 h-4 rounded-full bg-white text-black flex items-center justify-center font-bold text-[9px] shrink-0">
                              A
                            </div>
                            <span className="text-white font-semibold text-xs">Aegis</span>
                          </>
                        )}
                      </div>
                      <span>{msg.time}</span>
                    </div>

                    {/* Agent Thinking Accordion with Structured SRE Cognitive Phases (Matching Image 1) */}
                    {!isUser && msg.thinking && (
                      <ThinkingProcessCard
                        thinking={msg.thinking}
                        isStreaming={msg.isStreaming}
                        durationSeconds={msg.durationSeconds}
                      />
                    )}

                    {/* Interactive Tool Execution Rows (Matching Image 2 & 3) */}
                    {!isUser && tools.length > 0 && (
                      <div className="space-y-1 pt-0.5">
                        {tools.map((tool, idx) => {
                          const toolKey = `${msg.id}-tool-${idx}-${tool.name}`;
                          return <ToolCard key={toolKey} tool={tool} />;
                        })}
                      </div>
                    )}

                    {/* Inline Policy Status / Confirmation */}
                    {!isUser && msg.policyGate && (
                      status === 'RESOLVED' || state?.approval_granted ? (
                        <div className="bg-[#141418] border border-emerald-900/40 rounded-xl p-2.5 text-xs text-emerald-300 flex items-center gap-2">
                          <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                          <span>
                            <strong>Approved by LeadSRE.</strong> Rollback to v{msg.policyGate.target_version || '2.4.0'} executed and verified.
                          </span>
                        </div>
                      ) : status === 'ESCALATED' ? (
                        <div className="bg-[#141418] border border-zinc-700 rounded-xl p-2.5 text-xs text-zinc-300 flex items-center gap-2">
                          <X className="w-4 h-4 text-zinc-400 shrink-0" />
                          <span>
                            <strong>Rejected by Operator.</strong> Escalated to human on-call Lead SRE.
                          </span>
                        </div>
                      ) : (
                        <div className="bg-[#16161a] border border-white/10 rounded-xl p-3 text-xs text-zinc-300 space-y-2">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <ShieldCheck className="w-3.5 h-3.5 text-white" />
                              <span className="font-semibold text-white">Policy Guardrail Hooked</span>
                            </div>
                            <span className="text-[10px] font-mono text-zinc-200 bg-white/10 border border-white/20 px-1.5 py-0.5 rounded font-semibold">
                              {msg.policyGate.risk_level || 'HIGH'} RISK
                            </span>
                          </div>
                          <p className="text-zinc-300 text-xs leading-relaxed font-sans">
                            {msg.policyGate.reason || `Action ${msg.policyGate.action} requires operator approval before execution.`}
                          </p>
                          <div className="flex items-center gap-2 pt-0.5">
                            <button
                              onClick={() => {
                                handleSendText(`Approve rollback to v${msg.policyGate?.target_version || '2.4.0'}`);
                              }}
                              disabled={isApproving || isCopilotThinking}
                              className="px-3 py-1.5 bg-white hover:bg-zinc-200 text-black text-xs rounded-lg font-semibold flex items-center gap-1.5 transition-all shadow-sm active:scale-95"
                            >
                              <Check className="w-3.5 h-3.5 text-black" />
                              <span>Approve Rollback</span>
                            </button>
                            <button
                              onClick={() => {
                                handleSendText('Reject rollback');
                              }}
                              disabled={isApproving || isCopilotThinking}
                              className="px-3 py-1.5 bg-[#18181b] hover:bg-zinc-800 text-zinc-300 hover:text-white border border-[#27272a] text-xs rounded-lg font-medium flex items-center gap-1.5 transition-all active:scale-95"
                            >
                              <X className="w-3.5 h-3.5 text-zinc-400" />
                              <span>Reject</span>
                            </button>
                          </div>
                        </div>
                      )
                    )}

                    {/* Rich Markdown Message Text */}
                    <div className="text-zinc-200 text-xs leading-relaxed pt-0.5 font-sans">
                      <MarkdownRenderer content={msg.text} />
                      {msg.isStreaming && (
                        <span className="inline-block w-1.5 h-3.5 bg-white ml-1 animate-pulse align-middle" />
                      )}
                    </div>
                  </div>
                );
              })}

            {/* Active Thinking Indicator */}
            {isCopilotThinking && (
              <div className="flex items-center gap-2.5 p-3.5 rounded-2xl bg-[#141416] border border-[#27272a] text-xs text-zinc-300 mr-8 animate-pulse shadow-md">
                <ThinkingOrb state="working" size={20} color="#FFFFFF" theme="dark" />
                <span>Aegis is analyzing incident context & executing tools...</span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}

        {/* TAB B: DYNAMIC ACTIVE AGENTS DASHBOARD */}
        {activeTab === 'agents' && (
          <div className="space-y-3 animate-slide-fade">
            <div className="flex items-center justify-between pb-1 border-b border-[#27272a]">
              <span className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                Active Agents ({dynamicAgents.filter((a) => a.status === 'RUNNING' || a.status === 'DONE' || a.status === 'RESOLVED').length} / {dynamicAgents.length})
              </span>
              <span className="text-[11px] font-mono text-zinc-300 bg-[#141416] border border-[#27272a] px-2 py-0.5 rounded flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Mesh: {status === 'RESOLVED' ? 'COMPLETED' : 'ONLINE'}
              </span>
            </div>

            {dynamicAgents.map((agent) => {
              const Icon = agent.icon;
              const isRunning = agent.status === 'RUNNING';
              const isDone = agent.status === 'DONE' || agent.status === 'RESOLVED';
              const isGate = agent.status === 'GATE';
              const isPending = agent.status === 'PENDING';

              return (
                <div
                  key={agent.id}
                  className={`p-3 rounded-xl border transition-all duration-300 space-y-2 ${
                    isRunning
                      ? 'bg-[#18181b] border-zinc-600 shadow-[0_0_16px_rgba(0,0,0,0.5)]'
                      : isGate
                      ? 'bg-[#18181b] border-zinc-600 ring-1 ring-zinc-700'
                      : isDone
                      ? 'bg-[#161618] border-[#27272a]'
                      : 'bg-[#121214]/50 border-dashed border-[#222226] opacity-45'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Icon className={`w-4 h-4 ${isRunning ? 'text-white' : isDone ? 'text-zinc-300' : 'text-zinc-500'}`} />
                      <span className={`text-xs font-bold ${isPending ? 'text-zinc-500' : 'text-white'}`}>{agent.name}</span>
                    </div>

                    {isRunning ? (
                      <span className="text-[10px] font-mono text-white bg-[#141416] border border-zinc-700 px-1.5 py-0.5 rounded flex items-center gap-1">
                        <ThinkingOrb state="working" size={20} color="#ffffff" theme="dark" />
                        RUNNING
                      </span>
                    ) : isGate ? (
                      <span className="text-[10px] font-mono text-zinc-100 bg-zinc-800 border border-zinc-600 px-1.5 py-0.5 rounded font-bold animate-pulse">
                        GATE: APPROVAL
                      </span>
                    ) : isDone ? (
                      <span className="text-[10px] font-mono text-zinc-300 bg-[#141416] border border-[#27272a] px-1.5 py-0.5 rounded flex items-center gap-1">
                        <Check className="w-2.5 h-2.5 text-emerald-400" /> {agent.status}
                      </span>
                    ) : (
                      <span className="text-[10px] font-mono text-zinc-600 bg-[#141416]/60 px-1.5 py-0.5 rounded">
                        STANDBY
                      </span>
                    )}
                  </div>

                  <p className={`text-[11px] leading-normal ${isPending ? 'text-zinc-600' : 'text-zinc-400'}`}>
                    {agent.desc}
                  </p>

                  <div className="flex items-center justify-between pt-1 border-t border-[#27272a]/60 text-[10px] font-mono text-zinc-500">
                    <span>{agent.model}</span>
                    <span className={isRunning ? 'text-white font-medium' : isDone ? 'text-zinc-400' : 'text-zinc-600'}>
                      {agent.latency}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* TAB C: LIVE TRACE LOGS */}
        {activeTab === 'logs' && (
          <div className="space-y-2 font-mono text-xs text-zinc-400">
            <div className="flex items-center justify-between pb-1 border-b border-[#27272a]">
              <span className="text-xs font-bold text-white uppercase tracking-wider">Live System Logs & Traces</span>
              <span className="text-[10px] text-zinc-500">{state?.service || 'checkout-service'}</span>
            </div>

            <div className="space-y-2 overflow-x-auto leading-relaxed max-h-[calc(100vh-220px)] overflow-y-auto pr-1">
              {traces && traces.length > 0 ? (
                traces.map((ev, idx) => (
                  <TraceEventCard key={idx} event={ev} />
                ))
              ) : (
                <div className="bg-[#141416] border border-[#27272a] rounded-xl p-6 text-zinc-500 text-center font-mono text-xs">
                  Waiting for live telemetry events...
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* 2.5 DOCKED POLICY APPROVAL GATE (ALWAYS AT THE BOTTOM) */}
      {isPendingApproval && latestPolicyGate && (
        <div className="px-3 pt-2 pb-0 bg-transparent shrink-0 animate-slide-up z-20">
          <div className="p-3.5 rounded-2xl bg-[#16161c]/98 border border-white/20 backdrop-blur-2xl shadow-[0_16px_40px_rgba(0,0,0,0.85)] ring-1 ring-white/10 space-y-2.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-white" />
                <span className="text-xs font-bold text-white tracking-tight">Policy Guardrail Approval Required</span>
              </div>
              <span className="text-[9.5px] font-mono text-zinc-200 bg-white/10 border border-white/20 px-2 py-0.5 rounded font-semibold">
                {latestPolicyGate.risk_level || 'HIGH'} RISK
              </span>
            </div>

            <p className="text-xs text-zinc-300 leading-relaxed font-sans">
              {latestPolicyGate.reason ||
                `Action ${latestPolicyGate.action} on ${latestPolicyGate.service || 'checkout-service'} to baseline v${latestPolicyGate.target_version || '2.4.0'} requires operator approval.`}
            </p>

            <div className="flex items-center gap-2 pt-0.5">
              <button
                onClick={() => {
                  handleSendText(`Approve rollback to v${latestPolicyGate.target_version || '2.4.0'}`);
                }}
                disabled={isApproving || isCopilotThinking}
                className="flex-1 bg-white hover:bg-zinc-200 text-black text-xs py-2 rounded-lg font-semibold flex items-center justify-center gap-1.5 transition-all shadow-md active:scale-[0.98]"
              >
                <Check className="w-3.5 h-3.5 text-black" />
                <span>
                  {isApproving || isCopilotThinking
                    ? 'Executing Rollback...'
                    : `Approve Rollback to v${latestPolicyGate.target_version || '2.4.0'}`}
                </span>
              </button>
              <button
                onClick={() => {
                  handleSendText('Reject rollback');
                }}
                disabled={isApproving || isCopilotThinking}
                className="px-3.5 bg-[#141416] hover:bg-zinc-800 text-white border border-[#27272a] text-xs py-2 rounded-lg font-medium flex items-center justify-center gap-1.5 transition-all active:scale-[0.98]"
              >
                <X className="w-3.5 h-3.5 text-zinc-400" />
                <span>Reject</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 3. Bottom Chat Input with Ambient Shadow Blur */}
      <div className="p-3.5 bg-gradient-to-t from-[#09090c]/95 via-[#09090c]/80 to-transparent backdrop-blur-xl shrink-0 shadow-[0_-16px_36px_rgba(0,0,0,0.65)] border-t border-white/[0.06] relative z-10">
        {/* Quick action chips popover */}
        {showQuickActions && (
          <div className="mb-2 p-2 bg-[#16161a]/95 backdrop-blur-xl border border-white/10 rounded-xl shadow-2xl flex flex-wrap gap-1.5 animate-slide-fade">
            <button
              onClick={() => handleQuickAction('Investigate incident on checkout-service and diagnose root cause')}
              className="text-[11px] font-mono px-2.5 py-1 rounded-lg bg-[#1e1e24] hover:bg-zinc-800 text-white hover:text-zinc-200 transition-colors font-semibold border border-white/20"
            >
              Investigate Incident
            </button>
            <button
              onClick={() => handleQuickAction('Show database connection pool metrics and saturation')}
              className="text-[11px] font-mono px-2.5 py-1 rounded-lg bg-[#1e1e24] hover:bg-zinc-800 text-zinc-300 hover:text-white transition-colors border border-transparent hover:border-zinc-700"
            >
              Check DB Pool
            </button>
            <button
              onClick={() => handleQuickAction('Inspect recent 5xx error logs for checkout-service')}
              className="text-[11px] font-mono px-2.5 py-1 rounded-lg bg-[#1e1e24] hover:bg-zinc-800 text-zinc-300 hover:text-white transition-colors border border-transparent hover:border-zinc-700"
            >
              Inspect 5xx Logs
            </button>
            <button
              onClick={() => handleQuickAction('Explain the root cause and why v2.4.1 failed')}
              className="text-[11px] font-mono px-2.5 py-1 rounded-lg bg-[#1e1e24] hover:bg-zinc-800 text-zinc-300 hover:text-white transition-colors border border-transparent hover:border-zinc-700"
            >
              Explain Root Cause
            </button>
            <button
              onClick={() => handleQuickAction('execute get_metrics 4 times in parallel after triage test')}
              className="text-[11px] font-mono px-2.5 py-1 rounded-lg bg-[#1e1e24] hover:bg-zinc-800 text-zinc-200 hover:text-white transition-colors font-medium border border-white/10"
            >
              Run 4x Parallel Probes
            </button>
            <button
              onClick={() => handleQuickAction('Approve rollback to v2.4.0')}
              className="text-[11px] font-mono px-2.5 py-1 rounded-lg bg-[#1e1e24] hover:bg-zinc-800 text-white hover:text-zinc-200 transition-colors font-semibold border border-white/20"
            >
              Approve Rollback
            </button>
          </div>
        )}

        {/* Floating compact card container with deep ambient shadow blur */}
        <div className="relative bg-[#141418]/90 backdrop-blur-2xl border border-white/10 focus-within:border-white/25 rounded-2xl px-3.5 py-2.5 shadow-[0_12px_40px_rgba(0,0,0,0.9),0_0_24px_rgba(255,255,255,0.03)] transition-all flex flex-col gap-1">
          {/* Top text input area */}
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Ask Aegis, investigate incident, or instruct remediation..."
            rows={1}
            className="w-full bg-transparent text-xs text-white placeholder:text-zinc-500 resize-none focus:outline-none leading-normal py-1 max-h-20"
          />

          {/* Bottom controls row */}
          <div className="flex items-center justify-between pt-0.5">
            {/* Left side: (+) action trigger */}
            <button
              type="button"
              onClick={() => setShowQuickActions(!showQuickActions)}
              className="w-6 h-6 rounded-full border border-zinc-700 hover:border-zinc-500 text-zinc-400 hover:text-white flex items-center justify-center transition-colors"
              title="Quick actions & tools"
            >
              <Plus className="w-3 h-3" />
            </button>

            {/* Right side: Mic and Send buttons */}
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => alert('Voice input activated')}
                className="w-7 h-7 rounded-full text-zinc-400 hover:text-white hover:bg-zinc-800/60 flex items-center justify-center transition-colors"
                title="Voice input"
              >
                <Mic className="w-3.5 h-3.5" />
              </button>

              <button
                type="button"
                onClick={handleSend}
                disabled={!inputText.trim()}
                className={`w-7 h-7 rounded-xl flex items-center justify-center transition-all ${
                  inputText.trim()
                    ? 'bg-white text-black font-semibold shadow-md hover:bg-zinc-200 active:scale-95'
                    : 'bg-[#27272a] text-zinc-600 cursor-not-allowed'
                }`}
                title="Send message"
              >
                <ArrowUp className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
};
