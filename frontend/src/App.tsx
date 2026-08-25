import React, { useEffect, useState } from 'react';
import { Header } from './components/Header';
import { StageOverview } from './components/StageOverview';
import { IncidentWorkspace } from './components/IncidentWorkspace';
import { InvestigationTrace } from './components/InvestigationTrace';
import { EvidenceViewer } from './components/EvidenceViewer';
import { HumanApprovalModal } from './components/HumanApprovalModal';
import { Incident, RecoveryRecommendation } from './types';
import { fetchCurrentIncident, approveRecovery, resetIncident } from './services/api';
import { AlertCircle, Film } from 'lucide-react';

export const App: React.FC = () => {
  const [incident, setIncident] = useState<Incident | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isInvestigating, setIsInvestigating] = useState(false);
  const [selectedRecommendation, setSelectedRecommendation] = useState<RecoveryRecommendation | null>(null);
  const [isApprovalOpen, setIsApprovalOpen] = useState(false);
  const [isProcessingApproval, setIsProcessingApproval] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchCurrentIncident();
      setIncident(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load stage telemetry');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleInvestigate = async () => {
    try {
      setIsInvestigating(true);
      // Initiate SSE streaming of trace steps
      const eventSource = new EventSource('/api/v1/incidents/stream-trace');
      
      eventSource.addEventListener('trace_step', (e) => {
        const stepData = JSON.parse(e.data);
        setIncident((prev) => {
          if (!prev) return prev;
          const existing = prev.tool_trace.filter((t) => t.step_number !== stepData.step_number);
          return {
            ...prev,
            tool_trace: [...existing, stepData].sort((a, b) => a.step_number - b.step_number),
          };
        });
      });

      eventSource.addEventListener('complete', () => {
        eventSource.close();
        setIsInvestigating(false);
        fetchCurrentIncident().then((data) => setIncident(data));
      });

      eventSource.onerror = () => {
        eventSource.close();
        setIsInvestigating(false);
      };
    } catch (err: any) {
      setIsInvestigating(false);
      setError(err.message);
    }
  };

  const handleOpenApproval = (recommendation: RecoveryRecommendation) => {
    setSelectedRecommendation(recommendation);
    setIsApprovalOpen(true);
  };

  const handleConfirmApproval = async (actionId: string, operatorName: string) => {
    try {
      setIsProcessingApproval(true);
      const updatedIncident = await approveRecovery(actionId, operatorName);
      setIncident(updatedIncident);
      setIsApprovalOpen(false);
    } catch (err: any) {
      setError(err.message || 'Failed to execute recovery');
    } finally {
      setIsProcessingApproval(false);
    }
  };

  const handleReset = async () => {
    try {
      const freshIncident = await resetIncident();
      setIncident(freshIncident);
    } catch (err: any) {
      setError(err.message);
    }
  };

  if (loading && !incident) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-[#07090e] text-slate-300 font-mono">
        <div className="flex flex-col items-center space-y-3">
          <Film className="h-8 w-8 text-cyan-400 animate-spin" />
          <p className="text-sm">Connecting to Stage A Observability Plane...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#07090e] text-slate-100 flex flex-col font-sans selection:bg-cyan-500 selection:text-black">
      <Header
        incident={incident}
        onReset={handleReset}
        onInvestigate={handleInvestigate}
        isInvestigating={isInvestigating}
      />

      {error && (
        <div className="bg-red-950/80 border-b border-red-800 px-6 py-2 text-xs font-mono text-red-200 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <AlertCircle className="h-4 w-4 text-red-400" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-white">✕</button>
        </div>
      )}

      <main className="flex-1 p-6 space-y-5 max-w-[1720px] mx-auto w-full">
        {incident && (
          <>
            {/* Stage & Robot Telemetry Bar */}
            <StageOverview stage={incident.stage_info} robot={incident.robot_telemetry} />

            {/* 2-Column Split: Operations Workspace & Agent Trace */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
              {/* Left Column (7 cols): Incident Workspace & Multi-Source Evidence */}
              <div className="lg:col-span-7 space-y-5">
                <IncidentWorkspace
                  incident={incident}
                  onOpenApproval={handleOpenApproval}
                />
                <EvidenceViewer incident={incident} />
              </div>

              {/* Right Column (5 cols): Live Investigation Audit Trace */}
              <div className="lg:col-span-5 sticky top-20">
                <InvestigationTrace
                  traces={incident.tool_trace}
                  isInvestigating={isInvestigating}
                />
              </div>
            </div>
          </>
        )}
      </main>

      {/* Safety Gate Approval Modal */}
      <HumanApprovalModal
        recommendation={selectedRecommendation}
        isOpen={isApprovalOpen}
        onClose={() => setIsApprovalOpen(false)}
        onConfirm={handleConfirmApproval}
        isProcessing={isProcessingApproval}
      />

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-[#0c1017] px-6 py-3.5 mt-10 text-xs font-mono text-slate-400">
        <div className="max-w-[1720px] mx-auto flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center space-x-2">
            <span className="font-semibold text-slate-300">CineOps Guardian</span>
            <span>•</span>
            <span>Agentic Cinema Hackathon (Grafana Labs Partner Track)</span>
            <span>•</span>
            <span>Apache-2.0</span>
          </div>
          <div className="flex items-center space-x-3 text-[11px] text-slate-400">
            <span>Runtime: <strong className="text-cyan-400">Gemini 3.7 Flash</strong></span>
            <span>•</span>
            <span>Grafana MCP: <strong className="text-amber-400">mcp-grafana</strong></span>
            <span>•</span>
            <span>GCP Project: <code className="text-slate-300">project-55fbcfd2-0ad6-4c99-a25</code></span>
          </div>
        </div>
      </footer>
    </div>
  );
};
