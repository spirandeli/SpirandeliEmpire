import React, { useState } from 'react';
import { api, setAuthToken } from '../services/api';
import { Lock, Mail, User, Eye, EyeOff, ShieldCheck, KeyRound, AlertCircle, CheckCircle2 } from 'lucide-react';

interface AuthViewProps {
  onAuthenticated: (user: any) => void;
}

export const AuthView: React.FC<AuthViewProps> = ({ onAuthenticated }) => {
  const [mode, setMode] = useState<'login' | 'register' | 'forgot' | 'reset'>('login');
  const [identifier, setIdentifier] = useState('');
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [inviteCode, setInviteCode] = useState('');
  const [acceptTerms, setAcceptTerms] = useState(true);
  const [rememberMe, setRememberMe] = useState(true);
  const [resetToken, setResetToken] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await api.login(identifier, password, rememberMe);
      setAuthToken(res.access_token, rememberMe);
      onAuthenticated(res.user);
    } catch (err: any) {
      setError(err.message || 'Falha na autenticação.');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (password !== confirmPassword) {
      setError('As senhas não conferem.');
      return;
    }
    setLoading(true);
    try {
      await api.register({
        full_name: fullName,
        email,
        password,
        confirm_password: confirmPassword,
        accept_terms: acceptTerms,
        invite_code: inviteCode || undefined,
      });
      setInfo('Conta criada com sucesso! Faça login para continuar.');
      setMode('login');
      setIdentifier(email);
      setPassword('');
    } catch (err: any) {
      setError(err.message || 'Erro ao criar conta.');
    } finally {
      setLoading(false);
    }
  };

  const handleForgot = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await api.forgotPassword(email);
      setInfo(res.message || 'Instruções enviadas.');
      if (res.dev_reset_token) {
        setResetToken(res.dev_reset_token);
        setMode('reset');
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.resetPassword({ token: resetToken, new_password: password, confirm_password: confirmPassword });
      setInfo('Senha redefinida com sucesso. Faça login.');
      setMode('login');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0B0F19] text-gray-100 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-slate-900/90 border border-slate-800 rounded-2xl p-7 shadow-2xl">
        <div className="flex items-center space-x-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-400 flex items-center justify-center font-black text-white text-lg">
            S
          </div>
          <div>
            <h1 className="font-extrabold text-lg text-white">SPIRANDELIEMPIRE OS 3.2</h1>
            <p className="text-xs text-slate-400">Multi-User AI Platform • BYOK & Model Manager</p>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-rose-950/60 border border-rose-700/60 text-rose-200 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
        )}
        {info && (
          <div className="mb-4 p-3 rounded-xl bg-emerald-950/60 border border-emerald-700/60 text-emerald-200 text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
            <span>{info}</span>
          </div>
        )}

        {mode === 'login' && (
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="text-xs font-semibold text-slate-300">E-mail ou Usuário</label>
              <div className="relative mt-1">
                <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type="text"
                  required
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  placeholder="seu@email.com"
                  className="w-full pl-9 pr-3 py-2.5 bg-slate-950 border border-slate-700 rounded-xl text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-300">Senha</label>
              <div className="relative mt-1">
                <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-9 pr-10 py-2.5 bg-slate-950 border border-slate-700 rounded-xl text-sm text-white focus:outline-none focus:border-indigo-500"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((s) => !s)}
                  className="absolute right-3 top-2.5 text-slate-400 hover:text-white"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
            <div className="flex items-center justify-between text-xs">
              <label className="flex items-center gap-2 text-slate-400 cursor-pointer">
                <input type="checkbox" checked={rememberMe} onChange={(e) => setRememberMe(e.target.checked)} className="rounded" />
                <span>Lembrar sessão</span>
              </label>
              <button type="button" onClick={() => { setMode('forgot'); setError(null); }} className="text-indigo-400 hover:text-indigo-300">
                Esqueci minha senha
              </button>
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-xl text-sm font-semibold transition"
            >
              {loading ? 'Autenticando...' : 'Entrar no Sistema'}
            </button>
            <div className="text-center text-xs text-slate-400 pt-2">
              Não tem conta?{' '}
              <button type="button" onClick={() => { setMode('register'); setError(null); }} className="text-indigo-400 hover:text-indigo-300 font-semibold">
                Criar Conta
              </button>
            </div>
          </form>
        )}

        {mode === 'register' && (
          <form onSubmit={handleRegister} className="space-y-3">
            <div>
              <label className="text-xs font-semibold text-slate-300">Nome Completo</label>
              <div className="relative mt-1">
                <User className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-sm text-white"
                />
              </div>
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-300">E-mail</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full mt-1 px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-sm text-white"
              />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs font-semibold text-slate-300">Senha (mín. 8)</label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full mt-1 px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-sm text-white"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-300">Confirmar</label>
                <input
                  type="password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full mt-1 px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-sm text-white"
                />
              </div>
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-300">Código de Convite (se exigido)</label>
              <input
                type="text"
                value={inviteCode}
                onChange={(e) => setInviteCode(e.target.value)}
                placeholder="Opcional"
                className="w-full mt-1 px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-sm text-white"
              />
            </div>
            <label className="flex items-center gap-2 text-xs text-slate-400">
              <input type="checkbox" checked={acceptTerms} onChange={(e) => setAcceptTerms(e.target.checked)} />
              <span>Aceito os termos de uso e isolamento de dados.</span>
            </label>
            <button type="submit" disabled={loading} className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold">
              {loading ? 'Cadastrando...' : 'Criar Conta'}
            </button>
            <div className="text-center text-xs text-slate-400">
              Já possui conta?{' '}
              <button type="button" onClick={() => setMode('login')} className="text-indigo-400 font-semibold">
                Voltar ao Login
              </button>
            </div>
          </form>
        )}

        {mode === 'forgot' && (
          <form onSubmit={handleForgot} className="space-y-4">
            <p className="text-xs text-slate-400">Informe seu e-mail para gerar o token de recuperação de senha.</p>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="seu@email.com"
              className="w-full px-3 py-2.5 bg-slate-950 border border-slate-700 rounded-xl text-sm text-white"
            />
            <button type="submit" disabled={loading} className="w-full py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-semibold">
              Enviar Recuperação
            </button>
            <button type="button" onClick={() => setMode('login')} className="w-full text-xs text-slate-400">
              Voltar
            </button>
          </form>
        )}

        {mode === 'reset' && (
          <form onSubmit={handleReset} className="space-y-3">
            <input
              type="text"
              required
              value={resetToken}
              onChange={(e) => setResetToken(e.target.value)}
              placeholder="Token de recuperação"
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-sm text-white font-mono"
            />
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Nova senha"
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-sm text-white"
            />
            <input
              type="password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Confirmar nova senha"
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-sm text-white"
            />
            <button type="submit" disabled={loading} className="w-full py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-semibold">
              Redefinir Senha
            </button>
          </form>
        )}
      </div>
    </div>
  );
};

interface FirstAccessProps {
  user: any;
  onCompleted: () => void;
  onLogout: () => void;
}

export const FirstAccessSetupView: React.FC<FirstAccessProps> = ({ user, onCompleted, onLogout }) => {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      onCompleted();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0B0F19] text-gray-100 flex items-center justify-center p-4">
      <div className="w-full max-w-lg bg-slate-900 border border-amber-500/40 rounded-2xl p-7 shadow-2xl space-y-5">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-amber-500/20 text-amber-400">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">Configuração Inicial de Segurança</h2>
            <p className="text-xs text-slate-400">
              Conta: <b className="text-slate-200">{user.email}</b> ({user.role})
            </p>
          </div>
        </div>
        <p className="text-xs text-amber-200/90 bg-amber-950/40 border border-amber-800/50 p-3 rounded-xl">
          Por segurança, a senha provisória deve ser substituída por uma senha forte (mínimo 12 caracteres, maiúsculas, minúsculas, números e símbolo) antes de liberar o painel administrativo.
        </p>
        {error && (
          <div className="p-3 rounded-xl bg-rose-950/60 border border-rose-700 text-rose-200 text-xs">{error}</div>
        )}
        <form onSubmit={handleSubmit} className="space-y-3">
          <input
            type="password"
            required
            placeholder="Senha provisória atual"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            className="w-full px-3 py-2.5 bg-slate-950 border border-slate-700 rounded-xl text-sm text-white"
          />
          <input
            type="password"
            required
            placeholder="Nova senha forte (mín. 12 caracteres)"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className="w-full px-3 py-2.5 bg-slate-950 border border-slate-700 rounded-xl text-sm text-white"
          />
          <input
            type="password"
            required
            placeholder="Confirmar nova senha"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="w-full px-3 py-2.5 bg-slate-950 border border-slate-700 rounded-xl text-sm text-white"
          />
          <div className="flex justify-between items-center pt-2">
            <button type="button" onClick={onLogout} className="text-xs text-slate-400 hover:text-white">
              Sair
            </button>
            <button type="submit" disabled={loading} className="px-5 py-2.5 bg-amber-600 hover:bg-amber-500 text-white rounded-xl text-sm font-semibold flex items-center gap-2">
              <KeyRound className="w-4 h-4" />
              <span>{loading ? 'Atualizando...' : 'Atualizar Senha e Acessar'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

