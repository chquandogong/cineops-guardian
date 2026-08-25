import React, { useState } from 'react';
import { Eye, Download, FileSpreadsheet } from 'lucide-react';
import { Incident } from '../types';
import { TrajectoryCanvas } from './TrajectoryCanvas';
import { MetricChart } from './MetricChart';
import { getMcapDownloadUrl } from '../services/api';

interface EvidenceViewerProps {
  incident: Incident;
}

export const EvidenceViewer: React.FC<EvidenceViewerProps> = ({ incident }) => {
  const [activeTab, setActiveTab] = useState<'trajectory' | 'metrics' | 'logs' | 'foxglove'>('trajectory');
  const [logFilter, setLogFilter] = useState('');

  // Format trajectory data for metric charts
  const fpsChartData = incident.trajectory.map((pt, idx) => ({
    time: pt.timestamp_offset_s,
    value: idx < 12 ? 24.0 : 16.20,
    threshold: 24.0,
  }));

  const recoveryChartData = incident.trajectory.map((pt) => ({
    time: pt.timestamp_offset_s,
    value: pt.status === 'recovery_loop' ? 7 : (pt.status === 'warning' ? 3 : 0),
  }));

  const tfErrorChartData = incident.trajectory.map((pt) => ({
    time: pt.timestamp_offset_s,
    value: pt.tf_error_norm_m * 1000.0, // in mm
    threshold: 5.0, // 5mm threshold
  }));

  const filteredLogs = incident.loki_logs.filter(
    (log) =>
      log.message.toLowerCase().includes(logFilter.toLowerCase()) ||
      log.service.toLowerCase().includes(logFilter.toLowerCase())
  );

  return (
    <div className="rounded-xl border border-slate-800 bg-[#0c1017] p-4.5 shadow-md flex flex-col h-full">
      {/* Header & Tabs */}
      <div className="flex flex-wrap items-center justify-between border-b border-slate-800/80 pb-3 mb-3.5 gap-2">
        <div className="flex items-center space-x-2">
          <Eye className="h-4 w-4 text-cyan-400" />
          <h3 className="text-sm font-semibold text-white">Multi-Source Telemetry Evidence</h3>
        </div>

        <div className="flex items-center space-x-1.5 rounded-lg bg-slate-900 p-1 border border-slate-800 text-xs font-mono">
          <button
            onClick={() => setActiveTab('trajectory')}
            className={`px-3 py-1 rounded-md transition ${activeTab === 'trajectory' ? 'bg-cyan-600 text-white font-semibold' : 'text-slate-400 hover:text-white'}`}
          >
            2D Spatial Path
          </button>
          <button
            onClick={() => setActiveTab('metrics')}
            className={`px-3 py-1 rounded-md transition ${activeTab === 'metrics' ? 'bg-cyan-600 text-white font-semibold' : 'text-slate-400 hover:text-white'}`}
          >
            Prometheus Metrics
          </button>
          <button
            onClick={() => setActiveTab('logs')}
            className={`px-3 py-1 rounded-md transition ${activeTab === 'logs' ? 'bg-cyan-600 text-white font-semibold' : 'text-slate-400 hover:text-white'}`}
          >
            Loki Logs ({incident.loki_logs.length})
          </button>
          <button
            onClick={() => setActiveTab('foxglove')}
            className={`px-3 py-1 rounded-md transition ${activeTab === 'foxglove' ? 'bg-cyan-600 text-white font-semibold' : 'text-slate-400 hover:text-white'}`}
          >
            Foxglove & BigQuery
          </button>
        </div>
      </div>

      {/* Tab Contents */}
      <div className="flex-1">
        {activeTab === 'trajectory' && (
          <div className="space-y-3">
            <TrajectoryCanvas trajectory={incident.trajectory} />
            <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/70">
              <span>Sensor Fusion: <strong className="text-slate-200">LiDAR 2D Costmap vs Optical Tracker</strong></span>
              <span>Phantom Obstacle Inflation Delta: <strong className="text-red-400">+35mm Z-extrinsic offset</strong></span>
            </div>
          </div>
        )}

        {activeTab === 'metrics' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <MetricChart
              title="Camera Delivery Rate (FPS)"
              data={fpsChartData}
              unit="fps"
              color="crimson"
              height={160}
            />
            <MetricChart
              title="Nav Recovery Loop Count"
              data={recoveryChartData}
              unit="loops"
              color="amber"
              height={160}
            />
            <MetricChart
              title="TF Extrinsics Error Norm"
              data={tfErrorChartData}
              unit="mm"
              color="crimson"
              height={160}
            />
          </div>
        )}

        {activeTab === 'logs' && (
          <div className="space-y-2.5">
            <input
              type="text"
              placeholder="Search Loki logs by service or keyword..."
              value={logFilter}
              onChange={(e) => setLogFilter(e.target.value)}
              className="w-full rounded-md border border-slate-800 bg-[#07090e] px-3 py-1.5 text-xs font-mono text-slate-200 placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
            />
            <div className="max-h-[260px] overflow-y-auto space-y-1.5 text-xs font-mono">
              {filteredLogs.map((log, idx) => (
                <div
                  key={idx}
                  className={`rounded p-2 border ${log.level === 'ERROR' ? 'bg-red-950/20 border-red-900/50 text-red-200' : (log.level === 'WARN' ? 'bg-amber-950/20 border-amber-900/50 text-amber-200' : 'bg-slate-900/40 border-slate-800 text-slate-300')}`}
                >
                  <div className="flex items-center space-x-2 text-[10px] text-slate-400 mb-0.5">
                    <span>{log.timestamp}</span>
                    <span>•</span>
                    <span className="font-semibold text-cyan-400">{log.service}</span>
                    <span>•</span>
                    <span className="font-bold">{log.level}</span>
                  </div>
                  <div className="text-[11.5px]">{log.message}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'foxglove' && (
          <div className="space-y-4 text-xs font-mono">
            {/* MCAP / Foxglove section */}
            <div className="rounded-lg bg-slate-900/80 p-4 border border-slate-800">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  <FileSpreadsheet className="h-4 w-4 text-purple-400" />
                  <h4 className="font-semibold text-white">Foxglove Studio Verification Recording (.MCAP)</h4>
                </div>
                <a
                  href={getMcapDownloadUrl(incident.incident_id)}
                  download="stage_a_take_003_incident.mcap"
                  className="flex items-center space-x-1.5 rounded bg-purple-600 px-3 py-1 text-white hover:bg-purple-500 transition"
                >
                  <Download className="h-3.5 w-3.5" />
                  <span>Download .MCAP Recording</span>
                </a>
              </div>
              <p className="text-slate-400 text-[11px] leading-relaxed mb-3">
                CineOps Guardian automatically synthesized synchronized multi-channel ROS2 / Foxglove MCAP telemetry including <code>/tf</code>, <code>/dolly/odom</code>, <code>/costmap/obstacles</code>, and <code>/camera/status</code>. Open this file in Foxglove Studio to visually inspect 3D TF frames and LiDAR point clouds.
              </p>
              <div className="rounded bg-[#07090e] p-2.5 border border-slate-800 text-[11px] text-slate-300">
                <strong>How to verify:</strong> Open Foxglove Studio &gt; Open Local File &gt; Select <code>stage_a_take_003_incident.mcap</code> &gt; Check TF tree <code>[camera_optical_frame] -&gt; [lidar_link]</code> translation offset.
              </div>
            </div>

            {/* BigQuery Historical Matches */}
            <div className="rounded-lg bg-slate-900/80 p-4 border border-slate-800">
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-semibold text-white">BigQuery Historical Incident Comparison (2 Matches)</h4>
                <span className="text-[11px] text-cyan-400">cineops_guardian.incident_history</span>
              </div>
              <div className="space-y-2">
                {incident.historical_matches.map((match) => (
                  <div key={match.incident_id} className="rounded bg-[#07090e] p-2.5 border border-slate-800">
                    <div className="flex items-center justify-between text-slate-400 text-[10.5px] mb-1">
                      <span className="font-bold text-slate-200">{match.incident_id} ({match.stage})</span>
                      <span className="rounded bg-cyan-950 px-2 py-0.5 text-cyan-300 font-semibold">
                        {(match.similarity_score * 100).toFixed(0)}% Match
                      </span>
                    </div>
                    <div className="text-[11.5px] text-slate-300">{match.symptoms}</div>
                    <div className="text-[10.5px] text-emerald-400 mt-1">
                      ✓ Resolution: {match.action_taken} (Resolved in {match.delay_minutes}m)
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
