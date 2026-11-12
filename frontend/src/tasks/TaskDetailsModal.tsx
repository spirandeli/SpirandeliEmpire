import React from 'react';
import {
  X,
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  User,
  GitFork,
  Folder,
  FileText,
  Calendar,
  Layers,
  Sparkles,
  RefreshCw,
  Copy,
  Check,
} from 'lucide-react';

export interface TaskData {
  id: string;
  project_id?: string;
  workflow_id?: string;
  title: string;
  description?: string;
  assigned_agent: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'blocked' | 'waiting_approval' | string;
  priority: 'low' | 'medium' | 'high' | 'urgent' | string;
  quality_score?: number | null;
  result_summary?: string | null;
  artifacts?: string[];
  dependencies?: string[];
  attempts?: number;
  approvals_required?: boolean;
  created_at?: string;
  updated_at?: string;
}

interface TaskDetailsModalProps {
  task: TaskData | null;
  onClose: () => void;
  onStatusChange?: (id: string, newStatus: string) => Promise<void>;
}

export const TaskDetailsModal: React.FC<TaskDetailsModalProps> = ({
  task,
  onClose,
  onStatusChange,
}) => {
  const [copied, setCopied] = React.useState(false);
  const [updatingStatus, setUpdatingStatus] = React.useState(false);

  if (!task) return null;

  const handleCopyId = () => {
    navigator.clipboard.writeText(task.id);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleStatusSelect = async (newStatus: string) => {
    if (!onStatusChange) return;
    setUpdatingStatus(true);
    try {
      await onStatusChange(task.id, newStatus);
    } finally {
      setUpdatingStatus(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="w-3.5 h-3.5" /> Concluída
          </span>
        );
      case 'in_progress':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
            <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Em Execução
          </span>
        );
      case 'failed':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/20 text-rose-400 border border-rose-500/30">
            <XCircle className="w-3.5 h-3.5" /> Falhou
          </span>
        );
      case 'waiting_approval':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-400 border border-amber-500/30">
            <AlertTriangle className="w-3.5 h-3.5" /> Aguardando Aprovação
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700">
            <Clock className="w-3.5 h-3.5" /> {status}
          </span>
        );
    }
  };

  const getPriorityBadge = (priority: string) => {
    switch (priority) {
      case 'urgent':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-rose-950/80 text-rose-400 border border-rose-800">Urgente</span>;
      case 'high':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-amber-950/80 text-amber-400 border border-amber-800">Alta</span>;
      case 'medium':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-indigo-950/80 text-indigo-400 border border-indigo-800">Média</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-slate-800 text-slate-400">Baixa</span>;
    }
  };

  const formatDate = (isoString?: string) => {
    if (!isoString) return '—';
    try {
      const d = new Date(isoString);
      return d.toLocaleString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  const isFailed = task.status === 'failed';
  const hasResult = Boolean(task.result_summary && task.result_summary.trim());

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-3xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in duration-200">
        {/* Modal Header */}
        <div className="p-5 border-b border-slate-800 flex items-start justify-between gap-4 bg-slate-900/95 sticky top-0 z-10">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2 mb-2">
              {getStatusBadge(task.status)}
              {getPriorityBadge(task.priority)}
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-900/40 text-indigo-300 border border-indigo-700/50">
                <User className="w-3 h-3" /> Agente: <b className="capitalize">{task.assigned_agent}</b>
              </span>
            </div>
            <h3 className="text-xl font-bold text-white leading-snug">{task.title}</h3>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-xl transition"
            title="Fechar"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 overflow-y-auto space-y-6 text-slate-300 text-sm">
          {/* Metadata Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3.5 bg-slate-950/60 rounded-xl border border-slate-800/80 text-xs">
            <div>
              <span className="text-slate-500 block">ID da Tarefa:</span>
              <div className="flex items-center gap-1 font-mono text-slate-300 mt-0.5 truncate">
                <span className="truncate">{task.id.slice(0, 8)}...</span>
                <button onClick={handleCopyId} className="text-slate-400 hover:text-white" title="Copiar ID">
                  {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                </button>
              </div>
            </div>

            <div>
              <span className="text-slate-500 block">Workflow:</span>
              <span className="font-mono text-indigo-300 mt-0.5 block truncate">
                {task.workflow_id ? `${task.workflow_id.slice(0, 8)}...` : 'Nenhum'}
              </span>
            </div>

            <div>
              <span className="text-slate-500 block">Criado em:</span>
              <span className="text-slate-300 mt-0.5 block">{formatDate(task.created_at)}</span>
            </div>

            <div>
              <span className="text-slate-500 block">Tentativas:</span>
              <span className="text-slate-300 mt-0.5 block">{task.attempts ?? 1}</span>
            </div>
          </div>

          {/* Description / Goal */}
          {task.description && task.description.trim() && (
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5 flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-indigo-400" />
                Descrição / Objetivo da Tarefa
              </h4>
              <div className="p-3.5 bg-slate-950/40 rounded-xl border border-slate-800/80 text-slate-300 text-xs leading-relaxed whitespace-pre-wrap">
                {task.description}
              </div>
            </div>
          )}

          {/* SECTION: "O QUE FOI FEITO" */}
          <div className="space-y-2">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-white">
                <Sparkles className="w-4 h-4 text-emerald-400" />
                O que foi feito (Relatório do Agente)
              </span>
              {task.quality_score !== null && task.quality_score !== undefined && (
                <span className="text-xs text-emerald-400 font-bold">
                  Quality Score: {(task.quality_score * 100).toFixed(0)}%
                </span>
              )}
            </h4>

            {isFailed ? (
              <div className="p-4 bg-rose-950/40 border border-rose-800/80 rounded-xl text-xs space-y-2">
                <div className="flex items-center gap-2 font-bold text-rose-300">
                  <AlertTriangle className="w-4 h-4 text-rose-400" />
                  Falha Registrada na Execução
                </div>
                <div className="font-mono text-rose-200 bg-black/40 p-3 rounded-lg border border-rose-900/50 whitespace-pre-wrap">
                  {task.result_summary || 'O agente falhou sem registrar detalhes do erro.'}
                </div>
                <p className="text-rose-400/90 text-[11px]">
                  Dica: Se a falha ocorreu por oscilação de provedor de IA ou limite de taxa (Rate Limit), verifique suas chaves de API nas configurações ou tente reexecutar a tarefa.
                </p>
              </div>
            ) : hasResult ? (
              <div className="p-4 bg-slate-950/70 border border-slate-800 rounded-xl space-y-2">
                <div className="text-xs text-slate-300 leading-relaxed font-sans whitespace-pre-wrap">
                  {task.result_summary}
                </div>
              </div>
            ) : (
              <div className="p-8 text-center bg-slate-950/40 border border-slate-800/60 rounded-xl text-slate-400 text-xs">
                {task.status === 'in_progress' ? (
                  <div className="flex flex-col items-center gap-2">
                    <RefreshCw className="w-5 h-5 text-indigo-400 animate-spin" />
                    <span>O agente <b className="capitalize text-indigo-300">{task.assigned_agent}</b> está executando esta tarefa no momento...</span>
                  </div>
                ) : (
                  <span>Nenhum relatório de execução gerado ainda. A tarefa aguarda processamento.</span>
                )}
              </div>
            )}
          </div>

          {/* Artifacts Created */}
          {task.artifacts && task.artifacts.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-cyan-400" />
                Entregas & Artefatos Gerados ({task.artifacts.length})
              </h4>
              <div className="space-y-1.5">
                {task.artifacts.map((art, idx) => (
                  <div key={idx} className="p-2.5 bg-slate-950/60 border border-slate-800 rounded-xl flex items-center justify-between text-xs font-mono">
                    <span className="text-slate-300 truncate">{art}</span>
                    <span className="text-slate-500 text-[10px]">armazenado</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Dependencies */}
          {task.dependencies && task.dependencies.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1 flex items-center gap-1.5">
                <GitFork className="w-3.5 h-3.5 text-slate-400" />
                Dependências Pré-Requisito
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {task.dependencies.map((depId, idx) => (
                  <span key={idx} className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[11px] font-mono">
                    {depId}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/95 flex flex-col sm:flex-row justify-between items-center gap-3">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span>Alterar status:</span>
            <select
              value={task.status}
              disabled={updatingStatus || !onStatusChange}
              onChange={(e) => handleStatusSelect(e.target.value)}
              className="px-2.5 py-1 bg-slate-950 border border-slate-700 rounded-lg text-xs text-white disabled:opacity-50"
            >
              <option value="pending">Pendente</option>
              <option value="in_progress">Em andamento</option>
              <option value="completed">Concluída</option>
              <option value="failed">Falhou</option>
              <option value="waiting_approval">Aguardando aprovação</option>
            </select>
          </div>

          <button
            onClick={onClose}
            className="w-full sm:w-auto px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-semibold transition"
          >
            Fechar
          </button>
        </div>
      </div>
    </div>
  );
};

