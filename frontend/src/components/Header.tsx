import React from 'react';
import { Film, Clapperboard, RotateCcw, Activity } from 'lucide-react';
import { Incident } from '../types';

interface HeaderProps {
  incident: Incident | null;
  onReset: () => void;
  onInvestigate: () => void;
  isInvestigating: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  incident,
  onReset,
  onInvestigate,
  isInvestigating,
}) => {
  const isResolved = incident?.status === 'resolved';

  return (
    <header className="border-b border-slate-800 bg-[#0c1017] px-6 py-3.5 sticky top-0 z-40">
      <div className="flex flex-wrap items-center justify-between gap-4">
        {/* Brand & Stage Identity */}
        <div className="flex items-center space-x-3.5">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-500/20 to-blue-600/30 border border-cyan-500/40 text-cyan-400">
            <Film className="h-5 w-5 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center space-x-2.5">
              <h1 className="text-lg font-bold tracking-tight text-white flex items-center gap-1.5">
                CineOps <span className="text-cyan-400">Guardian</span>
              </h1>
              <span className="rounded bg-cyan-950/80 px-2 py-0.5 text-[11px] font-mono text-cyan-300 border border-cyan-800/60">
                v2.3.0
              </span>
              <span className="rounded bg-slate-800/80 px-2 py-0.5 text-[11px] font-mono text-slate-300 border border-slate-700">
                Grafana Labs Track
              </span>
            </div>
            <p className="text-xs text-slate-400 font-mono">
              Stage A — Virtual Production Volume & Robotic Camera Fleet
            </p>
          </div>
        </div>

        {/* Live Take Status Bar */}
        <div className="flex items-center space-x-3 text-xs font-mono">
          <div className="flex items-center space-x-2 rounded-md bg-slate-900/90 border border-slate-800 px-3 py-1.5">
            <Clapperboard className="h-3.5 w-3.5 text-amber-400" />
            <span className="text-slate-400">SCENE</span>
            <span className="font-semibold text-white">{incident?.stage_info.current_scene || 'Scene 42'}</span>
            <span className="text-slate-600">|</span>
            <span className="text-slate-400">TAKE</span>
            <span className="font-semibold text-amber-400">{incident?.stage_info.current_take || 'Take 3'}</span>
          </div>

          <div className="flex items-center space-x-2 rounded-md bg-slate-900/90 border border-slate-800 px-3 py-1.5">
            <span className="text-slate-400">TC</span>
            <span className="font-mono text-cyan-300">{incident?.stage_info.timecode || '14:22:08:19'}</span>
          </div>

          <div className="flex items-center space-x-2 rounded-md bg-slate-900/90 border border-slate-800 px-3 py-1.5">
            <div className={`h-2 w-2 rounded-full ${isResolved ? 'bg-emerald-400 animate-ping' : 'bg-red-500 animate-pulse'}`} />
            <span className="text-slate-400">STATUS:</span>
            <span className={`font-semibold uppercase ${isResolved ? 'text-emerald-400' : 'text-red-400'}`}>
              {isResolved ? 'TAKE ACTIVE' : 'STAGE PAUSED (INCIDENT)'}
            </span>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-2.5">
          <button
            onClick={onReset}
            className="flex items-center space-x-1.5 rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-700 hover:text-white transition"
            title="Reset to initial incident state"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            <span>Reset Demo</span>
          </button>

          <button
            onClick={onInvestigate}
            disabled={isInvestigating}
            className="flex items-center space-x-1.5 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-lg shadow-cyan-500/20 hover:from-cyan-400 hover:to-blue-500 disabled:opacity-50 transition"
          >
            <Activity className={`h-3.5 w-3.5 ${isInvestigating ? 'animate-spin' : ''}`} />
            <span>{isInvestigating ? 'Agent Investigating...' : 'Re-Run Agent'}</span>
          </button>
        </div>
      </div>
    </header>
  );
};
