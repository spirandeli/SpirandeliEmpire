import React, { useState, useEffect } from 'react';
import { api, liveEvents } from '../services/api';
import { ShieldAlert, CheckCircle2, XCircle, AlertTriangle, ArrowRight } from 'lucide-react';

export const ApprovalsView: React.FC = () => {
  const [approvals, setApprovals] = useState<any[]>([]);
  const [feedbackMap, setFeedbackMap] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);

  const loadApprovals = async () => {
    try {
      const data = await api.getApprovals();
      setApprovals(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadApprovals();
    const unsub = liveEvents.subscribe(() => loadApprovals());
    return () => unsub();
  }, []);

  const handleDecision = async (id: string, approved: boolean) => {
    const feedback = feedbackMap[id] || '';
    try {
      await api.decideApproval(id, approved, feedback);
      loadApprovals();
    } catch (e: any) {
      alert(`Erro: ${e.message}`);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
          Human-in-the-Loop Approvals
          <span className="text-xs px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
            Controle de Autonomia
          </span>
        </h2>
        <p className="text-sm text-slate-400">
          Operações críticas (deploys, publicação, exclusões e custos) interrompem o workflow aguardando decisão do proprietário.
        </p>
      </div>

      {loading ? (
        <div className="text-center py-12 text-slate-400 text-sm">Carregando aprovações...</div>
      ) : approvals.length === 0 ? (
        <div className="p-12 text-center bg-slate-900/60 rounded-2xl border border-slate-800">
          <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-slate-300">Nenhuma aprovação pendente</h3>
          <p className="text-sm text-slate-500 mt-1">Todos os workflows estão operando de acordo com as permissões autorizadas.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {approvals.map((app) => (
            <div
              key={app.id}
              className={`p-6 rounded-2xl border transition shadow-lg ${
                app.status === 'pending'
                  ? 'bg-amber-950/20 border-amber-500/50'
                  : 'bg-slate-900/80 border-slate-800 opacity-75'
              }`}
            >
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 pb-3 border-b border-slate-800">
                <div>
                  <span className="text-xs uppercase font-bold text-amber-400">Solicitado por: {app.requested_by}</span>
                  <h3 className="text-lg font-bold text-white mt-0.5">{app.action_name}</h3>
                </div>
                <span className={`text-xs px-3 py-1 rounded-full font-bold uppercase ${
                  app.status === 'pending' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' : 'bg-slate-800 text-slate-400'
                }`}>
                  {app.status}
                </span>
              </div>

              <div className="mt-4 space-y-3 text-sm">
                <div>
                  <span className="text-xs font-semibold text-slate-400 uppercase">Descrição da Operação</span>
                  <p className="text-slate-200 mt-1">{app.description}</p>
                </div>

                {app.risks && app.risks.length > 0 && (
                  <div>
                    <span className="text-xs font-semibold text-rose-400 uppercase flex items-center gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5" /> Riscos Identificados
                    </span>
                    <ul className="list-disc list-inside text-xs text-rose-200/90 mt-1 space-y-0.5">
                      {app.risks.map((r: string, idx: number) => (
                        <li key={idx}>{r}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {app.status === 'pending' && (
                  <div className="pt-3 border-t border-slate-800 space-y-3">
                    <input
                      type="text"
                      placeholder="Instruções adicionais ou observações para o Jeffrey..."
                      value={feedbackMap[app.id] || ''}
                      onChange={(e) => setFeedbackMap({ ...feedbackMap, [app.id]: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-sm text-white focus:outline-none focus:border-amber-500"
                    />
                    <div className="flex justify-end gap-3">
                      <button
                        onClick={() => handleDecision(app.id, false)}
                        className="px-4 py-2 bg-rose-950/60 hover:bg-rose-900 border border-rose-700/60 text-rose-200 rounded-xl text-xs font-bold transition flex items-center space-x-1.5"
                      >
                        <XCircle className="w-4 h-4" />
                        <span>Rejeitar Operação</span>
                      </button>
                      <button
                        onClick={() => handleDecision(app.id, true)}
                        className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-bold transition flex items-center space-x-1.5 shadow-lg shadow-emerald-600/30"
                      >
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Aprovar & Retomar LangGraph</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

