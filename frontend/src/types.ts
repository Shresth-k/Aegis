export type NodeStatus = 'pending' | 'active' | 'completed' | 'failed' | 'waiting_approval' | 'blocked_on_approval';

export interface DAGNode {
  id: string;
  step: string;
  title: string;
  subtitle: string;
  iconType: 'zap' | 'database' | 'search' | 'cpu' | 'shield' | 'gear' | 'check';
  accentColor: 'emerald' | 'blue' | 'purple' | 'amber' | 'slate';
  x: number;
  y: number;
  status: NodeStatus;
  data?: any;
}

export interface TraceEvent {
  step: string;
  event_type: string;
  timestamp: string;
  data: any;
  incident_id?: string;
}

export interface TelemetryEvidence {
  service: string;
  current_version: string;
  previous_version?: string;
  recent_deployment?: boolean;
  metrics: {
    error_rate?: number;
    latency_p95_ms?: number;
    latency_ms?: number;
    requests_per_sec?: number;
    db_pool_active?: number;
    db_pool_max?: number;
    [key: string]: any;
  };
  error_logs: string[];
  dependencies: string[];
  dependency_health: Record<string, boolean>;
  // Convenience backward compatibility
  error_rate?: number;
  latency_p95_ms?: number;
  db_pool_active?: number;
}

export interface RetrievedRunbook {
  doc_id: string;
  title: string;
  content: string;
  score: number;
  source_type: 'runbook' | 'postmortem' | 'policy' | 'architecture';
}

export interface DiagnosisResult {
  root_cause: string;
  confidence: number;
  evidence_summary: string[];
  recommended_action: string;
  action_parameters: Record<string, any>;
  reasoning: string;
}

export interface PolicyEvaluation {
  action: string;
  risk_level: 'READ_ONLY' | 'LOW' | 'MEDIUM' | 'HIGH' | 'FORBIDDEN';
  decision: 'ALLOW' | 'REQUIRE_APPROVAL' | 'DENY';
  requires_approval: boolean;
  reason: string;
}

export interface RemediationResult {
  action: string;
  target_service: string;
  parameters: Record<string, any>;
  status: 'SUCCESS' | 'FAILED' | 'SKIPPED';
  executed_at?: string;
  message: string;
}

export interface VerificationResult {
  is_healthy: boolean;
  error_rate: number;
  latency_ms: number;
  service_version: string;
  status: 'SUCCESS' | 'FAILED';
  details: string;
}

export interface IncidentState {
  incident_id: string;
  service: string;
  severity: 'P1' | 'P2' | 'P3' | 'P4' | string;
  status: 'OPEN' | 'INVESTIGATING' | 'DIAGNOSED' | 'PENDING_APPROVAL' | 'REMEDIATING' | 'VERIFYING' | 'RESOLVED' | 'ESCALATED';
  title?: string;
  description?: string;
  evidence?: TelemetryEvidence;
  retrieved_runbooks?: RetrievedRunbook[];
  diagnosis?: DiagnosisResult;
  policy_evaluation?: PolicyEvaluation;
  policy_decision?: PolicyEvaluation;
  approval_granted?: boolean | null;
  approved_by?: string | null;
  approval_reason?: string | null;
  remediation?: RemediationResult;
  verification?: VerificationResult;
  trajectory_log?: any[];
  created_at?: string;
  updated_at?: string;
}

export interface ToolCall {
  id?: string;
  name: string;
  args: string | Record<string, any>;
  output?: any;
  status?: 'calling' | 'success' | 'failed';
  durationMs?: number;
  timestamp?: string;
}
