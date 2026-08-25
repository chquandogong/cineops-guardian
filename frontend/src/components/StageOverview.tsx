import React from 'react';
import { Camera, Bot, Radio, Cpu, Wifi, CheckCircle2, AlertTriangle, ShieldAlert } from 'lucide-react';
import { StageHealth, RobotTelemetry } from '../types';

interface StageOverviewProps {
  stage: StageHealth;
  robot: RobotTelemetry;
}

export const StageOverview: React.FC<StageOverviewProps> = ({ stage, robot }) => {

  return (
    <div className="rounded-xl border border-slate-800 bg-[#0c1017] p-4.5 shadow-md">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-3.5">
        <div className="flex items-center space-x-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded bg-slate-800 text-cyan-400">
            <Bot className="h-4 w-4" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-white flex items-center gap-2">
              {robot.robot_name}
              <span className="text-xs font-mono text-slate-400">({robot.robot_id})</span>
            </h2>
            <p className="text-[11px] text-slate-400 font-mono">
              Firmware: {robot.firmware_version} | Profile: <span className={robot.tf_checksum_valid ? 'text-emerald-400' : 'text-amber-400 font-semibold'}>{robot.active_rig_profile}</span>
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {robot.tf_checksum_valid ? (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-950/80 border border-emerald-800/60 px-2.5 py-0.5 text-xs font-mono text-emerald-300">
              <CheckCircle2 className="h-3 w-3 text-emerald-400" />
              TF CHECKSUM VALID (CRC 0x8F4A)
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-red-950/80 border border-red-800/60 px-2.5 py-0.5 text-xs font-mono text-red-300 animate-pulse">
              <ShieldAlert className="h-3 w-3 text-red-400" />
              TF CHECKSUM MISMATCH (0x3E12)
            </span>
          )}
        </div>
      </div>

      {/* Grid of Key Telemetry Indicators */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 text-xs font-mono">
        {/* Camera FPS */}
        <div className={`rounded-lg p-2.5 border ${robot.camera_fps < 23.0 ? 'bg-red-950/30 border-red-800/60' : 'bg-slate-900 border-slate-800'}`}>
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="flex items-center gap-1"><Camera className="h-3 w-3" /> CAM FPS</span>
            <span className="text-[10px] text-slate-500">24.0 tgt</span>
          </div>
          <div className="flex items-baseline space-x-1.5">
            <span className={`text-lg font-bold ${robot.camera_fps < 23.0 ? 'text-red-400' : 'text-emerald-400'}`}>
              {robot.camera_fps.toFixed(2)}
            </span>
            <span className="text-[10px] text-slate-400">fps</span>
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5">
            {robot.dropped_frames_pct > 0 ? (
              <span className="text-red-400 font-semibold">{robot.dropped_frames_pct}% dropped</span>
            ) : (
              <span className="text-emerald-400">0% dropped</span>
            )}
          </div>
        </div>

        {/* Nav Recovery Loops */}
        <div className={`rounded-lg p-2.5 border ${robot.nav_recovery_loop_count > 0 ? 'bg-red-950/30 border-red-800/60' : 'bg-slate-900 border-slate-800'}`}>
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="flex items-center gap-1"><AlertTriangle className="h-3 w-3" /> NAV LOOPS</span>
            <span className="text-[10px] text-slate-500">0 tgt</span>
          </div>
          <div className="flex items-baseline space-x-1.5">
            <span className={`text-lg font-bold ${robot.nav_recovery_loop_count > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
              {robot.nav_recovery_loop_count}
            </span>
            <span className="text-[10px] text-slate-400">retries</span>
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5">
            {robot.costmap_inflation_alert ? (
              <span className="text-amber-400">Costmap Alert</span>
            ) : (
              <span className="text-slate-400">Clearance OK</span>
            )}
          </div>
        </div>

        {/* Localization Confidence */}
        <div className="rounded-lg p-2.5 bg-slate-900 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="flex items-center gap-1"><Radio className="h-3 w-3" /> LOC CONF</span>
            <span className="text-[10px] text-slate-500">&gt;0.85</span>
          </div>
          <div className="flex items-baseline space-x-1.5">
            <span className={`text-lg font-bold ${robot.localization_confidence < 0.8 ? 'text-amber-400' : 'text-emerald-400'}`}>
              {(robot.localization_confidence * 100).toFixed(0)}%
            </span>
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5">
            OptiTrack Sync: <span className={stage.led_wall_sync ? 'text-emerald-400' : 'text-red-400'}>GENLOCKED</span>
          </div>
        </div>

        {/* Encoder Latency */}
        <div className="rounded-lg p-2.5 bg-slate-900 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="flex items-center gap-1"><Cpu className="h-3 w-3" /> LATENCY</span>
            <span className="text-[10px] text-slate-500">&lt;25ms</span>
          </div>
          <div className="flex items-baseline space-x-1.5">
            <span className={`text-lg font-bold ${robot.encoder_latency_ms > 30 ? 'text-amber-400' : 'text-emerald-400'}`}>
              {robot.encoder_latency_ms.toFixed(1)}
            </span>
            <span className="text-[10px] text-slate-400">ms</span>
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5">
            GPU: {robot.gpu_temp_celsius}°C ({robot.gpu_utilization_pct}%)
          </div>
        </div>

        {/* Network & 5G Link */}
        <div className="rounded-lg p-2.5 bg-slate-900 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="flex items-center gap-1"><Wifi className="h-3 w-3" /> NETWORK</span>
            <span className="text-[10px] text-slate-500">Private 5G</span>
          </div>
          <div className="flex items-baseline space-x-1.5">
            <span className="text-lg font-bold text-emerald-400">
              {robot.network_rtt_ms}
            </span>
            <span className="text-[10px] text-slate-400">ms RTT</span>
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5">
            Loss: <span className="text-emerald-400">{robot.network_packet_loss_pct}% (Stable)</span>
          </div>
        </div>

        {/* Battery & Power */}
        <div className="rounded-lg p-2.5 bg-slate-900 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span>BATTERY</span>
            <span className="text-[10px] text-slate-500">Hot-Swap</span>
          </div>
          <div className="flex items-baseline space-x-1.5">
            <span className="text-lg font-bold text-cyan-400">
              {robot.battery_percentage}%
            </span>
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5">
            Nominal: 4.8h remaining
          </div>
        </div>
      </div>
    </div>
  );
};
