import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Key, RefreshCw, CheckCircle2, AlertCircle, Plus, Trash2, Shield, Lock, X } from 'lucide-react';

const PROVIDERS = [
  { id: 'gemini', name: 'Google Gemini', badge: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30' },
  { id: 'openai', name: 'OpenAI', badge: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' },
  { id: 'anthropic', name: 'Anthropic Claude', badge: 'bg-amber-500/20 text-amber-300 border-amber-500/30' },
];

export const AIProvidersView: React.FC = () => {
  const [connections, setConnections] = useState<any[]>([]);
  const [modelsByCred, setModelsByCred] = useState<Record<string, number>>({});
  const [modalProvider, setModalProvider] = useState<string | null>(null);
  const [label, setLabel] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [workspaceOrg, setWorkspaceOrg] = useState('');
  const [isDefault, setIsDefault] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<Record<string, { ok: boolean; msg: string }>>({});

  const loadData = async () => {
    try {
      const [conns, models] = await Promise.all([api.listConnections(), api.listModels()]);
      setConnections(conns);
      const counts: Record<string, number> = {};
      models.forEach((m: any) => {
        counts[m.credential_id] = (counts[m.credential_id] || 0) + 1;
      });
      setModelsByCred(counts);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!modalProvider) return;
    try {
      const created = await api.createConnection({
        provider: modalProvider,
        label: label || `Minha conta ${modalProvider}`,
        api_key: apiKey,
        workspace_org: workspaceOrg || undefined,
        is_default: isDefault,
      });
      setModalProvider(null);
      setLabel('');
      setApiKey('');
      setWorkspaceOrg('');
      await loadData();
      // Auto-sync catalog after adding key
      await handleSync(created.id);
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleTest = async (id: string) => {
    setBusyId(id);
    try {
      const res = await api.testConnection(id);
      setFeedback((prev) => ({ ...prev, [id]: { ok: res.success, msg: `${res.status}: ${res.message} (${res.latency_ms}ms)` } }));
      await loadData();
    } catch (err: any) {
      setFeedback((prev) => ({ ...prev, [id]: { ok: false, msg: err.message } }));
    } finally {
      setBusyId(null);
    }
  };

  const handleSync = async (id: string) => {
    setBusyId(id);
    try {
      const res = await api.syncCredentialModels(id, true);
      setFeedback((prev) => ({ ...prev, [id]: { ok: true, msg: `${res.models_count} modelos sincronizados.` } }));
      await loadData();
    } catch (err: any) {
      setFeedback((prev) => ({ ...prev, [id]: { ok: false, msg: err.message } }));
    } finally {
      setBusyId(null);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Remover esta credencial e seu catálogo de modelos?')) return;
    await api.deleteConnection(id);
    await loadData();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            AI Providers Hub (BYOK)
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 flex items-center gap-1 font-mono">
              <Lock className="w-3 h-3" /> AES-256-GCM
            </span>
          </h2>
          <p className="text-sm text-slate-400">Gerencie suas chaves individuais de Gemini, OpenAI e Anthropic Claude com isolamento por usuário.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {PROVIDERS.map((prov) => {
          const provConns = connections.filter((c) => c.provider === prov.id);
          return (
            <div key={prov.id} className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 flex flex-col justify-between space-y-4">
              <div>
                <div className="flex justify-between items-center pb-3 border-b border-slate-800">
                  <div>
                    <h3 className="text-lg font-bold text-white">{prov.name}</h3>
                    <span className={`inline-block mt-1 text-[10px] px-2 py-0.5 rounded-full border font-mono uppercase ${prov.badge}`}>
                      {provConns.length} {provConns.length === 1 ? 'conexão' : 'conexões'}
                    </span>
                  </div>
                  <button
                    onClick={() => { setModalProvider(prov.id); setLabel(`Conta ${prov.name}`); }}
                    className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold flex items-center gap-1"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Adicionar Chave</span>
                  </button>
                </div>

                {provConns.length === 0 ? (
                  <div className="py-8 text-center text-xs text-slate-500">
                    Nenhuma chave configurada para {prov.name}.
                  </div>
                ) : (
                  <div className="mt-3 space-y-3">
                    {provConns.map((c) => (
                      <div key={c.id} className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800 space-y-2">
                        <div className="flex justify-between items-start">
                          <div>
                            <div className="text-sm font-bold text-white flex items-center gap-1.5">
                              <span>{c.label}</span>
                              {c.is_default && (
                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300">Padrão</span>
                              )}
                            </div>
                            <div className="text-xs font-mono text-slate-400 mt-0.5">{c.masked_key}</div>
                          </div>
                          <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${
                            c.status === 'connected' || c.status === 'active'
                              ? 'bg-emerald-500/20 text-emerald-400'
                              : 'bg-amber-500/20 text-amber-300'
                          }`}>
                            {c.status}
                          </span>
                        </div>

                        <div className="flex items-center justify-between text-[11px] text-slate-400">
                          <span>Modelos descobertos: <b className="text-white">{modelsByCred[c.id] || 0}</b></span>
                          {c.last_latency_ms != null && <span>{c.last_latency_ms}ms</span>}
                        </div>

                        {feedback[c.id] && (
                          <div className={`p-2 rounded-lg text-[11px] flex items-center gap-1.5 ${
                            feedback[c.id].ok ? 'bg-emerald-950/50 text-emerald-300' : 'bg-rose-950/50 text-rose-300'
                          }`}>
                            {feedback[c.id].ok ? <CheckCircle2 className="w-3.5 h-3.5 shrink-0" /> : <AlertCircle className="w-3.5 h-3.5 shrink-0" />}
                            <span>{feedback[c.id].msg}</span>
                          </div>
                        )}

                        <div className="flex flex-wrap gap-1.5 pt-1">
                          <button
                            onClick={() => handleTest(c.id)}
                            disabled={busyId === c.id}
                            className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-[11px] font-medium flex items-center gap-1"
                          >
                            <Shield className="w-3 h-3" /> Testar conexão
                          </button>
                          <button
                            onClick={() => handleSync(c.id)}
                            disabled={busyId === c.id}
                            className="px-2.5 py-1 bg-indigo-950/80 hover:bg-indigo-900 text-indigo-200 border border-indigo-700/50 rounded-lg text-[11px] font-medium flex items-center gap-1"
                          >
                            <RefreshCw className={`w-3 h-3 ${busyId === c.id ? 'animate-spin' : ''}`} /> Atualizar modelos
                          </button>
                          <button
                            onClick={() => handleDelete(c.id)}
                            className="px-2 py-1 bg-rose-950/50 hover:bg-rose-900 text-rose-300 rounded-lg text-[11px]"
                            title="Excluir"
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {modalProvider && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl">
            <div className="flex justify-between items-center pb-3 border-b border-slate-800">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Key className="w-4 h-4 text-indigo-400" /> Nova Credencial ({modalProvider.toUpperCase()})
              </h3>
              <button onClick={() => setModalProvider(null)} className="text-slate-400 hover:text-white"><X className="w-5 h-5" /></button>
            </div>
            <form onSubmit={handleCreate} className="mt-4 space-y-3">
              <div>
                <label className="text-xs font-semibold text-slate-300">Nome identificador da conexão</label>
                <input
                  type="text"
                  required
                  value={label}
                  onChange={(e) => setLabel(e.target.value)}
                  className="w-full mt-1 px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-sm text-white"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-300">API Key (armazenada criptografada)</label>
                <input
                  type="password"
                  required
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="Cole sua API Key aqui..."
                  className="w-full mt-1 px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-sm text-white font-mono"
                />
              </div>
              {modalProvider === 'openai' && (
                <div>
                  <label className="text-xs font-semibold text-slate-300">Organization / Workspace (Opcional)</label>
                  <input
                    type="text"
                    value={workspaceOrg}
                    onChange={(e) => setWorkspaceOrg(e.target.value)}
                    className="w-full mt-1 px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-sm text-white font-mono"
                  />
                </div>
              )}
              <label className="flex items-center gap-2 text-xs text-slate-300">
                <input type="checkbox" checked={isDefault} onChange={(e) => setIsDefault(e.target.checked)} />
                <span>Definir como conexão padrão deste provedor</span>
              </label>
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setModalProvider(null)} className="px-4 py-2 bg-slate-800 text-slate-300 rounded-xl text-xs">Cancelar</button>
                <button type="submit" className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold">Salvar & Sincronizar</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

