import React from 'react';

export default class AppErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null, info: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error('[Fusion Frontend ErrorBoundary]', error, info);
    this.setState({ info });
  }

  render() {
    if (!this.state.error) return this.props.children;

    return (
      <div className="min-h-screen bg-[#0d1117] text-slate-100 p-6 font-mono">
        <div className="max-w-4xl mx-auto border border-red-900 bg-red-950/20 rounded p-4 space-y-3">
          <div className="text-red-400 text-sm font-bold uppercase tracking-wider">Erro no Fusion Frontend</div>
          <div className="text-xs text-slate-300">A aplicação encontrou um erro de renderização. A mensagem abaixo ajuda a localizar o ponto exato.</div>
          <pre className="text-xs whitespace-pre-wrap break-words bg-black/30 border border-red-900/60 rounded p-3 text-red-200">
            {String(this.state.error?.stack || this.state.error?.message || this.state.error)}
          </pre>
          {this.state.info?.componentStack && (
            <pre className="text-xs whitespace-pre-wrap break-words bg-black/30 border border-slate-800 rounded p-3 text-slate-300">
              {this.state.info.componentStack}
            </pre>
          )}
          <button
            className="px-3 py-1.5 rounded bg-red-600 text-white text-xs font-bold"
            onClick={() => window.location.reload()}
          >
            Recarregar
          </button>
        </div>
      </div>
    );
  }
}
