import React, { useEffect, useState } from 'react';
import { api, liveEvents } from '../services/api';
import { 
  Briefcase, CheckSquare, GitFork, Users, ShieldAlert, Cpu, 
  HardDrive, Activity, Plus, Sparkles, FileText, Zap 
} from 'lucide-react';

interface DashboardViewProps {
  onNavigate: (tab: string) => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({ onNavigate }) => {
  const [metrics, setMetrics] = useState<any>(null);
  const [projectsCount, setProjectsCount] = useState(0);
  const [tasksCount, setTasksCount] = useState(0);
  const [workflowsCount, setWorkflowsCount] = useState(0);
  const [agentsCount, setAgentsCount] = useState(0);
  const [pendingApprovalsCount, setPendingApprovalsCount] = useState(0);
  const [artifactsCount, setArtifactsCount] = useState(0);
  const [usageTotals, setUsageTotals] = useState<any>({ requests: 0, total_tokens: 0 });

  const loadData = async () => {
    try {
      const [sys, prjs, tsks, wfs, ags, apps, arts, usg] = await Promise.all([
        api.getSystemMetrics().catch(() => null),
        api.getProjects().catch(() => []),
        api.getTasks().catch(() => []),
        api.getWorkflows().catch(() => []),
        api.getAgents().catch(() => []),
        api.getApprovals('pending').catch(() => []),
        api.getArtifacts().catch(() => []),
        api.getUsageSummary().catch(() => ({ totals: { requests: 0, total_tokens: 0 } })),
      ]);
      setMetrics(sys);
      setProjectsCount(prjs.length);
      setTasksCount(tsks.length);
      setWorkflowsCount(wfs.length);
      setAgentsCount(ags.length);
      setPendingApprovalsCount(apps.length);
      setArtifactsCount(arts.length);
      setUsageTotals(usg?.totals || { requests: 0, total_tokens: 0 });
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000);
    const unsub = liveEvents.subscribe(() => loadData());
    return () => {
      clearInterval(interval);
      unsub();
    };
  }, []);

  return (
    <div className="space-y-6">
      {/* Top Welcome Banner */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-indigo-900/60 via-slate-900 to-slate-900 border border-indigo-800/40 shadow-xl flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
              SpirandeliEmpire OS 3.1
            </span>
            <span className="text-xs text-slate-400">LangGraph Multi-Agent Engine</span>
          </div>
          <h2 className="text-2xl font-bold text-white mt-1">Quartel General Operacional</h2>
          <p className="text-sm text-slate-300 mt-0.5">
            14 agentes de IA especializados operando de forma autônoma sob supervisão do CEO Jeffrey.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onNavigate('chat')}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-medium transition shadow-lg shadow-indigo-600/30 flex items-center space-x-2"
          >
            <Sparkles className="w-4 h-4" />
            <span>Falar com Jeffrey</span>
          </button>
          <button
            onClick={() => onNavigate('projects')}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-xl text-sm font-medium transition flex items-center space-x-2"
          >
            <Plus className="w-4 h-4" />
            <span>Novo Projeto</span>
          </button>
        </div>
      </div>

      {/* KPI Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div 
          onClick={() => onNavigate('projects')}
          className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 hover:border-indigo-500/50 cursor-pointer transition shadow-sm"
        >
          <div className="flex justify-between items-center text-slate-400">
            <span className="text-xs font-medium">Projetos Ativos</span>
            <Briefcase className="w-4 h-4 text-indigo-400" />
          </div>
          <p className="text-2xl font-bold text-white mt-2">{projectsCount}</p>
        </div>

        <div 
          onClick={() => onNavigate('tasks')}
          className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 hover:border-emerald-500/50 cursor-pointer transition shadow-sm"
        >
          <div className="flex justify-between items-center text-slate-400">
            <span className="text-xs font-medium">Tarefas</span>
            <CheckSquare className="w-4 h-4 text-emerald-400" />
          </div>
          <p className="text-2xl font-bold text-white mt-2">{tasksCount}</p>
        </div>

        <div 
          onClick={() => onNavigate('workflows')}
          className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 hover:border-cyan-500/50 cursor-pointer transition shadow-sm"
        >
          <div className="flex justify-between items-center text-slate-400">
            <span className="text-xs font-medium">Workflows</span>
            <GitFork className="w-4 h-4 text-cyan-400" />
          </div>
          <p className="text-2xl font-bold text-white mt-2">{workflowsCount}</p>
        </div>

        <div 
          onClick={() => onNavigate('agents')}
          className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 hover:border-purple-500/50 cursor-pointer transition shadow-sm"
        >
          <div className="flex justify-between items-center text-slate-400">
            <span className="text-xs font-medium">Agentes Oficiais</span>
            <Users className="w-4 h-4 text-purple-400" />
          </div>
          <p className="text-2xl font-bold text-white mt-2">{agentsCount}</p>
        </div>

        <div 
          onClick={() => onNavigate('approvals')}
          className={`p-4 rounded-xl border cursor-pointer transition shadow-sm ${
            pendingApprovalsCount > 0 
              ? 'bg-amber-950/30 border-amber-500/60 animate-pulse' 
              : 'bg-slate-900/90 border-slate-800 hover:border-amber-500/50'
          }`}
        >
          <div className="flex justify-between items-center text-slate-400">
            <span className="text-xs font-medium">Aprovações</span>
            <ShieldAlert className="w-4 h-4 text-amber-400" />
          </div>
          <p className="text-2xl font-bold text-white mt-2">{pendingApprovalsCount}</p>
        </div>

        <div 
          onClick={() => onNavigate('artifacts')}
          className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 hover:border-pink-500/50 cursor-pointer transition shadow-sm"
        >
          <div className="flex justify-between items-center text-slate-400">
            <span className="text-xs font-medium">Artefatos</span>
            <FileText className="w-4 h-4 text-pink-400" />
          </div>
          <p className="text-2xl font-bold text-white mt-2">{artifactsCount}</p>
        </div>

        <div 
          onClick={() => onNavigate('ai-models')}
          className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 hover:border-indigo-500/50 cursor-pointer transition shadow-sm"
        >
          <div className="flex justify-between items-center text-slate-400">
            <span className="text-xs font-medium">Consumo de IA</span>
            <Zap className="w-4 h-4 text-indigo-400" />
          </div>
          <p className="text-xl font-bold text-white mt-2">{usageTotals.total_tokens || 0} tok</p>
          <p className="text-[10px] text-slate-400">{usageTotals.requests || 0} reqs</p>
        </div>
      </div>

      {/* VPS Hardware & Infrastructure Monitor */}
      {metrics && (
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-md">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
            <div className="flex items-center space-x-2">
              <Activity className="w-4 h-4 text-emerald-400" />
              <h3 className="text-sm font-semibold text-slate-200">Recursos da VPS Ubuntu em Tempo Real</h3>
            </div>
            <span className="text-xs text-slate-400">Uptime: {metrics.uptime_seconds}s</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
            {/* CPU */}
            <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800/60">
              <div className="flex justify-between items-center text-xs text-slate-400">
                <span className="flex items-center gap-1.5"><Cpu className="w-3.5 h-3.5 text-indigo-400" /> Uso de CPU</span>
                <span className="font-semibold text-slate-200">{metrics.cpu.percent}%</span>
              </div>
              <div className="w-full bg-slate-800 h-2 rounded-full mt-2 overflow-hidden">
                <div 
                  className={`h-full transition-all duration-500 ${metrics.cpu.percent > 80 ? 'bg-rose-500' : 'bg-indigo-500'}`} 
                  style={{ width: `${Math.min(100, metrics.cpu.percent)}%` }} 
                />
              </div>
            </div>

            {/* RAM */}
            <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800/60">
              <div className="flex justify-between items-center text-xs text-slate-400">
                <span className="flex items-center gap-1.5"><Activity className="w-3.5 h-3.5 text-emerald-400" /> Memória RAM</span>
                <span className="font-semibold text-slate-200">{metrics.memory.percent}%</span>
              </div>
              <div className="w-full bg-slate-800 h-2 rounded-full mt-2 overflow-hidden">
                <div 
                  className={`h-full transition-all duration-500 ${metrics.memory.percent > 85 ? 'bg-rose-500' : 'bg-emerald-500'}`} 
                  style={{ width: `${Math.min(100, metrics.memory.percent)}%` }} 
                />
              </div>
              <p className="text-[10px] text-slate-400 mt-1">{metrics.memory.used_mb}MB / {metrics.memory.total_mb}MB</p>
            </div>

            {/* Disk */}
            <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800/60">
              <div className="flex justify-between items-center text-xs text-slate-400">
                <span className="flex items-center gap-1.5"><HardDrive className="w-3.5 h-3.5 text-cyan-400" /> Armazenamento SSD</span>
                <span className="font-semibold text-slate-200">{metrics.disk.percent}%</span>
              </div>
              <div className="w-full bg-slate-800 h-2 rounded-full mt-2 overflow-hidden">
                <div 
                  className="h-full bg-cyan-500 transition-all duration-500" 
                  style={{ width: `${Math.min(100, metrics.disk.percent)}%` }} 
                />
              </div>
              <p className="text-[10px] text-slate-400 mt-1">{metrics.disk.used_gb}GB / {metrics.disk.total_gb}GB</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

