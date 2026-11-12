import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Cpu, Wrench, X, Shield, Activity } from 'lucide-react';

export const AgentsView: React.FC = () => {
  const [agents, setAgents] = useState<any[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<any | null>(null);
  const [filterDept, setFilterDept] = useState<string>('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getAgents()
      .then(setAgents)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const openAgentDetail = async (id: string) => {
    try {
      const detail = await api.getAgent(id);
      setSelectedAgent(detail);
    } catch (e) {
      console.error(e);
    }
  };

  const departments = ['all', 'Executive', 'Development', 'Content', 'Audiovisual', 'QA', 'Infrastructure'];

  const filtered = filterDept === 'all'
    ? agents
    : agents.filter((a) => a.department.toLowerCase() === filterDept.toLowerCase());

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            Os {agents.length} Agentes Oficiais
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-mono">
              {agents.length}/14 Ativos
            </span>
          </h2>
          <p className="text-sm text-slate-400">Clique em qualquer especialista para inspecionar métricas, ferramentas, permissões e histórico.</p>
        </div>

        <div className="flex flex-wrap gap-1.5">
          {departments.map((dept) => (
            <button
              key={dept}
              onClick={() => setFilterDept(dept)}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium transition ${
                filterDept === dept
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                  : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
              }`}
            >
              {dept === 'all' ? 'Todos' : dept}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-slate-400 text-sm">Carregando agentes oficiais...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filtered.map((agent) => (
            <div
              key={agent.id}
              onClick={() => openAgentDetail(agent.id)}
              className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 hover:border-indigo-500/50 cursor-pointer transition shadow-md flex flex-col justify-between"
            >
              <div>
                <div className="flex justify-between items-start">
                  <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-slate-800 text-indigo-400 border border-slate-700">
                    {agent.department}
                  </span>
                  <div className="flex items-center space-x-1.5 text-xs text-emerald-400 font-medium">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                    <span className="capitalize">{agent.operational_state || 'idle'}</span>
                  </div>
                </div>

                <div className="mt-3">
                  <h3 className="text-xl font-bold text-white">{agent.name}</h3>
                  <p className="text-xs font-semibold text-slate-300 mt-0.5">{agent.role}</p>
                  <p className="text-xs text-slate-400 mt-2 line-clamp-3 leading-relaxed">{agent.specialty}</p>
                </div>
              </div>

              <div className="mt-5 pt-4 border-t border-slate-800/80 space-y-2">
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span className="flex items-center gap-1.5"><Cpu className="w-3.5 h-3.5 text-indigo-400" /> Tarefas:</span>
                  <span className="font-mono text-slate-300">{agent.metrics?.tasks_completed || 0}</span>
                </div>
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span className="flex items-center gap-1.5"><Wrench className="w-3.5 h-3.5 text-cyan-400" /> Ferramentas:</span>
                  <span className="text-slate-300 font-medium">{agent.allowed_tools?.length || 0} declaradas</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {selectedAgent && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-2xl max-h-[85vh] bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl flex flex-col">
            <div className="flex justify-between items-start pb-4 border-b border-slate-800">
              <div>
                <span className="text-[10px] uppercase font-bold text-indigo-400">{selectedAgent.department} • {selectedAgent.office_room}</span>
                <h3 className="text-xl font-bold text-white">{selectedAgent.name}</h3>
                <p className="text-xs text-slate-400">{selectedAgent.role}</p>
              </div>
              <button onClick={() => setSelectedAgent(null)} className="text-slate-400 hover:text-white"><X className="w-5 h-5" /></button>
            </div>
            <div className="mt-4 space-y-4 overflow-y-auto pr-1 text-xs">
              <div>
                <div className="font-semibold text-slate-400 uppercase mb-1">Especialidade</div>
                <p className="text-slate-200 leading-relaxed">{selectedAgent.specialty}</p>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
                  <div className="text-slate-400 flex items-center gap-1"><Activity className="w-3.5 h-3.5 text-emerald-400" /> Status</div>
                  <div className="text-sm font-bold text-emerald-400 capitalize mt-1">{selectedAgent.operational_state}</div>
                </div>
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
                  <div className="text-slate-400">Tarefas Concluídas</div>
                  <div className="text-sm font-bold text-white mt-1">{selectedAgent.metrics?.tasks_completed || 0}</div>
                </div>
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
                  <div className="text-slate-400">Tokens</div>
                  <div className="text-sm font-bold text-white mt-1">{selectedAgent.metrics?.token_usage || 0}</div>
                </div>
              </div>
              <div>
                <div className="font-semibold text-slate-400 uppercase mb-1.5">Ferramentas & Permissões</div>
                <div className="flex flex-wrap gap-1.5">
                  {(selectedAgent.allowed_tools || []).map((t: string) => (
                    <span key={t} className="px-2 py-0.5 rounded bg-slate-800 text-cyan-300 border border-slate-700 font-mono">{t}</span>
                  ))}
                  {(selectedAgent.permissions || []).map((p: string) => (
                    <span key={p} className="px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800 font-mono flex items-center gap-1"><Shield className="w-3 h-3" />{p}</span>
                  ))}
                </div>
              </div>
              {(selectedAgent.history || []).length > 0 && (
                <div>
                  <div className="font-semibold text-slate-400 uppercase mb-1.5">Histórico Recente</div>
                  <div className="space-y-1.5">
                    {selectedAgent.history.slice(-5).reverse().map((h: any, idx: number) => (
                      <div key={idx} className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 flex justify-between">
                        <span className="text-slate-200">{h.title}</span>
                        <span className="text-emerald-400 font-mono">{h.status}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
