import React from "react";

export default function StatusCard({ icon: Icon, label, value, sub, color = "text-white" }) {
  return (
    <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-4 flex items-start gap-3">
      {Icon && (
        <div className="p-2 rounded-lg bg-[#1a2035]">
          <Icon className={`w-4 h-4 ${color}`} />
        </div>
      )}
      <div className="min-w-0">
        <p className="text-xs text-gray-500 uppercase tracking-wider">{label}</p>
        <p className={`text-lg font-bold ${color} truncate`}>{value}</p>
        {sub && <p className="text-xs text-gray-500 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}