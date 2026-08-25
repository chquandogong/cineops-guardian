import React, { useEffect, useRef } from 'react';
import { TrajectoryPoint } from '../types';

interface TrajectoryCanvasProps {
  trajectory: TrajectoryPoint[];
}

export const TrajectoryCanvas: React.FC<TrajectoryCanvasProps> = ({ trajectory }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;

    // Clear background
    ctx.fillStyle = '#0a0e17';
    ctx.fillRect(0, 0, width, height);

    // Draw coordinate grid
    ctx.strokeStyle = '#172030';
    ctx.lineWidth = 1;
    for (let x = 0; x < width; x += 40) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    for (let y = 0; y < height; y += 40) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    // Stage boundary / Volume wall
    ctx.strokeStyle = '#233047';
    ctx.lineWidth = 2;
    ctx.strokeRect(20, 20, width - 40, height - 40);

    // Coordinate transforms mapping (x: 0..10m -> 40..width-40, y: 0..4m -> height-40..40)
    const mapX = (x: number) => 40 + (x / 10.0) * (width - 80);
    const mapY = (y: number) => height - (40 + (y / 4.0) * (height - 80));

    // Obstacle (Lighting Stand C-Stand 03) at (4.82, 2.15)
    const obsX = mapX(4.82);
    const obsY = mapY(2.15);

    // Phantom Inflation Zone (due to +35mm TF error)
    ctx.fillStyle = 'rgba(239, 68, 68, 0.15)';
    ctx.beginPath();
    ctx.arc(obsX, obsY, 45, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = 'rgba(239, 68, 68, 0.4)';
    ctx.setLineDash([4, 4]);
    ctx.stroke();

    // Actual physical clearance radius (1.25m)
    ctx.fillStyle = 'rgba(245, 158, 11, 0.25)';
    ctx.beginPath();
    ctx.arc(obsX, obsY, 25, 0, Math.PI * 2);
    ctx.fill();

    // Obstacle Center Marker
    ctx.fillStyle = '#ef4444';
    ctx.beginPath();
    ctx.arc(obsX, obsY, 6, 0, Math.PI * 2);
    ctx.fill();
    ctx.setLineDash([]);
    ctx.fillStyle = '#cbd5e1';
    ctx.font = '10px JetBrains Mono, monospace';
    ctx.fillText('Lighting C-Stand 03 (x: 4.82, y: 2.15)', obsX - 70, obsY - 14);

    if (trajectory.length > 0) {
      // 1. Draw Planned Path (Cyan Dashed)
      ctx.strokeStyle = '#06b6d4';
      ctx.lineWidth = 2;
      ctx.setLineDash([6, 4]);
      ctx.beginPath();
      trajectory.forEach((pt, idx) => {
        const cx = mapX(pt.planned_x);
        const cy = mapY(pt.planned_y);
        if (idx === 0) ctx.moveTo(cx, cy);
        else ctx.lineTo(cx, cy);
      });
      ctx.stroke();

      // 2. Draw Actual Trajectory (Green -> Amber -> Red Oscillation)
      ctx.setLineDash([]);
      for (let i = 0; i < trajectory.length - 1; i++) {
        const p1 = trajectory[i];
        const p2 = trajectory[i + 1];
        ctx.beginPath();
        ctx.moveTo(mapX(p1.actual_x), mapY(p1.actual_y));
        ctx.lineTo(mapX(p2.actual_x), mapY(p2.actual_y));

        if (p2.status === 'normal') {
          ctx.strokeStyle = '#10b981';
          ctx.lineWidth = 2.5;
        } else if (p2.status === 'warning') {
          ctx.strokeStyle = '#f59e0b';
          ctx.lineWidth = 3;
        } else {
          ctx.strokeStyle = '#ef4444';
          ctx.lineWidth = 3.5;
        }
        ctx.stroke();
      }

      // 3. Draw Camera Dolly Current Position Marker
      const lastPt = trajectory[trajectory.length - 1];
      const curX = mapX(lastPt.actual_x);
      const curY = mapY(lastPt.actual_y);

      // Dolly Body Box
      ctx.fillStyle = '#0284c7';
      ctx.strokeStyle = '#38bdf8';
      ctx.lineWidth = 2;
      ctx.fillRect(curX - 10, curY - 7, 20, 14);
      ctx.strokeRect(curX - 10, curY - 7, 20, 14);

      // Camera Optical Vector / Optical Tracking Ray
      ctx.strokeStyle = '#e0e7ff';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(curX + 10, curY);
      ctx.lineTo(curX + 35, curY);
      ctx.stroke();

      // Camera label
      ctx.fillStyle = '#38bdf8';
      ctx.font = 'bold 11px JetBrains Mono, monospace';
      ctx.fillText('Dolly Alpha [Oscillating in Recovery Loop]', curX - 90, curY + 26);
    }

    // Legend
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(30, height - 60, 360, 32);
    ctx.strokeStyle = '#334155';
    ctx.strokeRect(30, height - 60, 360, 32);

    ctx.font = '10px JetBrains Mono, monospace';
    ctx.fillStyle = '#06b6d4';
    ctx.fillText('-- Planned Trajectory', 40, height - 40);
    ctx.fillStyle = '#10b981';
    ctx.fillText('— Normal', 170, height - 40);
    ctx.fillStyle = '#ef4444';
    ctx.fillText('— Avoidance Oscillation', 240, height - 40);
  }, [trajectory]);

  return (
    <div className="relative w-full overflow-hidden rounded-lg border border-slate-800 bg-[#0a0e17]">
      <canvas
        ref={canvasRef}
        width={720}
        height={320}
        className="w-full h-auto block"
      />
    </div>
  );
};
