import React, { useEffect, useState } from 'react';
import { api, liveEvents } from '../services/api';
import { CheckSquare, Plus, Trash2, Eye, Sparkles, CheckCircle2, XCircle, Clock } from 'lucide-react';
import { TaskDetailsModal, TaskData } from './TaskDetailsModal';

export const TasksView: React.FC = () => {
  const [tasks, setTasks] = useState<any[]>([]);
  const [agents, setAgents] = useState<any[]>([]);
  const [projects, setProjects] = useState<any[]>([]);
  const [filterStatus, setFilterStatus] = useState('');
  const [title, setTitle] = useState('');
  const [assignedAgent, setAssignedAgent] = useState('jeffrey');
  const [projectId, setProjectId] = useState('');
  const [priority, setPriority] = useState('medium');
  const [loading, setLoading] = useState(true);
  const [selectedTask, setSelectedTask] = useState<TaskData | null>(null);

  const loadData = async () => {
    try {
      const [tsks, ags, prjs] = await Promise.all([
        api.getTasks(),
        api.getAgents().catch(() => []),
        api.getProjects().catch(() => []),
      ]);
      setTasks(tsks);
      setAgents(ags);
      setProjects(prjs);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const unsub = liveEvents.subscribe(() => loadData());
    return () => unsub();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    await api.createTask({
      title,
      assigned_agent_id: assignedAgent,
      project_id: projectId || undefined,
      priority,
    });
    setTitle('');
    await loadData();
  };

  const handleStatusChange = async (id: string, status: string) => {
    await api.updateTaskStatus(id, status);
    if (selectedTask && selectedTask.id === id) {
      setSelectedTask({ ...selectedTask, status });
    }
    await loadData();
  };

  const handleDelete = async (id: string) => {
    await api.deleteTask(id);
    await loadData();
  };

  const visible = filterStatus ? tasks.filter((t) => t.status === filterStatus) : tasks;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <CheckSquare className="w-6 h-6 text-emerald-400" />
            <span>Gerenciador de Tarefas</span>
          </h2>
          <p className="text-sm text-slate-400">Criação, delegação por agente e acompanhamento persistente de tarefas.</p>
        </div>
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-xs text-white"
        >
          <option value="">Todos os status</option>
          <option value="pending">Pendente</option>
          <option value="in_progress">Em andamento</option>
          <option value="completed">Concluída</option>
          <option value="failed">Falhou</option>
        </select>
      </div>

      <form onSubmit={handleCreate} className="p-4 rounded-2xl bg-slate-900/90 border border-slate-800 grid grid-cols-1 md:grid-cols-5 gap-3">
        <input
          type="text"
          required
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Título da nova tarefa..."
          className="md:col-span-2 px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-xs text-white"
        />
        <select
          value={assignedAgent}
          onChange={(e) => setAssignedAgent(e.target.value)}
          className="px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-xs text-white"
        >
          {agents.map((a) => (
            <option key={a.id} value={a.id}>{a.name}</option>
          ))}
        </select>
        <select
          value={projectId}
          onChange={(e) => setProjectId(e.target.value)}
          className="px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-xs text-white"
        >
          <option value="">Sem projeto</option>
          {projects.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
        <div className="flex gap-2">
          <select
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
            className="px-2 py-2 bg-slate-950 border border-slate-700 rounded-xl text-xs text-white"
          >
            <option value="low">Baixa</option>
            <option value="medium">Média</option>
            <option value="high">Alta</option>
          </select>
          <button type="submit" className="flex-1 px-3 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold flex items-center justify-center gap-1">
            <Plus className="w-4 h-4" /> Criar
          </button>
        </div>
      </form>

      {loading ? (
        <div className="text-center py-12 text-slate-400 text-sm">Carregando tarefas...</div>
      ) : visible.length === 0 ? (
        <div className="p-12 text-center bg-slate-900/60 rounded-2xl border border-slate-800 text-slate-400 text-sm">
          Nenhuma tarefa encontrada.
        </div>
      ) : (
        <div className="space-y-2.5">
          {visible.map((t) => (
            <div
              key={t.id}
              onClick={() => setSelectedTask(t)}
              className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 hover:border-slate-700 cursor-pointer transition flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 shadow-sm hover:shadow-md"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-white hover:text-indigo-300 transition">{t.title}</span>
                  {t.result_summary && (
                    <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
                      <Sparkles className="w-2.5 h-2.5" /> Entrega pronta
                    </span>
                  )}
                </div>
                <div className="text-xs text-slate-400 mt-1 flex flex-wrap items-center gap-3">
                  <span>Agente: <b className="text-indigo-300 capitalize">{t.assigned_agent}</b></span>
                  <span>•</span>
                  <span>Prioridade: <b className="capitalize text-slate-300">{t.priority}</b></span>
                  {t.quality_score !== null && t.quality_score !== undefined && (
                    <>
                      <span>•</span>
                      <span className="text-emerald-400 font-medium">Qualidade: {(t.quality_score * 100).toFixed(0)}%</span>
                    </>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0" onClick={(e) => e.stopPropagation()}>
                <button
                  type="button"
                  onClick={() => setSelectedTask(t)}
                  className="px-2.5 py-1.5 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition"
                  title="Ver detalhes da entrega"
                >
                  <Eye className="w-3.5 h-3.5" />
                  <span>Ver Detalhes</span>
                </button>

                <select
                  value={t.status}
                  onChange={(e) => handleStatusChange(t.id, e.target.value)}
                  className="px-2.5 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-xs text-white"
                >
                  <option value="pending">pending</option>
                  <option value="in_progress">in_progress</option>
                  <option value="completed">completed</option>
                  <option value="failed">failed</option>
                  <option value="waiting_approval">waiting_approval</option>
                </select>

                <button
                  type="button"
                  onClick={() => handleDelete(t.id)}
                  className="p-1.5 bg-rose-950/60 hover:bg-rose-900 text-rose-300 rounded-lg transition"
                  title="Excluir"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {selectedTask && (
        <TaskDetailsModal
          task={selectedTask}
          onClose={() => setSelectedTask(null)}
          onStatusChange={handleStatusChange}
        />
      )}
    </div>
  );
};

