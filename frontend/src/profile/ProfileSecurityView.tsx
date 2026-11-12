import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { User, Shield, KeyRound, MonitorSmartphone, Trash2, Users } from 'lucide-react';

interface ProfileSecurityViewProps {
  currentUser: any;
  onUserUpdated: () => void;
}

export const ProfileSecurityView: React.FC<ProfileSecurityViewProps> = ({ currentUser, onUserUpdated }) => {
  const [fullName, setFullName] = useState(currentUser?.full_name || '');
  const [currPw, setCurrPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [confPw, setConfPw] = useState('');
  const [sessions, setSessions] = useState<any[]>([]);
  const [adminUsers, setAdminUsers] = useState<any[]>([]);
  const [regMode, setRegMode] = useState('public');
  const [inviteCode, setInviteCode] = useState('');
  const [msg, setMsg] = useState('');

  const isAdmin = ['ADMIN', 'OWNER'].includes((currentUser?.role || '').toUpperCase());

  const loadData = async () => {
    try {
      const sess = await api.getSessions();
      setSessions(sess);
      if (isAdmin) {
        const [usrs, pol] = await Promise.all([api.adminListUsers(), api.adminGetPolicies()]);
        setAdminUsers(usrs);
        setRegMode(pol.registration_mode);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    await api.updateProfile(fullName);
    setMsg('Perfil atualizado.');
    onUserUpdated();
  };

  const handleChangePw = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.changePassword({ current_password: currPw, new_password: newPw, confirm_password: confPw });
      setCurrPw('');
      setNewPw('');
      setConfPw('');
      setMsg('Senha alterada e sessões antigas revogadas.');
      await loadData();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleRevokeSession = async (id: string) => {
    await api.revokeSession(id);
    await loadData();
  };

  const handlePolicyChange = async (mode: string) => {
    await api.adminUpdatePolicies(mode);
    setRegMode(mode);
    setMsg('Política de cadastro atualizada.');
  };

  const handleCreateInvite = async () => {
    const res = await api.adminCreateInvite();
    setInviteCode(res.invite_code);
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white">Meu Perfil & Segurança</h2>
        <p className="text-sm text-slate-400">Gerencie sua conta, senha, sessões ativas e políticas administrativas.</p>
      </div>

      {msg && (
        <div className="p-3 rounded-xl bg-emerald-950/60 border border-emerald-700 text-emerald-300 text-xs">{msg}</div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <form onSubmit={handleSaveProfile} className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-3">
          <h3 className="text-base font-bold text-white flex items-center gap-2"><User className="w-4 h-4 text-indigo-400" /> Dados do Perfil</h3>
          <div className="text-xs text-slate-400">E-mail: <b className="text-white">{currentUser?.email}</b> • Perfil: <b className="text-indigo-300">{currentUser?.role}</b></div>
          <input
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-sm text-white"
          />
          <button type="submit" className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold">
            Salvar Perfil
          </button>
        </form>

        <form onSubmit={handleChangePw} className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-3">
          <h3 className="text-base font-bold text-white flex items-center gap-2"><KeyRound className="w-4 h-4 text-amber-400" /> Alterar Senha</h3>
          <input type="password" required placeholder="Senha atual" value={currPw} onChange={(e) => setCurrPw(e.target.value)} className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-xs text-white" />
          <div className="grid grid-cols-2 gap-2">
            <input type="password" required placeholder="Nova senha" value={newPw} onChange={(e) => setNewPw(e.target.value)} className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-xs text-white" />
            <input type="password" required placeholder="Confirmar" value={confPw} onChange={(e) => setConfPw(e.target.value)} className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-xs text-white" />
          </div>
          <button type="submit" className="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded-xl text-xs font-semibold">
            Atualizar Senha
          </button>
        </form>
      </div>

      {/* Sessions */}
      <div className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-3">
        <h3 className="text-base font-bold text-white flex items-center gap-2"><MonitorSmartphone className="w-4 h-4 text-cyan-400" /> Sessões Ativas e Histórico</h3>
        <div className="space-y-2">
          {sessions.map((s) => (
            <div key={s.id} className="p-3 rounded-xl bg-slate-950/70 border border-slate-800 flex justify-between items-center text-xs">
              <div>
                <div className="text-white font-mono">{s.ip_address || 'IP local'} • {s.is_revoked ? 'Revogada' : 'Ativa'}</div>
                <div className="text-[11px] text-slate-400 truncate max-w-md">{s.user_agent}</div>
              </div>
              {!s.is_revoked && (
                <button onClick={() => handleRevokeSession(s.id)} className="px-2.5 py-1 bg-rose-950/60 text-rose-300 rounded-lg flex items-center gap-1">
                  <Trash2 className="w-3 h-3" /> Encerrar
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Admin Section */}
      {isAdmin && (
        <div className="p-5 rounded-2xl bg-slate-900/90 border border-indigo-800/50 space-y-4">
          <h3 className="text-base font-bold text-white flex items-center gap-2"><Shield className="w-4 h-4 text-indigo-400" /> Administração de Usuários e Políticas</h3>
          <div className="flex flex-wrap items-center gap-3 text-xs">
            <span className="text-slate-400">Política de Cadastro:</span>
            {['public', 'invite_only', 'disabled'].map((m) => (
              <button
                key={m}
                onClick={() => handlePolicyChange(m)}
                className={`px-3 py-1 rounded-lg font-semibold ${regMode === m ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-300'}`}
              >
                {m}
              </button>
            ))}
            <button onClick={handleCreateInvite} className="px-3 py-1 bg-emerald-700 hover:bg-emerald-600 text-white rounded-lg font-semibold">
              Gerar Convite
            </button>
            {inviteCode && <span className="font-mono text-emerald-300 bg-emerald-950/60 px-2 py-1 rounded">{inviteCode}</span>}
          </div>
          <div className="space-y-2">
            <div className="text-xs font-semibold text-slate-400 flex items-center gap-1.5"><Users className="w-3.5 h-3.5" /> Contas Cadastradas ({adminUsers.length})</div>
            {adminUsers.map((u) => (
              <div key={u.id} className="p-3 rounded-xl bg-slate-950/70 border border-slate-800 flex justify-between items-center text-xs">
                <div>
                  <span className="font-bold text-white">{u.full_name}</span> <span className="text-slate-400">({u.email})</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-mono">{u.role}</span>
                  <button
                    onClick={() => api.adminUpdateUser(u.id, { is_active: !u.is_active }).then(loadData)}
                    className={`px-2.5 py-1 rounded-lg ${u.is_active ? 'bg-emerald-950 text-emerald-300' : 'bg-rose-950 text-rose-300'}`}
                  >
                    {u.is_active ? 'Ativo' : 'Inativo'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

