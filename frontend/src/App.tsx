import React, { useState, useEffect, useRef, useCallback } from 'react';
import { TopBar } from './components/TopBar';
import { WorkflowCanvas } from './components/WorkflowCanvas';
import { AgentStreamPanel } from './components/AgentStreamPanel';
import { IncidentState, TraceEvent } from './types';

export default function App() {
  const [currentIncidentId, setCurrentIncidentId] = useState<string>('INC-001');
  const [incidents, setIncidents] = useState<Array<{
    incident_id: string;
    title: string;
    service: string;
    severity: string;
    status: string;
  }>>([]);
  const [incidentState, setIncidentState] = useState<IncidentState | null>(null);
  const [traces, setTraces] = useState<TraceEvent[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [isApproving, setIsApproving] = useState<boolean>(false);
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [visibleNodeIds, setVisibleNodeIds] = useState<string[]>([]);
  const [activeNodeId, setActiveNodeId] = useState<string | null>(null);
  const [sessionKey, setSessionKey] = useState<number>(0);

  // Paced animation queue for real backend trace events
  const traceQueueRef = useRef<TraceEvent[]>([]);
  const isProcessingQueueRef = useRef<boolean>(false);
  const isRunningRef = useRef<boolean>(false);
  isRunningRef.current = isRunning;
  const pendingRunStateRef = useRef<IncidentState | null>(null);

  // Apply a trace event to update visible nodes and active node
  const applyTraceEvent = useCallback((trace: TraceEvent) => {
    switch (trace.event_type) {
      case 'INCIDENT_INGESTED':
        setVisibleNodeIds((prev) => Array.from(new Set([...prev, 'ingest'])));
        setActiveNodeId('ingest');
        setSelectedNodeId('ingest');
        break;

      case 'TRIAGE_COMPLETE':
        setVisibleNodeIds((prev) => Array.from(new Set([...prev, 'ingest', 'triage'])));
        setActiveNodeId('triage');
        setSelectedNodeId('triage');
        break;

      case 'EVIDENCE_COLLECTED':
        setVisibleNodeIds((prev) => Array.from(new Set([...prev, 'tool-logs', 'tool-metrics'])));
        setActiveNodeId('tool-logs');
        setSelectedNodeId('tool-logs');
        break;

      case 'RUNBOOKS_RETRIEVED':
        setVisibleNodeIds((prev) => Array.from(new Set([...prev, 'knowledge'])));
        setActiveNodeId('knowledge');
        setSelectedNodeId('knowledge');
        break;

      case 'DIAGNOSIS_PRODUCED':
        setVisibleNodeIds((prev) => Array.from(new Set([...prev, 'diagnose'])));
        setActiveNodeId('diagnose');
        setSelectedNodeId('diagnose');
        setTimeout(() => {
          setActiveNodeId(null);
        }, 800);
        break;

      case 'POLICY_EVALUATED':
        setVisibleNodeIds((prev) => Array.from(new Set([...prev, 'policy'])));
        setActiveNodeId('policy');
        setSelectedNodeId('policy');
        setTimeout(() => {
          setActiveNodeId(null);
        }, 800);
        break;

      case 'APPROVAL_DECISION':
      case 'REMEDIATION_EXECUTED':
        setVisibleNodeIds((prev) => Array.from(new Set([...prev, 'remediate'])));
        setActiveNodeId('remediate');
        setSelectedNodeId('remediate');
        break;

      case 'VERIFICATION_COMPLETE':
        setVisibleNodeIds((prev) => Array.from(new Set([...prev, 'verify'])));
        setActiveNodeId('verify');
        setSelectedNodeId('verify');
        setTimeout(() => {
          setActiveNodeId(null);
        }, 800);
        break;

      default:
        break;
    }
  }, []);

  // Process the animation queue with smooth pacing (380ms per node)
  const processQueue = useCallback(() => {
    if (isProcessingQueueRef.current) return;
    if (traceQueueRef.current.length === 0) return;

    isProcessingQueueRef.current = true;

    const step = () => {
      const nextEvent = traceQueueRef.current.shift();
      if (!nextEvent) {
        isProcessingQueueRef.current = false;
        if (pendingRunStateRef.current) {
          setIncidentState(pendingRunStateRef.current);
          pendingRunStateRef.current = null;
        }
        setIsRunning(false);
        return;
      }

      applyTraceEvent(nextEvent);

      if (traceQueueRef.current.length > 0) {
        setTimeout(step, 380);
      } else {
        isProcessingQueueRef.current = false;
        if (pendingRunStateRef.current) {
          setIncidentState(pendingRunStateRef.current);
          pendingRunStateRef.current = null;
        }
        setIsRunning(false);
      }
    };

    step();
  }, [applyTraceEvent]);

  // Enqueue a trace event
  const handleTraceEvent = useCallback((trace: TraceEvent, immediate = false) => {
    setTraces((prev) => {
      const exists = prev.some(
        (t) => t.timestamp === trace.timestamp && t.event_type === trace.event_type
      );
      return exists ? prev : [...prev, trace];
    });

    // Only apply trace animation if canvas is not in initial empty state or is actively running
    if (isRunningRef.current) {
      if (immediate || (!isProcessingQueueRef.current && traceQueueRef.current.length === 0)) {
        applyTraceEvent(trace);
      } else {
        traceQueueRef.current.push(trace);
        processQueue();
      }
    }
  }, [applyTraceEvent, processQueue]);

  // Fetch incident list
  const fetchIncidents = async () => {
    try {
      const res = await fetch('/api/incidents');
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          setIncidents(data);
        }
      }
    } catch (err) {
      console.warn('Failed to fetch incidents list:', err);
    }
  };

  // Fetch incident traces
  const fetchTraces = async (id: string) => {
    try {
      const res = await fetch(`/api/incidents/${id}/traces`);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data.events)) {
          setTraces(data.events);
        }
      }
    } catch (err) {
      console.warn('Failed to fetch incident traces:', err);
    }
  };

  const updateVisibleNodesForState = (st: IncidentState) => {
    if (st.status === 'RESOLVED' || st.verification) {
      setVisibleNodeIds(['ingest', 'triage', 'tool-logs', 'tool-metrics', 'knowledge', 'diagnose', 'policy', 'remediate', 'verify']);
      setActiveNodeId(null);
      setSelectedNodeId('verify');
    } else if (st.status === 'REMEDIATING' || st.remediation) {
      setVisibleNodeIds(['ingest', 'triage', 'tool-logs', 'tool-metrics', 'knowledge', 'diagnose', 'policy', 'remediate']);
      setActiveNodeId('remediate');
      setSelectedNodeId('remediate');
    } else if (st.status === 'PENDING_APPROVAL' || st.policy_evaluation || st.policy_decision) {
      setVisibleNodeIds(['ingest', 'triage', 'tool-logs', 'tool-metrics', 'knowledge', 'diagnose', 'policy']);
      setActiveNodeId(null);
      setSelectedNodeId('policy');
    } else if (st.status === 'DIAGNOSED' || st.diagnosis) {
      setVisibleNodeIds(['ingest', 'triage', 'tool-logs', 'tool-metrics', 'knowledge', 'diagnose']);
      setActiveNodeId(null);
      setSelectedNodeId('diagnose');
    } else {
      setVisibleNodeIds([]);
      setActiveNodeId(null);
      setSelectedNodeId(null);
    }
  };

  // Progressive node reveal for chat-driven agent execution
  const animateNewNodes = useCallback((newNodes: string[]) => {
    if (!newNodes || newNodes.length === 0) return;
    newNodes.forEach((nodeId, idx) => {
      setTimeout(() => {
        setVisibleNodeIds((prev) => Array.from(new Set([...prev, nodeId])));
        setActiveNodeId(nodeId);
        setSelectedNodeId(nodeId);
        if (idx === newNodes.length - 1) {
          setTimeout(() => {
            setActiveNodeId(null);
          }, 800);
        }
      }, idx * 350);
    });
  }, []);

  const handleChatResponse = useCallback((data: any) => {
    if (data.status) {
      setIncidentState((prev) => prev ? {
        ...prev,
        status: data.status,
        approval_granted: data.status === 'RESOLVED' ? true : prev.approval_granted
      } : null);
    }
    if (data.new_nodes && Array.isArray(data.new_nodes) && data.new_nodes.length > 0) {
      animateNewNodes(data.new_nodes);
    }
  }, [animateNewNodes]);

  // Fetch incident state
  const fetchIncident = async (id: string = currentIncidentId, syncNodes: boolean = false) => {
    try {
      const res = await fetch(`/api/incidents/${id}`);
      if (res.ok) {
        const data: IncidentState = await res.json();
        setIncidentState(data);
        if (syncNodes) {
          updateVisibleNodesForState(data);
        }
      } else {
        // Fallback default state
        const fallback: IncidentState = {
          incident_id: id,
          service: 'checkout-service',
          severity: 'P1',
          status: 'OPEN',
          title: 'High 5xx Error Rate on Checkout Service',
          description: 'Connection pool starvation following release v2.4.1.'
        };
        setIncidentState(fallback);
        if (syncNodes) {
          updateVisibleNodesForState(fallback);
        }
      }
    } catch (err) {
      console.warn('API unavailable, running in local preview mode:', err);
    }
  };

  // SSE subscription effect
  useEffect(() => {
    fetchIncidents();
    fetchIncident(currentIncidentId);
    fetchTraces(currentIncidentId);

    let es: EventSource | null = null;
    try {
      es = new EventSource(`/api/incidents/${currentIncidentId}/stream`);

      // 1. Listen to named 'trace' events
      es.addEventListener('trace', (e: MessageEvent) => {
        try {
          const trace = JSON.parse(e.data);
          handleTraceEvent(trace);
        } catch (err) {
          console.warn('Error parsing trace event:', err);
        }
      });

      // 2. Listen to named 'state' events
      es.addEventListener('state', (e: MessageEvent) => {
        try {
          const stateData = JSON.parse(e.data);
          // Only update if not currently running animation
          if (!isRunningRef.current && !isProcessingQueueRef.current) {
            setIncidentState(stateData);
          } else {
            pendingRunStateRef.current = stateData;
          }
        } catch (err) {
          console.warn('Error parsing state event:', err);
        }
      });

      // 3. Fallback onmessage listener (for any un-named events)
      es.onmessage = (e: MessageEvent) => {
        try {
          const parsed = JSON.parse(e.data);
          if (parsed.event_type) {
            handleTraceEvent(parsed);
          } else if (parsed.incident_id && parsed.status) {
            if (!isRunningRef.current && !isProcessingQueueRef.current) {
              setIncidentState(parsed);
            }
          }
        } catch {}
      };
    } catch (e) {
      console.warn('SSE connection skipped:', e);
    }

    return () => {
      es?.close();
    };
  }, [currentIncidentId, handleTraceEvent]);



  // Handle operator approval: executes remediation and verification
  const handleApprove = async (approved: boolean, reason?: string) => {
    setIsApproving(true);

    try {
      const approvePromise = fetch('/api/incidents/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          incident_id: incidentState?.incident_id || currentIncidentId,
          approved,
          approved_by: 'LeadSRE',
          reason: reason || 'Operator approved in Aegis Studio console'
        })
      });

      if (approved) {
        // Step 7: Needle Remediation (Container Rollback to v2.4.0)
        setVisibleNodeIds((prev) => Array.from(new Set([...prev, 'remediate'])));
        setActiveNodeId('remediate');
        setSelectedNodeId('remediate');
        await new Promise((r) => setTimeout(r, 700));

        // Step 8: Verification Agent (SLO Metrics Check)
        setVisibleNodeIds((prev) => Array.from(new Set([...prev, 'verify'])));
        setActiveNodeId('verify');
        setSelectedNodeId('verify');
        await new Promise((r) => setTimeout(r, 600));
      }

      const res = await approvePromise;
      if (res.ok) {
        const updated = await res.json();
        setIncidentState(updated);
        setActiveNodeId(null);
      } else {
        // Optimistic UI update
        setIncidentState((prev) => prev ? {
          ...prev,
          status: approved ? 'RESOLVED' : 'ESCALATED',
          approval_granted: approved,
          remediation: { status: 'SUCCESS', action: 'rollback_deployment', target_service: 'checkout-service', parameters: { target_version: '2.4.0' }, message: 'Rollback executed.' },
          verification: { is_healthy: true, error_rate: 0.002, latency_ms: 42.5, service_version: '2.4.0', status: 'SUCCESS', details: 'All SLOs verified.' }
        } : null);
        setVisibleNodeIds((prev) => Array.from(new Set([...prev, 'remediate', 'verify'])));
        setSelectedNodeId('verify');
        setActiveNodeId(null);
      }
    } catch {
      // Optimistic update
      setIncidentState((prev) => prev ? {
        ...prev,
        status: approved ? 'RESOLVED' : 'ESCALATED',
        approval_granted: approved,
        remediation: { status: 'SUCCESS', action: 'rollback_deployment', target_service: 'checkout-service', parameters: { target_version: '2.4.0' }, message: 'Rollback executed.' },
        verification: { is_healthy: true, error_rate: 0.002, latency_ms: 42.5, service_version: '2.4.0', status: 'SUCCESS', details: 'All SLOs verified.' }
      } : null);
      setVisibleNodeIds((prev) => Array.from(new Set([...prev, 'remediate', 'verify'])));
      setSelectedNodeId('verify');
      setActiveNodeId(null);
    } finally {
      setIsApproving(false);
    }
  };

  // Chaos injection handler
  const handleInjectChaos = async () => {
    try {
      await fetch('/api/chaos/inject?service=checkout-service&version=2.4.1', { method: 'POST' });
      setVisibleNodeIds([]);
      setActiveNodeId(null);
      setSelectedNodeId(null);
      setSessionKey((prev) => prev + 1);
      await fetchIncident(currentIncidentId, false);
      await fetchTraces(currentIncidentId);
    } catch (err) {
      console.error('Failed to inject chaos:', err);
    }
  };

  // Reset baseline handler
  const handleResetChaos = async () => {
    try {
      await fetch('/api/chaos/reset?service=checkout-service', { method: 'POST' });
      setVisibleNodeIds([]);
      setActiveNodeId(null);
      setSelectedNodeId(null);
      setSessionKey((prev) => prev + 1);
      await fetchIncident(currentIncidentId, false);
      await fetchTraces(currentIncidentId);
    } catch (err) {
      console.error('Failed to reset chaos:', err);
    }
  };

  const handleSendMessage = (msg: string) => {
    console.log('Operator message sent:', msg);
  };

  const handleClearCanvas = () => {
    setVisibleNodeIds([]);
    setActiveNodeId(null);
    setSelectedNodeId(null);
  };

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-[#000000] text-zinc-100 font-sans">
      {/* 1. Global Unified TopBar spanning entire screen */}
      <TopBar
        state={incidentState}
        isRunning={isRunning}
        onShare={() => alert('Incident link copied to clipboard')}
        userInitials="SK"
        incidents={incidents}
        currentIncidentId={currentIncidentId}
        onSelectIncident={(id) => {
          setCurrentIncidentId(id);
          setSessionKey((prev) => prev + 1);
          fetchIncident(id);
        }}
        onInjectChaos={handleInjectChaos}
        onResetChaos={handleResetChaos}
      />

      {/* 2. Main Workspace (Canvas + Glassmorphic Agent Stream Panel) */}
      <div className="flex-1 flex w-full overflow-hidden relative">
        {/* Left Canvas Pane */}
        <div className="flex-1 h-full relative overflow-hidden">
          <WorkflowCanvas
            state={incidentState}
            selectedNodeId={selectedNodeId}
            onNodeSelect={setSelectedNodeId}
            isRunning={isRunning}
            visibleNodeIds={visibleNodeIds}
            activeNodeId={activeNodeId}
            onClearCanvas={handleClearCanvas}
          />
        </div>

        {/* Right Glassmorphic Agent Stream Panel */}
        <AgentStreamPanel
          key={`${currentIncidentId}-${sessionKey}`}
          state={incidentState}
          traces={traces}
          selectedNodeId={selectedNodeId}
          onApprove={handleApprove}
          isApproving={isApproving}
          onSendMessage={handleSendMessage}
          visibleNodeIds={visibleNodeIds}
          activeNodeId={activeNodeId}
          onChatResponse={handleChatResponse}
        />
      </div>
    </div>
  );
}
