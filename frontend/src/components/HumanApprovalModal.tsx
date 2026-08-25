import React, { useState } from 'react';
import { ShieldCheck, X, Lock } from 'lucide-react';
import { RecoveryRecommendation } from '../types';

interface HumanApprovalModalProps {
  recommendation: RecoveryRecommendation | null;
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (actionId: string, operatorName: string) => void;
  isProcessing: boolean;
}

export const HumanApprovalModal: React.FC<HumanApprovalModalProps> = ({
  recommendation,
  isOpen,
  onClose,
  onConfirm,
  isProcessing,
}) => {
  const [operatorName, setOperatorName] = useState('Lead Rig Operator / Stage Director');
  const [confirmedSafety, setConfirmedSafety] = useState(false);

  if (!isOpen || !recommendation) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="w-full max-w-xl rounded-xl border border-slate-800 bg-[#0c1017] p-6 shadow-2xl text-xs font-mono">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="h-5 w-5 text-emerald-400" />
            <h3 className="text-base font-bold text-white">Stage Safety & Recovery Authorization</h3>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-4">
          {/* Action Details */}
          <div className="rounded-lg bg-slate-900 p-3.5 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-cyan-400 font-bold">ACTION ID: {recommendation.action_id}</span>
              <span className="rounded bg-emerald-950 px-2 py-0.5 text-emerald-400 font-semibold border border-emerald-800">
                RISK LEVEL: {recommendation.risk_level.toUpperCase()}
              </span>
            </div>
            <h4 className="text-sm font-semibold text-white">{recommendation.title}</h4>
            <p className="text-slate-300 text-[11.5px] leading-relaxed">{recommendation.action_description}</p>
          </div>

          {/* Rollback and Effect */}
          <div className="rounded-lg bg-[#07090e] p-3 border border-slate-800 text-[11px] space-y-1.5">
            <div>
              <strong className="text-cyan-300">Expected Result:</strong> {recommendation.expected_effect}
            </div>
            <div>
              <strong className="text-amber-400">Rollback Safety Plan:</strong> {recommendation.rollback_instructions}
            </div>
          </div>

          {/* Operator Signature Form */}
          <div className="space-y-3 pt-2">
            <div>
              <label className="block text-slate-300 font-semibold mb-1">
                Authorized Operator Name / Call Sign:
              </label>
              <input
                type="text"
                value={operatorName}
                onChange={(e) => setOperatorName(e.target.value)}
                className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-xs font-mono text-white focus:border-emerald-500 focus:outline-none"
              />
            </div>

            <label className="flex items-start space-x-2 cursor-pointer pt-1">
              <input
                type="checkbox"
                checked={confirmedSafety}
                onChange={(e) => setConfirmedSafety(e.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-slate-700 bg-slate-950 text-emerald-500 focus:ring-0"
              />
              <span className="text-slate-300 text-[11px] leading-snug">
                I verify that the camera dolly is stationary, stage crew is clear of the trajectory path, and reload of approved profile <strong>CALIB-RIG-2026-v4</strong> is safe to execute.
              </span>
            </label>
          </div>

          {/* Modal Actions */}
          <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-800">
            <button
              onClick={onClose}
              className="rounded-lg border border-slate-700 px-4 py-2 text-slate-300 hover:bg-slate-800"
            >
              Cancel
            </button>
            <button
              onClick={() => onConfirm(recommendation.action_id, operatorName)}
              disabled={!confirmedSafety || isProcessing}
              className="flex items-center space-x-1.5 rounded-lg bg-emerald-600 px-5 py-2 font-bold text-white shadow-lg shadow-emerald-600/30 hover:bg-emerald-500 disabled:opacity-50 transition"
            >
              <Lock className="h-3.5 w-3.5" />
              <span>{isProcessing ? 'Executing Recovery...' : 'Authorize & Execute Recovery'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
