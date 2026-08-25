import React from 'react';
import { CheckCircle2, XCircle, Sparkles, ShieldCheck } from 'lucide-react';
import { Incident, RecoveryRecommendation } from '../types';

interface IncidentWorkspaceProps {
  incident: Incident;
  onOpenApproval: (recommendation: RecoveryRecommendation) => void;
}

export const IncidentWorkspace: React.FC<IncidentWorkspaceProps> = ({
  incident,
  onOpenApproval,
}) => {
  const isResolved = incident.status === 'resolved';

  return (
    <div className="space-y-4">
      {/* Incident Header Banner */}
      <div className={`rounded-xl border p-4.5 shadow-md ${isResolved ? 'bg-emerald-950/20 border-emerald-800/60' : 'bg-red-950/20 border-red-800/60'}`}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex items-center space-x-2.5">
              <span className={`rounded px-2.5 py-0.5 text-xs font-mono font-bold ${isResolved ? 'bg-emerald-900 text-emerald-300' : 'bg-red-900 text-red-300 animate-pulse'}`}>
                {isResolved ? 'RESOLVED' : incident.severity}
              </span>
              <span className="text-xs font-mono text-slate-400">
                #{incident.incident_id}
              </span>
            </div>
            <h2 className="text-base font-bold text-white mt-1.5 flex items-center gap-2">
              {incident.title}
            </h2>
            <p className="text-xs text-slate-300 mt-1 max-w-3xl leading-relaxed">
              {isResolved
                ? incident.resolution_summary
                : 'Robotic Camera Dolly Alpha experienced severe navigation oscillation and frame delivery degradation during Scene 42 Take 3 near stage lighting stand C-03.'}
            </p>
          </div>

          {/* Production Impact Summary */}
          <div className="rounded-lg bg-slate-900/90 border border-slate-800 p-3 text-xs font-mono space-y-1.5 shrink-0">
            <div className="text-[11px] text-slate-400 font-semibold border-b border-slate-800 pb-1">
              ESTIMATED PRODUCTION IMPACT
            </div>
            <div className="flex items-center space-x-4">
              <div>
                <span className="text-slate-400">Take at Risk:</span>{' '}
                <span className={`font-bold ${isResolved ? 'text-emerald-400' : 'text-red-400'}`}>
                  {isResolved ? 'SAVED (Take 3)' : 'YES (Scene 42 Take 3)'}
                </span>
              </div>
              <div>
                <span className="text-slate-400">Delay:</span>{' '}
                <span className="font-bold text-amber-400">
                  {isResolved ? '4 mins' : `${incident.production_impact.estimated_delay_minutes} mins`}
                </span>
              </div>
              <div>
                <span className="text-slate-400">Burn Rate:</span>{' '}
                <span className="font-bold text-slate-200">
                  ${incident.production_impact.financial_burn_rate_per_hour_usd.toLocaleString()}/hr
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Ranked Hypotheses Cards */}
      <div className="rounded-xl border border-slate-800 bg-[#0c1017] p-4.5 shadow-md">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-3.5">
          <div className="flex items-center space-x-2">
            <Sparkles className="h-4 w-4 text-cyan-400" />
            <h3 className="text-sm font-semibold text-white">Ranked Root-Cause Hypotheses (Gemini 3.7 Flash)</h3>
          </div>
          <span className="text-xs font-mono text-slate-400">Thinking Level: HIGH</span>
        </div>

        <div className="space-y-3">
          {incident.hypotheses.map((hyp) => {
            const isSupported = hyp.status === 'supported';

            return (
              <div
                key={hyp.id}
                className={`rounded-lg border p-3.5 text-xs font-mono ${isSupported ? 'bg-cyan-950/20 border-cyan-700/60' : 'bg-slate-900/40 border-slate-800/80 opacity-75'}`}
              >
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div className="flex items-start space-x-2.5">
                    <span className={`flex h-5 w-5 items-center justify-center rounded-full text-[11px] font-bold ${isSupported ? 'bg-cyan-500 text-black' : 'bg-slate-800 text-slate-400'}`}>
                      {hyp.rank}
                    </span>
                    <div>
                      <h4 className="font-semibold text-sm text-white">{hyp.title}</h4>
                      <p className="text-slate-300 text-[11.5px] mt-0.5 leading-relaxed">{hyp.rationale}</p>
                    </div>
                  </div>

                  <div className="text-right shrink-0">
                    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-bold ${isSupported ? 'bg-cyan-900/80 text-cyan-300 border border-cyan-600' : 'bg-slate-800 text-slate-400'}`}>
                      {(hyp.confidence * 100).toFixed(0)}% Confidence
                    </span>
                    <div className="text-[10px] text-slate-400 uppercase mt-1">
                      Status: <strong className={isSupported ? 'text-emerald-400' : 'text-red-400'}>{hyp.status}</strong>
                    </div>
                  </div>
                </div>

                {/* Supporting & Conflicting Evidence Checklists */}
                <div className="mt-2.5 pt-2.5 border-t border-slate-800/70 grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px]">
                  {hyp.supporting_evidence.length > 0 && (
                    <div>
                      <div className="text-emerald-400 font-semibold mb-1 flex items-center gap-1">
                        <CheckCircle2 className="h-3 w-3" /> Supporting Evidence:
                      </div>
                      <ul className="space-y-0.5 list-disc list-inside text-slate-300">
                        {hyp.supporting_evidence.map((ev, idx) => (
                          <li key={idx}>{ev}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {hyp.conflicting_evidence.length > 0 && (
                    <div>
                      <div className="text-red-400 font-semibold mb-1 flex items-center gap-1">
                        <XCircle className="h-3 w-3" /> Conflicting Evidence (Ruled Out):
                      </div>
                      <ul className="space-y-0.5 list-disc list-inside text-slate-400">
                        {hyp.conflicting_evidence.map((ev, idx) => (
                          <li key={idx}>{ev}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Recovery Action Plan */}
      <div className="rounded-xl border border-slate-800 bg-[#0c1017] p-4.5 shadow-md">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-3.5">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
            <h3 className="text-sm font-semibold text-white">Actionable Recovery Plan (Human Safety Gate)</h3>
          </div>
          <span className="rounded bg-amber-950/80 px-2 py-0.5 text-[11px] font-mono text-amber-300 border border-amber-800/60">
            REQUIRES HUMAN AUTHORIZATION
          </span>
        </div>

        {incident.recommendations.map((rec) => {
          const isExecuted = rec.approval_status === 'executed';

          return (
            <div key={rec.action_id} className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 text-xs font-mono space-y-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="rounded bg-emerald-950 px-2 py-0.5 text-emerald-400 font-bold border border-emerald-800">
                      RECOMMENDED ACTION
                    </span>
                    <span className="text-slate-400">Risk: <strong className="text-emerald-400 uppercase">{rec.risk_level}</strong></span>
                  </div>
                  <h4 className="text-sm font-bold text-white mt-1.5">{rec.title}</h4>
                  <p className="text-slate-300 text-[11.5px] mt-1 leading-relaxed">{rec.action_description}</p>
                </div>

                <div className="shrink-0">
                  {isExecuted ? (
                    <span className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-900/80 border border-emerald-600 px-3.5 py-2 text-xs font-bold text-emerald-200">
                      <CheckCircle2 className="h-4 w-4 text-emerald-300" />
                      EXECUTED & VERIFIED
                    </span>
                  ) : (
                    <button
                      onClick={() => onOpenApproval(rec)}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-2 text-xs font-bold text-white shadow-lg shadow-emerald-600/20 hover:bg-emerald-500 transition"
                    >
                      <ShieldCheck className="h-4 w-4" />
                      <span>Review & Authorize Action</span>
                    </button>
                  )}
                </div>
              </div>

              {/* Expected Effect & Rollback */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2.5 border-t border-slate-800 text-[11px]">
                <div className="rounded bg-[#07090e] p-2.5 border border-slate-800/80">
                  <div className="text-cyan-400 font-semibold mb-1">Expected Effect:</div>
                  <p className="text-slate-300">{rec.expected_effect}</p>
                </div>
                <div className="rounded bg-[#07090e] p-2.5 border border-slate-800/80">
                  <div className="text-amber-400 font-semibold mb-1">Rollback Procedure:</div>
                  <p className="text-slate-300">{rec.rollback_instructions}</p>
                </div>
              </div>

              {/* Success Criteria */}
              <div>
                <div className="text-slate-300 font-semibold text-[11px] mb-1.5">Verification Criteria:</div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-[10.5px]">
                  {rec.success_criteria.map((crit, idx) => (
                    <div key={idx} className="flex items-center space-x-1.5 text-slate-300 bg-[#07090e] px-2.5 py-1 rounded border border-slate-800/60">
                      <CheckCircle2 className={`h-3 w-3 shrink-0 ${isExecuted ? 'text-emerald-400' : 'text-slate-500'}`} />
                      <span>{crit}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
