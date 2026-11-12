import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Cpu, Users, Layers, ShieldAlert, BarChart3, Search, CheckCircle2 } from 'lucide-react';

export const AIModelManagerView: React.FC = () => {
  const [subTab, setSubTab] = useState<'global' | 'agents' | 'tasks' | 'fallback' | 'usage'>('global');
  const [connections, setConnections] = useState<any[]>([]);
  const [models, setModels] = useState<any[]>([]);
  const [globalPref, setGlobalPref] = useState<any>({});
  const [agentConfigs, setAgentConfigs] = useState<any[]>([]);
  const [taskProfiles, setTaskProfiles] = useState<any[]>([]);
  const [fallbackCfg, setFallbackCfg] = useState<{ fallback_enabled: boolean; fallback_chain: any[] }>({
    fallback_enabled: false,
    fallback_chain: [],
  });
  const [usage, setUsage] = useState<any>({ totals: {}, records: [] });
  const [search, setSearch] = useState('');
  const [capFilter, setCapFilter] = useState('');
  const [savedNotice, setSavedNotice] = useState('');

  const loadAll = async () => {
    try {
      const [conns, mods, pref, ags, tps, fb, usg] = await Promise.all([
        api.listConnections(),
        api.listModels(),
        api.getGlobalAISettings(),
        api.listAgentModelConfigs(),
        api.listTaskProfiles(),
        api.getFallbackSettings(),
        api.getUsageSummary(),
      ]);
      setConnections(conns);
      setModels(mods);
      setGlobalPref(pref);
      setAgentConfigs(ags);
      setTaskProfiles(tps);
      setFallbackCfg(fb);
      setUsage(usg);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const flashSaved = (msg: string) => {
    setSavedNotice(msg);
    setTimeout(() => setSavedNotice(''), 3000);
  };

  const handleSaveGlobal = async () => {
    await api.updateGlobalAISettings(globalPref);
    flashSaved('Configuração global salva.');
  };

  const handleUpdateAgent = async (agentId: string, patch: any) => {
    await api.updateAgentModelConfig(agentId, patch);
    flashSaved(`Agente ${agentId} atualizado.`);
    await loadAll();
  };

  const handleUpdateTask = async (profileKey: string, patch: any) => {
    await api.updateTaskProfile(profileKey, patch);
    flashSaved(`Perfil ${profileKey} atualizado.`);
    await loadAll();
  };

  const handleSaveFallback = async () => {
    await api.updateFallbackSettings(fallbackCfg);
    flashSaved('Política de fallback salva.');
  };

  const filteredModels = (provider?: string, credId?: string, chatOnly: boolean = false) =>
    models.filter((m) => {
      if (provider && m.provider !== provider) return false;
      if (credId && m.credential_id !== credId) return false;
      if (chatOnly) {
        if (m.lifecycle_status === 'retired' || m.is_available === false) return false;
        const hasChat = m.capabilities?.some((c: any) => c.capability === 'chat' && c.supported);
        const hasEmbed = m.capabilities?.some((c: any) => c.capability === 'embeddings' && c.supported);
        if (hasEmbed && !hasChat) return false;
      }
      if (search && !m.model_id.toLowerCase().includes(search.toLowerCase()) && !m.display_name.toLowerCase().includes(search.toLowerCase())) return false;
      if (capFilter && !m.capabilities?.some((c: any) => c.capability === capFilter && c.supported)) return false;
      return true;
    });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div>
          <h2 className="text-2xl font-bold text-white">AI Model Manager</h2>
          <p className="text-sm text-slate-400">Seleção dinâmica de modelos por usuário, agente (14 oficiais), perfil de tarefa e fallback.</p>
        </div>
        {savedNotice && (
          <span className="px-3 py-1.5 rounded-xl bg-emerald-950/60 border border-emerald-700 text-emerald-300 text-xs flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4" /> {savedNotice}
          </span>
        )}
      </div>

      {/* Sub-navigation */}
      <div className="flex flex-wrap gap-2">
        {[
          { id: 'global', label: 'Global & Catálogo', icon: Cpu },
          { id: 'agents', label: '14 Agentes', icon: Users },
          { id: 'tasks', label: 'Perfis de Tarefa', icon: Layers },
          { id: 'fallback', label: 'Fallback', icon: ShieldAlert },
          { id: 'usage', label: 'Consumo & Tokens', icon: BarChart3 },
        ].map((t) => {
          const Icon = t.icon;
          return (
            <button
              key={t.id}
              onClick={() => setSubTab(t.id as any)}
              className={`px-3.5 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition ${
                subTab === t.id ? 'bg-indigo-600 text-white' : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
              }`}
            >
              <Icon className="w-3.5 h-3.5" /> {t.label}
            </button>
          );
        })}
      </div>

      {/* Global + Dynamic Catalog */}
      {subTab === 'global' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-4">
            <h3 className="text-base font-bold text-white">Modelo Padrão Global</h3>
            <div>
              <label className="text-xs text-slate-400">Provedor Padrão</label>
              <select
                value={globalPref.default_provider || ''}
                onChange={(e) => setGlobalPref({ ...globalPref, default_provider: e.target.value, default_credential_id: '', default_model_id: '' })}
                className="w-full mt-1 px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-sm text-white"
              >
                <option value="">Selecionar provedor...</option>
                <option value="gemini">Google Gemini</option>
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic Claude</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-400">Conexão</label>
              <select
                value={globalPref.default_credential_id || ''}
                onChange={(e) => setGlobalPref({ ...globalPref, default_credential_id: e.target.value, default_model_id: '' })}
                className="w-full mt-1 px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-sm text-white"
              >
                <option value="">Selecionar conta...</option>
                {connections
                  .filter((c) => !globalPref.default_provider || c.provider === globalPref.default_provider)
                  .map((c) => (
                    <option key={c.id} value={c.id}>{c.label} ({c.provider})</option>
                  ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-400">Modelo Padrão (Dinâmico)</label>
              <select
                value={globalPref.default_model_id || ''}
                onChange={(e) => setGlobalPref({ ...globalPref, default_model_id: e.target.value })}
                className="w-full mt-1 px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-sm text-white font-mono"
              >
                <option value="">Selecionar modelo...</option>
                {filteredModels(globalPref.default_provider, globalPref.default_credential_id, true).map((m) => (
                  <option key={m.id} value={m.model_id}>{m.display_name} ({m.model_id})</option>
                ))}
              </select>
            </div>
            <button onClick={handleSaveGlobal} className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold">
              Salvar Padrão Global
            </button>
          </div>

          <div className="lg:col-span-2 p-5 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-4">
            <div className="flex flex-col sm:flex-row gap-2 justify-between">
              <h3 className="text-base font-bold text-white">Catálogo Dinâmico ({models.length} modelos)</h3>
              <div className="flex gap-2">
                <div className="relative">
                  <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
                  <input
                    type="text"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Pesquisar modelo..."
                    className="pl-8 pr-3 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-xs text-white"
                  />
                </div>
                <select
                  value={capFilter}
                  onChange={(e) => setCapFilter(e.target.value)}
                  className="px-2.5 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-xs text-white"
                >
                  <option value="">Todas capacidades</option>
                  <option value="chat">Chat</option>
                  <option value="reasoning">Reasoning</option>
                  <option value="coding">Coding</option>
                  <option value="function_calling">Function Calling</option>
                  <option value="vision">Vision</option>
                  <option value="embeddings">Embeddings</option>
                </select>
              </div>
            </div>
            <div className="max-h-96 overflow-y-auto space-y-2 pr-1">
              {filteredModels().length === 0 ? (
                <p className="text-xs text-slate-500 py-8 text-center">Nenhum modelo sincronizado. Cadastre e sincronize uma API Key em AI Providers.</p>
              ) : (
                filteredModels().map((m) => (
                  <div key={m.id} className="p-3 rounded-xl bg-slate-950/70 border border-slate-800 flex flex-col sm:flex-row justify-between gap-2">
                    <div>
                      <div className="text-xs font-bold text-white flex items-center gap-2">
                        <span className="uppercase text-[10px] px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300">{m.provider}</span>
                        <span>{m.display_name}</span>
                        {m.lifecycle_status === 'deprecated' && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300">Deprecated</span>
                        )}
                      </div>
                      <div className="text-[11px] font-mono text-slate-400 mt-0.5">{m.model_id}</div>
                    </div>
                    <div className="flex flex-wrap gap-1 items-center">
                      {(m.capabilities || []).filter((c: any) => c.supported).slice(0, 5).map((c: any) => (
                        <span key={c.capability} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                          {c.capability}
                        </span>
                      ))}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* 14 Agents Model Table */}
      {subTab === 'agents' && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/80 text-slate-400 uppercase text-[10px] border-b border-slate-800">
              <tr>
                <th className="p-3.5">Agente</th>
                <th className="p-3.5">Provedor</th>
                <th className="p-3.5">Conexão</th>
                <th className="p-3.5">Modelo</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/70">
              {agentConfigs.map((ag) => {
                const availModels = filteredModels(ag.provider || undefined, ag.credential_id || undefined, true);
                return (
                  <tr key={ag.agent_id} className="hover:bg-slate-800/30">
                    <td className="p-3.5">
                      <div className="font-bold text-white">{ag.agent_name}</div>
                      <div className="text-[11px] text-slate-400">{ag.role}</div>
                    </td>
                    <td className="p-3.5">
                      <select
                        value={ag.provider || ''}
                        onChange={(e) => handleUpdateAgent(ag.agent_id, { provider: e.target.value, credential_id: '', model_id: '' })}
                        className="px-2.5 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-white"
                      >
                        <option value="">Usar padrão / perfil</option>
                        <option value="gemini">Gemini</option>
                        <option value="openai">OpenAI</option>
                        <option value="anthropic">Claude</option>
                      </select>
                    </td>
                    <td className="p-3.5">
                      <select
                        value={ag.credential_id || ''}
                        onChange={(e) => handleUpdateAgent(ag.agent_id, { credential_id: e.target.value })}
                        className="px-2.5 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-white"
                      >
                        <option value="">Auto / Padrão</option>
                        {connections.filter((c) => !ag.provider || c.provider === ag.provider).map((c) => (
                          <option key={c.id} value={c.id}>{c.label}</option>
                        ))}
                      </select>
                    </td>
                    <td className="p-3.5">
                      <select
                        value={ag.model_id || ''}
                        onChange={(e) => {
                          const mId = e.target.value;
                          const found = availModels.find((m) => m.model_id === mId);
                          handleUpdateAgent(ag.agent_id, {
                            model_id: mId,
                            provider: found?.provider || ag.provider || undefined,
                            credential_id: found?.credential_id || ag.credential_id || undefined,
                          });
                        }}
                        className="px-2.5 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-white font-mono max-w-xs"
                      >
                        <option value="">Herdar padrão</option>
                        {availModels.map((m) => (
                          <option key={m.id} value={m.model_id}>{m.model_id}</option>
                        ))}
                      </select>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Task Profiles */}
      {subTab === 'tasks' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {taskProfiles.map((tp) => (
            <div key={tp.profile_key} className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 space-y-2.5">
              <div className="font-bold text-white text-sm">{tp.display_name}</div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <select
                  value={tp.provider || ''}
                  onChange={(e) => handleUpdateTask(tp.profile_key, { provider: e.target.value, model_id: '' })}
                  className="px-2.5 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-white"
                >
                  <option value="">Provedor padrão</option>
                  <option value="gemini">Gemini</option>
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Claude</option>
                </select>
                <select
                  value={tp.model_id || ''}
                  onChange={(e) => handleUpdateTask(tp.profile_key, { model_id: e.target.value })}
                  className="px-2.5 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-white font-mono"
                >
                  <option value="">Herdar padrão</option>
                  {filteredModels(tp.provider || undefined, undefined, true).map((m) => (
                    <option key={m.id} value={m.model_id}>{m.model_id}</option>
                  ))}
                </select>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Fallback */}
      {subTab === 'fallback' && (
        <div className="p-6 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-4 max-w-2xl">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-white">Fallback Configurável</h3>
              <p className="text-xs text-slate-400">Desativado por padrão. Nenhuma troca silenciosa de modelo acontece sem sua autorização.</p>
            </div>
            <label className="flex items-center gap-2 text-xs font-semibold text-white cursor-pointer">
              <input
                type="checkbox"
                checked={fallbackCfg.fallback_enabled}
                onChange={(e) => setFallbackCfg({ ...fallbackCfg, fallback_enabled: e.target.checked })}
              />
              <span>Habilitar Fallback</span>
            </label>
          </div>
          <button
            onClick={() =>
              setFallbackCfg({
                ...fallbackCfg,
                fallback_chain: [...fallbackCfg.fallback_chain, { provider: 'openai', credential_id: '', model_id: '' }],
              })
            }
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs text-white rounded-lg"
          >
            + Adicionar Etapa de Fallback
          </button>
          <div className="space-y-2">
            {fallbackCfg.fallback_chain.map((step, idx) => (
              <div key={idx} className="grid grid-cols-3 gap-2 text-xs">
                <select
                  value={step.provider}
                  onChange={(e) => {
                    const next = [...fallbackCfg.fallback_chain];
                    next[idx] = { ...step, provider: e.target.value };
                    setFallbackCfg({ ...fallbackCfg, fallback_chain: next });
                  }}
                  className="px-2 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-white"
                >
                  <option value="gemini">Gemini</option>
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Claude</option>
                </select>
                <select
                  value={step.credential_id}
                  onChange={(e) => {
                    const next = [...fallbackCfg.fallback_chain];
                    next[idx] = { ...step, credential_id: e.target.value };
                    setFallbackCfg({ ...fallbackCfg, fallback_chain: next });
                  }}
                  className="px-2 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-white"
                >
                  <option value="">Conexão...</option>
                  {connections.filter((c) => c.provider === step.provider).map((c) => (
                    <option key={c.id} value={c.id}>{c.label}</option>
                  ))}
                </select>
                <select
                  value={step.model_id}
                  onChange={(e) => {
                    const next = [...fallbackCfg.fallback_chain];
                    next[idx] = { ...step, model_id: e.target.value };
                    setFallbackCfg({ ...fallbackCfg, fallback_chain: next });
                  }}
                  className="px-2 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-white font-mono"
                >
                  <option value="">Modelo...</option>
                  {filteredModels(step.provider, step.credential_id, true).map((m) => (
                    <option key={m.id} value={m.model_id}>{m.model_id}</option>
                  ))}
                </select>
              </div>
            ))}
          </div>
          <button onClick={handleSaveFallback} className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold">
            Salvar Fallback
          </button>
        </div>
      )}

      {/* Usage */}
      {subTab === 'usage' && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: 'Requisições', val: usage.totals?.requests || 0 },
              { label: 'Tokens de Entrada', val: usage.totals?.input_tokens || 0 },
              { label: 'Tokens de Saída', val: usage.totals?.output_tokens || 0 },
              { label: 'Total de Tokens', val: usage.totals?.total_tokens || 0 },
            ].map((k) => (
              <div key={k.label} className="p-4 rounded-xl bg-slate-900/90 border border-slate-800">
                <div className="text-xs text-slate-400">{k.label}</div>
                <div className="text-2xl font-bold text-white mt-1">{k.val}</div>
              </div>
            ))}
          </div>
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 overflow-x-auto">
            <h3 className="text-sm font-bold text-white mb-3">Histórico Recente de Execuções</h3>
            <table className="w-full text-left text-xs">
              <thead className="text-slate-400 border-b border-slate-800 text-[10px] uppercase">
                <tr>
                  <th className="py-2">Agente</th>
                  <th className="py-2">Provedor / Modelo</th>
                  <th className="py-2">Tokens</th>
                  <th className="py-2">Latência</th>
                  <th className="py-2">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {(usage.records || []).map((r: any) => (
                  <tr key={r.id}>
                    <td className="py-2 text-white font-semibold">{r.agent_id || 'system'}</td>
                    <td className="py-2 font-mono text-slate-300">{r.provider} / {r.model_id}</td>
                    <td className="py-2 text-slate-300">{r.total_tokens}</td>
                    <td className="py-2 text-slate-400">{r.duration_ms}ms</td>
                    <td className="py-2">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        r.status === 'success' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-300'
                      }`}>{r.status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

