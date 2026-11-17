import React, { useState, useEffect, useCallback } from 'react';
import {
  Server,
  Database,
  Activity,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Play,
  Square,
  Radio,
  Layers,
  ExternalLink,
  ShieldCheck,
  RefreshCw,
  Cpu,
  HardDrive,
  GitBranch,
  ArrowRight
} from 'lucide-react';

export interface AcmeBuild {
  version: string;
  title: string;
  service: string;
  status: string;
  fault_type: string;
  description: string;
  needs_rollback: boolean;
  recommended_action: string;
  action_label: string;
  env_diff: Record<string, any>;
  target_incident_severity: string;
  is_active?: boolean;
}

export interface AcmeCloudStatus {
  service: string;
  current_version: string;
  is_healthy: boolean;
  error_rate: number;
  latency_p95_ms: number;
  requests_per_sec: number;
  db_pool_active: number;
  db_pool_max: number;
  traffic_running: boolean;
  services: Array<{
    name: string;
    role: string;
    port: number;
    version: string;
    healthy: boolean;
  }>;
  containers: Array<Record<string, any>>;
}

interface AcmeCloudConsoleProps {
  onSwitchToAegis: () => void;
  onDeploySuccess?: (version: string) => void;
}

export const AcmeCloudConsole: React.FC<AcmeCloudConsoleProps> = ({
  onSwitchToAegis,
  onDeploySuccess
}) => {
  const [builds, setBuilds] = useState<AcmeBuild[]>([]);
  const [status, setStatus] = useState<AcmeCloudStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [deployingVersion, setDeployingVersion] = useState<string | null>(null);
  const [trafficLoading, setTrafficLoading] = useState<boolean>(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const fetchBuildsAndStatus = useCallback(async () => {
    try {
      const [buildsRes, statusRes] = await Promise.all([
        fetch('/api/acmecloud/builds'),
        fetch('/api/acmecloud/status')
      ]);

      if (buildsRes.ok) {
        const buildsData = await buildsRes.json();
        if (Array.isArray(buildsData.builds)) {
          setBuilds(buildsData.builds);
        }
      }

      if (statusRes.ok) {
        const statusData = await statusRes.json();
        setStatus(statusData);
      }
    } catch (err) {
      console.warn('AcmeCloud API fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBuildsAndStatus();
    const interval = setInterval(fetchBuildsAndStatus, 3000);
    return () => clearInterval(interval);
  }, [fetchBuildsAndStatus]);

  const handleDeploy = async (version: string) => {
    setDeployingVersion(version);
    setActionMessage(null);
    try {
      const res = await fetch('/api/acmecloud/deploy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ service: 'checkout-service', version })
      });
      if (res.ok) {
        const data = await res.json();
        setActionMessage(`Deployed build v${version}: ${data.message || 'Updated.'}`);
        await fetchBuildsAndStatus();
        onDeploySuccess?.(version);
      }
    } catch (err) {
      setActionMessage(`Deployment error: ${err}`);
    } finally {
      setDeployingVersion(null);
    }
  };

  const handleToggleTraffic = async () => {
    setTrafficLoading(true);
    try {
      const targetState = !(status?.traffic_running);
      const res = await fetch('/api/acmecloud/traffic/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enable: targetState })
      });
      if (res.ok) {
        await fetchBuildsAndStatus();
      }
    } catch (err) {
      console.warn('Traffic toggle error:', err);
    } finally {
      setTrafficLoading(false);
    }
  };

  const activeBuild = builds.find((b) => b.is_active) || builds[0];
  const isHealthy = status?.is_healthy ?? true;
  const currentVer = status?.current_version || '2.4.0';

  return (
    <div className="flex-1 flex flex-col h-full bg-[#0a0b0e] text-zinc-200 overflow-y-auto font-sans select-none">
      {/* 1. Header Banner */}
      <div className="h-16 border-b border-[#1f2128] bg-[#0f1015] px-6 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-zinc-800 border border-zinc-700 flex items-center justify-center text-zinc-100 font-mono font-bold text-sm tracking-wider">
              AC
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold tracking-wide text-zinc-100 uppercase font-mono">
                  AcmeCloud Infrastructure Portal
                </span>
                <span className="text-[10px] bg-zinc-800 text-zinc-300 font-mono px-1.5 py-0.5 rounded border border-zinc-700">
                  Region: us-east-1a
                </span>
              </div>
              <p className="text-[11px] text-zinc-400 font-mono">
                Environment: production-cluster-01
              </p>
            </div>
          </div>

          <div className="h-4 w-[1px] bg-zinc-800 hidden md:block" />

          {/* Active Service Status Pill */}
          <div
            className={`hidden md:flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono border ${
              isHealthy
                ? 'bg-emerald-950/40 text-emerald-300 border-emerald-800/60'
                : 'bg-red-950/40 text-red-300 border-red-800/60'
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                isHealthy ? 'bg-emerald-400' : 'bg-red-400 animate-pulse'
              }`}
            />
            <span>checkout-service: v{currentVer}</span>
            <span className="text-[10px] uppercase font-bold tracking-wider opacity-80">
              [{isHealthy ? 'Nominal' : 'Fault Active'}]
            </span>
          </div>
        </div>

        {/* Action Button: Switch to Aegis SRE Copilot */}
        <div className="flex items-center gap-3">
          <button
            onClick={fetchBuildsAndStatus}
            disabled={loading}
            className="p-2 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition-all cursor-pointer"
            title="Refresh status"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>

          <button
            onClick={onSwitchToAegis}
            className="flex items-center gap-2 bg-zinc-100 hover:bg-white text-zinc-900 text-xs font-medium px-3.5 py-1.5 rounded-lg transition-all shadow-sm active:scale-95 cursor-pointer font-mono"
          >
            <span>Open Aegis SRE Copilot</span>
            <ArrowRight className="w-3.5 h-3.5 text-zinc-800" />
          </button>
        </div>
      </div>

      {/* Action Notification Banner */}
      {actionMessage && (
        <div className="bg-zinc-900/90 border-b border-zinc-800 px-6 py-2 flex items-center justify-between text-xs font-mono text-zinc-300">
          <div className="flex items-center gap-2">
            <Radio className="w-3.5 h-3.5 text-zinc-400 animate-pulse" />
            <span>{actionMessage}</span>
          </div>
          <button
            onClick={() => setActionMessage(null)}
            className="text-zinc-500 hover:text-zinc-300 text-[11px]"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* 2. Main Portal Grid */}
      <div className="flex-1 p-6 grid grid-cols-1 lg:grid-cols-12 gap-6 max-w-7xl mx-auto w-full">
        {/* Left Column: Services & Runtime (4 cols) */}
        <div className="lg:col-span-4 flex flex-col gap-5">
          {/* Services Manifest Card */}
          <div className="bg-[#121318] border border-[#22242e] rounded-xl p-4.5 flex flex-col gap-3.5">
            <div className="flex items-center justify-between border-b border-[#22242e] pb-3">
              <div className="flex items-center gap-2">
                <Server className="w-4 h-4 text-zinc-300" />
                <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-200 font-mono">
                  Managed Services
                </h3>
              </div>
              <span className="text-[11px] font-mono text-zinc-400">
                4 Active Containers
              </span>
            </div>

            <div className="flex flex-col gap-2.5">
              {(status?.services || [
                { name: 'checkout-service', role: 'Core API', port: 8001, version: currentVer, healthy: isHealthy },
                { name: 'postgres', role: 'Stateful DB', port: 5432, version: '17.0', healthy: true },
                { name: 'prometheus', role: 'Metrics TSDB', port: 9090, version: 'v3.5.0', healthy: true },
                { name: 'grafana', role: 'Dashboards', port: 3001, version: '12.1.1', healthy: true }
              ]).map((svc) => (
                <div
                  key={svc.name}
                  className="bg-[#17181f] border border-[#262835] rounded-lg p-2.5 flex items-center justify-between text-xs"
                >
                  <div className="flex items-center gap-2.5">
                    <span
                      className={`w-2 h-2 rounded-full ${
                        svc.healthy ? 'bg-emerald-400' : 'bg-red-400 animate-pulse'
                      }`}
                    />
                    <div>
                      <span className="font-mono font-medium text-zinc-200">
                        {svc.name}
                      </span>
                      <p className="text-[10px] text-zinc-400 font-mono">
                        {svc.role} | Port :{svc.port}
                      </p>
                    </div>
                  </div>
                  <span className="text-[11px] font-mono bg-[#0f1015] border border-[#282a38] text-zinc-300 px-2 py-0.5 rounded">
                    v{svc.version}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Real-time Telemetry Card */}
          <div className="bg-[#121318] border border-[#22242e] rounded-xl p-4.5 flex flex-col gap-3.5">
            <div className="flex items-center justify-between border-b border-[#22242e] pb-3">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-zinc-300" />
                <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-200 font-mono">
                  Live Telemetry
                </h3>
              </div>
              <span className="text-[10px] font-mono text-zinc-400 bg-zinc-800/80 px-1.5 py-0.5 rounded">
                Source: Prometheus
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2.5">
              <div className="bg-[#17181f] border border-[#262835] rounded-lg p-3 flex flex-col gap-1">
                <span className="text-[10px] text-zinc-400 font-mono uppercase">
                  Error Rate
                </span>
                <span
                  className={`text-lg font-bold font-mono ${
                    (status?.error_rate ?? 0) > 0.05 ? 'text-red-400' : 'text-emerald-400'
                  }`}
                >
                  {((status?.error_rate ?? 0) * 100).toFixed(1)}%
                </span>
                <div className="w-full bg-zinc-800 h-1 rounded-full overflow-hidden mt-1">
                  <div
                    className={`h-full ${
                      (status?.error_rate ?? 0) > 0.05 ? 'bg-red-400' : 'bg-emerald-400'
                    }`}
                    style={{ width: `${Math.min(100, (status?.error_rate ?? 0) * 100)}%` }}
                  />
                </div>
              </div>

              <div className="bg-[#17181f] border border-[#262835] rounded-lg p-3 flex flex-col gap-1">
                <span className="text-[10px] text-zinc-400 font-mono uppercase">
                  P95 Latency
                </span>
                <span
                  className={`text-lg font-bold font-mono ${
                    (status?.latency_p95_ms ?? 0) > 500 ? 'text-amber-400' : 'text-zinc-200'
                  }`}
                >
                  {(status?.latency_p95_ms ?? 42.5).toFixed(0)}ms
                </span>
                <span className="text-[10px] text-zinc-500 font-mono">
                  SLO target: &lt; 200ms
                </span>
              </div>

              <div className="bg-[#17181f] border border-[#262835] rounded-lg p-3 flex flex-col gap-1">
                <span className="text-[10px] text-zinc-400 font-mono uppercase">
                  DB Connections
                </span>
                <span className="text-lg font-bold font-mono text-zinc-200">
                  {status?.db_pool_active ?? 5}/{status?.db_pool_max ?? 50}
                </span>
                <span className="text-[10px] text-zinc-500 font-mono">
                  Active / Max limit
                </span>
              </div>

              <div className="bg-[#17181f] border border-[#262835] rounded-lg p-3 flex flex-col gap-1">
                <span className="text-[10px] text-zinc-400 font-mono uppercase">
                  Throughput
                </span>
                <span className="text-lg font-bold font-mono text-zinc-200">
                  {(status?.requests_per_sec ?? 120.0).toFixed(0)} rps
                </span>
                <span className="text-[10px] text-zinc-500 font-mono">
                  Synthetic traffic load
                </span>
              </div>
            </div>

            {/* Traffic Generator Controls */}
            <div className="bg-[#17181f] border border-[#262835] rounded-lg p-3 flex items-center justify-between mt-1">
              <div>
                <span className="text-xs font-mono font-medium text-zinc-200">
                  Continuous Traffic Loop
                </span>
                <p className="text-[10px] text-zinc-400 font-mono">
                  {status?.traffic_running
                    ? '120 req/s active load bursts'
                    : 'Load generation idle'}
                </p>
              </div>

              <button
                onClick={handleToggleTraffic}
                disabled={trafficLoading}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono transition-all cursor-pointer ${
                  status?.traffic_running
                    ? 'bg-amber-950/50 text-amber-300 border border-amber-800/60 hover:bg-amber-900/60'
                    : 'bg-zinc-800 text-zinc-200 border border-zinc-700 hover:bg-zinc-700'
                }`}
              >
                {status?.traffic_running ? (
                  <>
                    <Square className="w-3 h-3 text-amber-400" />
                    <span>Pause Traffic</span>
                  </>
                ) : (
                  <>
                    <Play className="w-3 h-3 text-zinc-300" />
                    <span>Start Traffic</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Center/Right Column: Deployment & Build Catalog (8 cols) */}
        <div className="lg:col-span-8 flex flex-col gap-5">
          <div className="bg-[#121318] border border-[#22242e] rounded-xl p-5 flex flex-col gap-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-[#22242e] pb-3 gap-2">
              <div>
                <div className="flex items-center gap-2">
                  <Layers className="w-4 h-4 text-zinc-300" />
                  <h2 className="text-sm font-semibold tracking-wide text-zinc-100 uppercase font-mono">
                    Build Catalog &amp; Scenario Simulator
                  </h2>
                </div>
                <p className="text-[11px] text-zinc-400 font-mono mt-0.5">
                  Select a build to deploy to checkout-service. Observe telemetry and trigger remediation in Aegis.
                </p>
              </div>

              {/* Restore Baseline Button */}
              <button
                onClick={() => handleDeploy('2.4.0')}
                disabled={deployingVersion !== null || currentVer === '2.4.0'}
                className="flex items-center gap-1.5 bg-emerald-950/40 hover:bg-emerald-900/50 text-emerald-300 border border-emerald-800/60 disabled:opacity-40 disabled:cursor-not-allowed text-xs font-mono px-3 py-1.5 rounded-lg transition-all shrink-0 cursor-pointer"
              >
                <RotateCcw className="w-3.5 h-3.5 text-emerald-400" />
                <span>Restore Baseline (v2.4.0)</span>
              </button>
            </div>

            {/* Build Cards List */}
            <div className="flex flex-col gap-3">
              {builds.map((build) => {
                const isActive = build.version === currentVer;
                const isDeploying = deployingVersion === build.version;

                return (
                  <div
                    key={build.version}
                    className={`rounded-xl border p-4 transition-all ${
                      isActive
                        ? 'bg-[#181a24] border-blue-500/60 shadow-sm'
                        : 'bg-[#15161d] border-[#252735] hover:border-zinc-700'
                    }`}
                  >
                    <div className="flex flex-col md:flex-row md:items-start justify-between gap-3">
                      <div className="flex flex-col gap-1.5 flex-1">
                        <div className="flex items-center gap-2.5 flex-wrap">
                          <span
                            className={`font-mono text-xs px-2.5 py-0.5 rounded-md font-bold border ${
                              build.status === 'STABLE'
                                ? 'bg-emerald-950/60 text-emerald-300 border-emerald-800/70'
                                : 'bg-red-950/60 text-red-300 border-red-800/70'
                            }`}
                          >
                            v{build.version}
                          </span>

                          <span className="font-semibold text-sm text-zinc-100">
                            {build.title}
                          </span>

                          {isActive && (
                            <span className="bg-blue-950/70 text-blue-300 border border-blue-700/60 text-[10px] font-mono px-2 py-0.5 rounded-full flex items-center gap-1">
                              <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-ping" />
                              Active Deployed
                            </span>
                          )}

                          <span className="text-[10px] font-mono text-zinc-400 bg-zinc-800 px-2 py-0.5 rounded">
                            {build.target_incident_severity}
                          </span>
                        </div>

                        <p className="text-xs text-zinc-400 leading-relaxed">
                          {build.description}
                        </p>

                        {/* Environment Diff & Remediation Details */}
                        <div className="flex flex-wrap items-center gap-3 pt-1 text-[11px] font-mono">
                          <div className="text-zinc-500">
                            Remediation expected:{' '}
                            <span className="text-zinc-300 underline underline-offset-2">
                              {build.action_label}
                            </span>
                          </div>

                          <span className="text-zinc-700">|</span>

                          <div className="text-zinc-500 flex items-center gap-1.5">
                            <span>Config diff:</span>
                            {Object.entries(build.env_diff).slice(0, 2).map(([k, v]) => (
                              <code
                                key={k}
                                className="bg-[#0e0f14] text-zinc-300 px-1.5 py-0.5 rounded border border-zinc-800 text-[10px]"
                              >
                                {k}={String(v)}
                              </code>
                            ))}
                          </div>
                        </div>
                      </div>

                      {/* Action Button */}
                      <div className="flex items-center gap-2 shrink-0 self-start md:self-center">
                        {isActive ? (
                          <div className="flex items-center gap-1.5 text-xs font-mono text-blue-400 px-3 py-1.5 bg-blue-950/30 rounded-lg border border-blue-900/40">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>Currently Active</span>
                          </div>
                        ) : (
                          <button
                            onClick={() => handleDeploy(build.version)}
                            disabled={deployingVersion !== null}
                            className={`flex items-center gap-1.5 text-xs font-mono px-3.5 py-1.5 rounded-lg border transition-all cursor-pointer active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed ${
                              build.status === 'STABLE'
                                ? 'bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border-zinc-700'
                                : 'bg-red-950/40 hover:bg-red-900/60 text-red-200 border-red-800/60'
                            }`}
                          >
                            {isDeploying ? (
                              <>
                                <RefreshCw className="w-3 h-3 animate-spin" />
                                <span>Deploying...</span>
                              </>
                            ) : (
                              <>
                                <Play className="w-3 h-3" />
                                <span>Deploy v{build.version}</span>
                              </>
                            )}
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Help Callout Banner */}
            <div className="bg-[#171822] border border-[#2a2c3d] rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-3 mt-2">
              <div className="flex items-center gap-3">
                <ShieldCheck className="w-5 h-5 text-blue-400 shrink-0" />
                <div>
                  <h4 className="text-xs font-semibold text-zinc-200 font-mono">
                    Ready to test autonomous incident resolution?
                  </h4>
                  <p className="text-[11px] text-zinc-400">
                    Deploy a faulty build above, then switch to Aegis SRE Copilot to watch the AI investigate, diagnose root cause, and heal the service.
                  </p>
                </div>
              </div>

              <button
                onClick={onSwitchToAegis}
                className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-mono px-3.5 py-2 rounded-lg transition-all shrink-0 cursor-pointer shadow-sm active:scale-95"
              >
                <span>Investigate in Aegis</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
