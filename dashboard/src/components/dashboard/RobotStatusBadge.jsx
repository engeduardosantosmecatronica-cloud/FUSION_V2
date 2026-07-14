import React from "react";
import { Circle } from "lucide-react";

const statusConfig = {
  running: { color: "text-emerald-400 bg-emerald-400/10", label: "Ativo" },
  paused: { color: "text-amber-400 bg-amber-400/10", label: "Pausado" },
  stopped: { color: "text-red-400 bg-red-400/10", label: "Parado" },
};

export default function RobotStatusBadge({ status }) {
  const cfg = statusConfig[status] || statusConfig.stopped;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${cfg.color}`}>
      <Circle className="w-2 h-2 fill-current" />
      {cfg.label}
    </span>
  );
}