import React, { useState, useEffect } from 'react';
import { api, liveEvents } from '../services/api';
import { GitFork, CheckCircle2, AlertTriangle, Clock, XCircle, Play, Eye, Sparkles, CheckSquare } from 'lucide-react';
import { TaskDetailsModal, TaskData } from '../tasks/TaskDetailsModal';

export const WorkflowsView: React.FC = () => {
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [selectedWf, setSelectedWf] = useState<any | null>(null);
  const [wfTasks, setWfTasks] = useState<any[]>([]);
  const [selectedTask, setSelectedTask] = useState<TaskData | null>(null);
  const [loading, setLoading] = useState(true);

  const loadWorkflows = async () => {
    try {
      const data = await api.getWorkflows();
      setWorkflows(data);
      if (data.length > 0 && !selectedWf) {
        const details = await api.getWorkflow(data[0].id);
        setSelectedWf(details);
        loadWorkflowTasks(data[0].id);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const loadWorkflowTasks = async (workflowId: string) => {
    try {
      const tasks = await api.getTasks({ workflow_id: workflowId });
      setWfTasks(tasks);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadWorkflows();
    const unsub = liveEvents.subscribe(() => {
      loadWorkflows();
      if (selectedWf) {
        loadWorkflowTasks(selectedWf.id);
      }
    });
    return () => unsub();
  }, [selectedWf?.id]);

  const handleSelectWorkflow = async (id: string) => {
    try {
      const details = await api.getWorkflow(id);
      setSelectedWf(details);
      await loadWorkflowTasks(id);
    } catch (e) {
      console.error(e);
    }
  };

  const handleCancel = async (id: string) => {
    try {
      await api.cancelWorkflow(id);
      await handleSelectWorkflow(id);
      await loadWorkflows();
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleResume = async (id: string, approved: boolean) => {
    try {
      await api.resumeWorkflow(id, approved, approved ? 'Aprovado via Monitor de Workflows' : 'Rejeitado via Monitor');
      await handleSelectWorkflow(id);
      await loadWorkflows();
    } catch (e: any) {
      alert(e.message);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white">Monitor de Workflows LangGraph</h2>
        <p className="text-sm text-slate-400">Rastreamento de StateGraph, checkpoints, nós de execução e quality gates.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Workflows List */}
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wide">Execuções Recentes</h3>
          {workflows.map((wf) => (
            <div
              key={wf.id}
              onClick={() => handleSelectWorkflow(wf.id)}
              className={`p-4 rounded-xl border cursor-pointer transition ${
                selectedWf?.id === wf.id
                  ? 'bg-indigo-950/40 border-indigo-500 shadow-md'
                  : 'bg-slate-900/80 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div className="flex justify-between items-start">
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                  {wf.workflow_type}
                </span>
                <span className={`text-xs font-semibold capitalize ${
                  wf.status === 'completed' ? 'text-emerald-400' : wf.status === 'waiting_approval' ? 'text-amber-400' : 'text-indigo-400'
                }`}>
                  {wf.status}
                </span>
              </div>
              <h4 className="text-sm font-bold text-white mt-2 line-clamp-1">{wf.title}</h4>
              <p className="text-xs text-slate-400 mt-1">Nó atual: <b className="text-indigo-300 font-mono">{wf.current_node}</b></p>
            </div>
          ))}
        </div>

        {/* Workflow Detail & Checkpoints */}
        <div className="lg:col-span-2 bg-slate-900/90 rounded-2xl border border-slate-800 p-6 shadow-xl">
          {selectedWf ? (
            <div className="space-y-5">
              <div className="flex justify-between items-start pb-4 border-b border-slate-800">
                <div>
                  <span className="text-xs uppercase font-mono text-indigo-400">{selectedWf.workflow_type} Graph</span>
                  <h3 className="text-xl font-bold text-white mt-1">{selectedWf.title}</h3>
                  <p className="text-xs text-slate-400 mt-0.5 font-mono">ID: {selectedWf.id}</p>
                </div>
                <div className="text-right flex flex-col items-end gap-2">
                  <span className={`inline-block px-3 py-1 rounded-full text-xs font-bold capitalize ${
                    selectedWf.status === 'completed' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-indigo-500/20 text-indigo-300'
                  }`}>
                    {selectedWf.status}
                  </span>
                  <div className="flex gap-2">
                    {selectedWf.status === 'waiting_approval' && (
                      <>
                        <button
                          onClick={() => handleResume(selectedWf.id, true)}
                          className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-[11px] font-semibold flex items-center gap-1"
                        >
                          <Play className="w-3 h-3" /> Aprovar & Retomar
                        </button>
                        <button
                          onClick={() => handleResume(selectedWf.id, false)}
                          className="px-2.5 py-1 bg-rose-700 hover:bg-rose-600 text-white rounded-lg text-[11px] font-semibold"
                        >
                          Rejeitar
                        </button>
                      </>
                    )}
                    {['running', 'queued', 'waiting_approval'].includes(selectedWf.status) && (
                      <button
                        onClick={() => handleCancel(selectedWf.id)}
                        className="px-2.5 py-1 bg-slate-800 hover:bg-rose-900 text-rose-300 rounded-lg text-[11px] font-semibold flex items-center gap-1"
                      >
                        <XCircle className="w-3 h-3" /> Cancelar
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {/* Errors */}
              {selectedWf.errors && selectedWf.errors.length > 0 && (
                <div className="p-3 bg-rose-950/50 border border-rose-800 rounded-xl text-xs text-rose-200 space-y-1">
                  <div className="font-bold flex items-center gap-1.5 text-rose-400"><AlertTriangle className="w-4 h-4" /> Erros Registrados</div>
                  {selectedWf.errors.map((err: string, idx: number) => (
                    <div key={idx}>{err}</div>
                  ))}
                </div>
              )}

              {/* Quality Gate Status */}
              {selectedWf.quality_results && selectedWf.quality_results.length > 0 && (
                <div className="p-4 bg-slate-950/70 rounded-xl border border-slate-800">
                  <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wide flex items-center gap-2">
                    <CheckCircle2 className={`w-4 h-4 ${selectedWf.quality_results[0].passed ? 'text-emerald-400' : 'text-rose-400'}`} />
                    Avaliação Quality Gate (Murphy)
                  </h4>
                  <div className="mt-2 flex items-center justify-between text-sm">
                    <span className="text-slate-300">Pontuação de Qualidade:</span>
                    <span className={`font-bold ${selectedWf.quality_results[0].passed ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {(selectedWf.quality_results[0].score * 100).toFixed(0)}% ({selectedWf.quality_results[0].passed ? 'Aprovado' : 'Reprovado'})
                    </span>
                  </div>
                </div>
              )}

              {/* Checkpoints History */}
              <div>
                <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wide flex items-center gap-1.5">
                  <Clock className="w-4 h-4 text-cyan-400" />
                  Histórico de Checkpoints LangGraph
                </h4>
                <div className="mt-3 space-y-2">
                  {(selectedWf.checkpoints || []).map((cp: any, idx: number) => (
                    <div key={idx} className="p-3 bg-slate-950/60 rounded-xl border border-slate-800/80 flex justify-between items-center text-xs">
                      <div className="flex items-center space-x-2">
                        <span className="w-5 h-5 rounded-full bg-indigo-500/20 text-indigo-300 flex items-center justify-center font-bold">
                          {cp.step_number}
                        </span>
                        <span className="font-mono text-white font-semibold">{cp.node_name}</span>
                      </div>
                      <span className="text-slate-400 font-mono">{cp.timestamp?.slice(11, 19)}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Tasks Executed in Workflow */}
              <div>
                <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wide flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <CheckSquare className="w-4 h-4 text-emerald-400" />
                    Tarefas Executadas no Workflow ({wfTasks.length})
                  </span>
                  <span className="text-[11px] text-slate-500 font-normal">Clique para ver o que foi feito</span>
                </h4>
                <div className="mt-3 space-y-2">
                  {wfTasks.length === 0 ? (
                    <div className="p-4 bg-slate-950/40 rounded-xl border border-slate-800 text-xs text-slate-500 text-center">
                      Nenhuma tarefa registrada para este workflow ainda.
                    </div>
                  ) : (
                    wfTasks.map((t) => (
                      <div
                        key={t.id}
                        onClick={() => setSelectedTask(t)}
                        className="p-3 bg-slate-950/60 hover:bg-slate-950 border border-slate-800/80 hover:border-slate-700 rounded-xl flex items-center justify-between gap-3 text-xs cursor-pointer transition shadow-sm"
                      >
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-white truncate hover:text-indigo-300">{t.title}</span>
                            {t.result_summary && (
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400">
                                Relatório pronto
                              </span>
                            )}
                          </div>
                          <div className="text-[11px] text-slate-400 mt-0.5">
                            Agente: <b className="capitalize text-indigo-300">{t.assigned_agent}</b>
                          </div>
                        </div>

                        <div className="flex items-center gap-2 shrink-0">
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${
                            t.status === 'completed'
                              ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                              : t.status === 'failed'
                              ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                              : 'bg-indigo-500/20 text-indigo-300'
                          }`}>
                            {t.status}
                          </span>
                          <button
                            type="button"
                            onClick={(e) => { e.stopPropagation(); setSelectedTask(t); }}
                            className="p-1.5 bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-300 rounded-lg transition"
                            title="Ver O que foi feito"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-16 text-slate-500 text-sm">Selecione um workflow para inspecionar.</div>
          )}
        </div>
      </div>

      {selectedTask && (
        <TaskDetailsModal
          task={selectedTask}
          onClose={() => setSelectedTask(null)}
          onStatusChange={async (id, status) => {
            await api.updateTaskStatus(id, status);
            if (selectedWf) await loadWorkflowTasks(selectedWf.id);
          }}
        />
      )}
    </div>
  );
};

