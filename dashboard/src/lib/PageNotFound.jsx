import React from "react";
import { Link } from "react-router-dom";

export default function PageNotFound() {
  return (
    <div className="min-h-screen bg-[#060a13] text-white flex items-center justify-center">
      <div className="text-center">
        <div className="text-6xl font-bold text-emerald-400">404</div>
        <h1 className="text-2xl font-semibold mt-4">Página não encontrada</h1>
        <Link to="/" className="inline-block mt-6 px-4 py-2 rounded bg-emerald-500 text-white">Voltar ao início</Link>
      </div>
    </div>
  );
}