import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Plus, Briefcase, Rocket, X, Eye, Trash2, Edit3 } from 'lucide-react';

export const ProjectsView: React.FC = () => {
  const [projects, setProjects] = useState<any[]>([]);
  const [selectedProject, setSelectedProject] = useState<any | null>(null);
  const [editingProject, setEditingProject] = useState<any | null>(null);
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [newTaskAgent, setNewTaskAgent] = useState('jeffrey');
  const [loading, setLoading] = useState(true);
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);
  const [showBusinessWizard, setShowBusinessWizard] = useState(false);

  const [name, setName] = useState('');
  const [desc, setDesc] = useState('');
  const [type, setType] = useState('software');
  const [priority, setPriority] = useState('medium');

  const [bizName, setBizName] = useState('');
  const [bizNiche, setBizNiche] = useState('');
  const [bizAudience, setBizAudience] = useState('');
  const [bizMonetization, setBizMonetization] = useState('Assinatura SaaS Recorrente');
  const [bizBudget, setBizBudget] = useState('Bootstrapped ($0-$500)');

  const loadProjects = async () => {
    try {
      const data = await api.getProjects();
      setProjects(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    try {
      await api.createProject({ name, description: desc, project_type: type, priority });
      setShowNewProjectModal(false);
      setName('');
      setDesc('');
      loadProjects();
    } catch (e: any) {
      alert(`Erro: ${e.message}`);
    }
  };

  const handleCreateBusiness = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!bizName.trim()) return;
    try {
      await api.createDigitalBusiness({
        name: bizName,
        niche: bizNiche,
        audience: bizAudience,
        monetization: bizMonetization,
        budget: bizBudget,
      });
      setShowBusinessWizard(false);
      setBizName('');
      setBizNiche('');
      loadProjects();
    } catch (e: any) {
      alert(`Erro: ${e.message}`);
    }
  };

  const handleOpenProject = async (id: string) => {
    try {
      const details = await api.getProject(id);
      setSelectedProject(details);
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleDeleteProject = async (id: string) => {
    if (!confirm('Tem certeza que deseja excluir este projeto?')) return;
    await api.deleteProject(id);
    if (selectedProject?.id === id) setSelectedProject(null);
    loadProjects();
  };

  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingProject) return;
    await api.updateProject(editingProject.id, {
      name: editingProject.name,
      description: editingProject.description,
      priority: editingProject.priority,
      status: editingProject.status,
    });
    setEditingProject(null);
    loadProjects();
  };

  const handleAddTaskToProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProject || !newTaskTitle.trim()) return;
    await api.createTask({
      title: newTaskTitle,
      assigned_agent_id: newTaskAgent,
      project_id: selectedProject.id,
    });
    setNewTaskTitle('');
    await handleOpenProject(selectedProject.id);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold text-white">Hub de Projetos & Negócios</h2>
          <p className="text-sm text-slate-400">Gerenciamento executivo de iniciativas digitais autônomas.</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => setShowBusinessWizard(true)}
            className="px-4 py-2.5 bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-500 hover:to-amber-400 text-white font-medium rounded-xl text-sm transition shadow-lg shadow-amber-600/30 flex items-center space-x-2"
          >
            <Rocket className="w-4 h-4" />
            <span>+ Criar Novo Negócio Digital</span>
          </button>
          <button
            onClick={() => setShowNewProjectModal(true)}
            className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-xl text-sm transition shadow-lg shadow-indigo-600/30 flex items-center space-x-2"
          >
            <Plus className="w-4 h-4" />
            <span>+ Novo Projeto</span>
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-slate-400 text-sm py-12 text-center">Carregando projetos...</div>
      ) : projects.length === 0 ? (
        <div className="p-12 text-center bg-slate-900/60 rounded-2xl border border-slate-800">
          <Briefcase className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-slate-300">Nenhum projeto registrado</h3>
          <p className="text-sm text-slate-500 mt-1 max-w-md mx-auto">
            Inicie um novo projeto ou clique no botão acima para criar um negócio digital com o CEO Jeffrey.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {projects.map((p) => (
            <div
              key={p.id}
              className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 hover:border-slate-700 transition shadow-md flex flex-col justify-between"
            >
              <div>
                <div className="flex justify-between items-start">
                  <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-slate-800 text-indigo-400 border border-slate-700">
                    {p.project_type}
                  </span>
                  <span className="text-xs text-emerald-400 font-medium capitalize flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-emerald-400" />
                    {p.status}
                  </span>
                </div>
                <h3 className="text-lg font-bold text-white mt-3">{p.name}</h3>
                <p className="text-xs text-slate-400 mt-1.5 line-clamp-3 leading-relaxed">{p.description}</p>
              </div>

              <div className="mt-5 pt-4 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
                <span>Líder: <b className="text-slate-300 capitalize">{p.lead_agent_id}</b></span>
                <div className="flex items-center gap-1.5">
                  <button onClick={() => handleOpenProject(p.id)} className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200" title="Detalhes">
                    <Eye className="w-3.5 h-3.5" />
                  </button>
                  <button onClick={() => setEditingProject({ ...p })} className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-indigo-300" title="Editar">
                    <Edit3 className="w-3.5 h-3.5" />
                  </button>
                  <button onClick={() => handleDeleteProject(p.id)} className="p-1.5 rounded-lg bg-rose-950/60 hover:bg-rose-900 text-rose-300" title="Excluir">
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {showNewProjectModal && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl">
            <div className="flex justify-between items-center pb-4 border-b border-slate-800">
              <h3 className="text-lg font-bold text-white">Criar Novo Projeto</h3>
              <button onClick={() => setShowNewProjectModal(false)} className="text-slate-400 hover:text-white"><X className="w-5 h-5" /></button>
            </div>
            <form onSubmit={handleCreateProject} className="mt-4 space-y-4">
              <div>
                <label className="text-xs font-semibold text-slate-300">Nome do Projeto</label>
                <input type="text" required value={name} onChange={(e) => setName(e.target.value)} className="w-full mt-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-sm text-white" />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-300">Tipo de Projeto</label>
                <select value={type} onChange={(e) => setType(e.target.value)} className="w-full mt-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-sm text-white">
                  <option value="software">Desenvolvimento de Software</option>
                  <option value="content">Produção de Conteúdo (YouTube/TikTok)</option>
                  <option value="audiovisual">Clipagem e Edição Audiovisual</option>
                  <option value="business">Novo Negócio Digital</option>
                </select>
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-300">Descrição e Objetivos</label>
                <textarea required rows={3} value={desc} onChange={(e) => setDesc(e.target.value)} className="w-full mt-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-sm text-white" />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setShowNewProjectModal(false)} className="px-4 py-2 bg-slate-800 text-slate-300 rounded-xl text-sm">Cancelar</button>
                <button type="submit" className="px-5 py-2 bg-indigo-600 text-white rounded-xl text-sm font-semibold">Criar e Iniciar</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showBusinessWizard && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-xl bg-slate-900 border border-amber-500/40 rounded-2xl p-6 shadow-2xl">
            <div className="flex justify-between items-center pb-4 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <Rocket className="w-5 h-5 text-amber-400" />
                <h3 className="text-lg font-bold text-white">Criar Novo Negócio Digital</h3>
              </div>
              <button onClick={() => setShowBusinessWizard(false)} className="text-slate-400 hover:text-white"><X className="w-5 h-5" /></button>
            </div>
            <form onSubmit={handleCreateBusiness} className="mt-4 space-y-4">
              <input type="text" required placeholder="Nome do Negócio" value={bizName} onChange={(e) => setBizName(e.target.value)} className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-sm text-white" />
              <div className="grid grid-cols-2 gap-3">
                <input type="text" required placeholder="Nicho" value={bizNiche} onChange={(e) => setBizNiche(e.target.value)} className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-sm text-white" />
                <input type="text" required placeholder="Público-Alvo" value={bizAudience} onChange={(e) => setBizAudience(e.target.value)} className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-sm text-white" />
              </div>
              <input type="text" value={bizMonetization} onChange={(e) => setBizMonetization(e.target.value)} className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-sm text-white" />
              <input type="text" value={bizBudget} onChange={(e) => setBizBudget(e.target.value)} className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-sm text-white" />
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setShowBusinessWizard(false)} className="px-4 py-2 bg-slate-800 text-slate-300 rounded-xl text-sm">Cancelar</button>
                <button type="submit" className="px-5 py-2 bg-amber-600 text-white rounded-xl text-sm font-semibold">Lançar Negócio</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {selectedProject && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-2xl max-h-[85vh] bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl flex flex-col">
            <div className="flex justify-between items-center pb-3 border-b border-slate-800">
              <div>
                <h3 className="text-lg font-bold text-white">{selectedProject.name}</h3>
                <span className="text-xs text-indigo-400 uppercase">{selectedProject.project_type} • {selectedProject.status}</span>
              </div>
              <button onClick={() => setSelectedProject(null)} className="text-slate-400 hover:text-white"><X className="w-5 h-5" /></button>
            </div>
            <div className="mt-4 space-y-4 overflow-y-auto text-xs pr-1">
              <p className="text-slate-300">{selectedProject.description}</p>
              <form onSubmit={handleAddTaskToProject} className="flex gap-2">
                <input type="text" value={newTaskTitle} onChange={(e) => setNewTaskTitle(e.target.value)} placeholder="Nova tarefa no projeto..." className="flex-1 px-3 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-white" />
                <select value={newTaskAgent} onChange={(e) => setNewTaskAgent(e.target.value)} className="px-2 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-white">
                  <option value="jeffrey">Jeffrey</option>
                  <option value="noe">Noé</option>
                  <option value="balsini">Balsini</option>
                  <option value="fonseca">Fonseca</option>
                  <option value="murphy">Murphy</option>
                </select>
                <button type="submit" className="px-3 py-1.5 bg-indigo-600 text-white rounded-lg font-semibold">+ Tarefa</button>
              </form>
              <div>
                <div className="font-semibold text-slate-400 uppercase mb-1">Tarefas ({selectedProject.tasks?.length || 0})</div>
                {(selectedProject.tasks || []).map((t: any) => (
                  <div key={t.id} className="p-2 rounded bg-slate-950 border border-slate-800 flex justify-between mb-1">
                    <span className="text-white">{t.title}</span>
                    <span className="text-indigo-300 font-mono">{t.assigned_agent} • {t.status}</span>
                  </div>
                ))}
              </div>
              <div>
                <div className="font-semibold text-slate-400 uppercase mb-1">Workflows ({selectedProject.workflows?.length || 0})</div>
                {(selectedProject.workflows || []).map((w: any) => (
                  <div key={w.id} className="p-2 rounded bg-slate-950 border border-slate-800 flex justify-between mb-1">
                    <span className="text-white">{w.title}</span>
                    <span className="text-emerald-400 font-mono">{w.status}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {editingProject && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl">
            <h3 className="text-base font-bold text-white mb-4">Editar Projeto</h3>
            <form onSubmit={handleSaveEdit} className="space-y-3 text-xs">
              <input type="text" required value={editingProject.name} onChange={(e) => setEditingProject({ ...editingProject, name: e.target.value })} className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-white" />
              <textarea rows={3} value={editingProject.description} onChange={(e) => setEditingProject({ ...editingProject, description: e.target.value })} className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-white" />
              <div className="grid grid-cols-2 gap-2">
                <select value={editingProject.priority} onChange={(e) => setEditingProject({ ...editingProject, priority: e.target.value })} className="px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-white">
                  <option value="low">low</option>
                  <option value="medium">medium</option>
                  <option value="high">high</option>
                  <option value="urgent">urgent</option>
                </select>
                <select value={editingProject.status} onChange={(e) => setEditingProject({ ...editingProject, status: e.target.value })} className="px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-white">
                  <option value="active">active</option>
                  <option value="paused">paused</option>
                  <option value="completed">completed</option>
                  <option value="archived">archived</option>
                </select>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setEditingProject(null)} className="px-4 py-2 bg-slate-800 text-slate-300 rounded-xl">Cancelar</button>
                <button type="submit" className="px-4 py-2 bg-indigo-600 text-white rounded-xl font-semibold">Salvar</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
