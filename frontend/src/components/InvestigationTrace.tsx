import React, { useState } from 'react';
import { Terminal, Database, FileCode, Sparkles, CheckCircle2, ChevronRight, ChevronDown, Clock, Shield } from 'lucide-react';
import { ToolTraceEntry } from '../types';

interface InvestigationTraceProps {
  traces: ToolTraceEntry[];
  isInvestigating: boolean;
}

export const InvestigationTrace: React.FC<InvestigationTraceProps> = ({ traces, isInvestigating }) => {
  const [expandedSteps, setExpandedSteps] = useState<Record<number, boolean>>({});

  const toggleStep = (step: number) => {
    setExpandedSteps((prev) => ({ ...prev, [step]: !prev[step] }));
  };

  const getToolIcon = (type: ToolTraceEntry['tool_type']) => {
    switch (type) {
      case 'grafana_mcp':
        return <Terminal className="h-3.5 w-3.5 text-amber-400" />;
      case 'bigquery':
        return <Database className="h-3.5 w-3.5 text-blue-400" />;
      case 'mcap_inspector':
        return <FileCode className="h-3.5 w-3.5 text-purple-400" />;
      case 'gemini_reasoner':
        return <Sparkles className="h-3.5 w-3.5 text-cyan-400" />;
      case 'system':
      default:
        return <Shield className="h-3.5 w-3.5 text-emerald-400" />;
    }
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-[#0c1017] p-4.5 flex flex-col h-full shadow-md">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-3">
        <div className="flex items-center space-x-2">
          <Terminal className="h-4 w-4 text-cyan-400" />
          <h3 className="text-sm font-semibold text-white">Agent Investigation Trace</h3>
        </div>
        <div className="flex items-center space-x-2">
          {isInvestigating ? (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-cyan-950/80 border border-cyan-800/60 px-2 py-0.5 text-[11px] font-mono text-cyan-300 animate-pulse">
              <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-ping" />
              INVESTIGATING — {traces.length} TOOL CALL{traces.length === 1 ? '' : 'S'}
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-900 border border-slate-800 px-2 py-0.5 text-[11px] font-mono text-slate-400">
              <CheckCircle2 className="h-3 w-3 text-emerald-400" />
              {traces.length} STEPS AUDITED
            </span>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2 pr-1 text-xs font-mono max-h-[520px]">
        {traces.map((trace) => {
          const isExpanded = !!expandedSteps[trace.step_number];

          return (
            <div
              key={trace.step_number}
              className="rounded-lg border border-slate-800/90 bg-slate-900/50 p-2.5 transition hover:border-slate-700"
            >
              <div
                className="flex items-start justify-between cursor-pointer gap-2"
                onClick={() => toggleStep(trace.step_number)}
              >
                <div className="flex items-start space-x-2.5 flex-1">
                  <div className="mt-0.5 flex h-5 w-5 items-center justify-center rounded bg-slate-800/90 border border-slate-700/60">
                    {getToolIcon(trace.tool_type)}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center space-x-2">
                      <span className="text-[10px] text-cyan-400 font-bold">
                        STEP {trace.step_number}
                      </span>
                      <span className="text-slate-500">•</span>
                      <span className="font-semibold text-slate-200">
                        {trace.step_name}
                      </span>
                    </div>
                    <p className="text-slate-300 text-[11.5px] mt-0.5 leading-snug">
                      {trace.action_summary}
                    </p>
                  </div>
                </div>

                <div className="flex items-center space-x-2 text-[10px] text-slate-400 shrink-0">
                  <span className="flex items-center gap-0.5">
                    <Clock className="h-3 w-3" /> {trace.duration_ms}ms
                  </span>
                  {isExpanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                </div>
              </div>

              {/* Output Summary */}
              <div className="mt-2 rounded bg-[#070a0f] border border-slate-800/60 px-2.5 py-1.5 text-[11px] text-slate-300">
                <span className="text-cyan-400 font-bold mr-1.5">EVIDENCE:</span>
                {trace.tool_output_summary}
              </div>

              {/* Collapsible Safe Tool Input / Output Payload */}
              {isExpanded && (
                <div className="mt-2 space-y-1.5 pt-2 border-t border-slate-800/60 text-[10.5px]">
                  <div>
                    <span className="text-slate-500 font-semibold">TOOL:</span>{' '}
                    <code className="text-amber-300">{trace.tool_name}</code>
                  </div>
                  <div>
                    <span className="text-slate-500 font-semibold">PARAMETERS:</span>
                    <pre className="mt-1 rounded bg-[#05070a] p-2 text-slate-300 overflow-x-auto border border-slate-800/40">
                      {JSON.stringify(trace.tool_input_safe, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
