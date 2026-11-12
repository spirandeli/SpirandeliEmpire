import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Key, ShieldCheck, RefreshCw, CheckCircle2, AlertCircle, Lock } from 'lucide-react';

export const IntegrationsView: React.FC = () => {
  const [integrations, setIntegrations] = useState<any[]>([]);
  const [inputKeys, setInputKeys] = useState<Record<string, string>>({});
  const [testingId, setTestingId] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);

  const loadIntegrations = async () => {
    try {
      const data = await api.getIntegrations();
      setIntegrations(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadIntegrations();
  }, []);

  const handleSave = async (id: string) => {
    const val = inputKeys[id];
    if (val === undefined) return;
    try {
      await api.saveIntegrationCredentials(id, val);
      setInputKeys({ ...inputKeys, [id]: '' });
      loadIntegrations();
    } catch (e: any) {
      alert(`Erro: ${e.message}`);
    }
  };

  const handleTest = async (id: string) => {
    setTestingId(id);
    try {
      const res = await api.testIntegration(id);
      setTestResults({ ...testResults, [id]: res });
      loadIntegrations();
    } catch (e: any) {
      setTestResults({ ...testResults, [id]: { success: false, error: e.message } });
    } finally {
      setTestingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
          Integration Hub
          <span className="text-xs px-2.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 flex items-center gap-1 font-mono">
            <Lock className="w-3 h-3" /> Encriptação Fernet AES-256
          </span>
        </h2>
        <p className="text-sm text-slate-400">
          Cadastre e teste credenciais de APIs externas diretamente pela interface. Secrets são encriptados em repouso.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {integrations.map((item) => (
          <div
            key={item.id}
            className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 shadow-md flex flex-col justify-between"
          >
            <div>
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="text-lg font-bold text-white">{item.name}</h3>
                  <span className="text-xs font-mono text-indigo-400 uppercase">{item.provider}</span>
                </div>
                <span className={`text-xs px-2.5 py-0.5 rounded-full font-bold capitalize ${
                  item.status === 'active' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-slate-800 text-slate-400'
                }`}>
                  {item.status}
                </span>
              </div>

              <div className="mt-4">
                <label className="text-xs font-semibold text-slate-400 uppercase">
                  Credencial / Chave de API
                </label>
                <div className="mt-1 flex items-center space-x-2">
                  <input
                    type="password"
                    placeholder={item.masked_key || 'Insira a chave da API...'}
                    value={inputKeys[item.id] || ''}
                    onChange={(e) => setInputKeys({ ...inputKeys, [item.id]: e.target.value })}
                    className="flex-1 px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono"
                  />
                  <button
                    onClick={() => handleSave(item.id)}
                    className="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold transition"
                  >
                    Salvar
                  </button>
                </div>
                {item.masked_key && (
                  <p className="text-[11px] text-slate-400 mt-1 font-mono">
                    Chave ativa: <span className="text-emerald-400">{item.masked_key}</span>
                  </p>
                )}
              </div>

              {testResults[item.id] && (
                <div className={`mt-3 p-3 rounded-xl text-xs flex items-center space-x-2 ${
                  testResults[item.id].success ? 'bg-emerald-950/40 text-emerald-300 border border-emerald-800' : 'bg-rose-950/40 text-rose-300 border border-rose-800'
                }`}>
                  {testResults[item.id].success ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <AlertCircle className="w-4 h-4 text-rose-400" />}
                  <span>{testResults[item.id].message || testResults[item.id].error}</span>
                </div>
              )}
            </div>

            <div className="mt-5 pt-3 border-t border-slate-800/80 flex items-center justify-between">
              <span className="text-xs text-slate-500">
                {item.last_tested_at ? `Testado em: ${item.last_tested_at.slice(11, 19)}` : 'Não testado'}
              </span>
              <button
                onClick={() => handleTest(item.id)}
                disabled={testingId === item.id}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg text-xs font-medium transition flex items-center space-x-1.5"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${testingId === item.id ? 'animate-spin' : ''}`} />
                <span>Testar Conexão</span>
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

