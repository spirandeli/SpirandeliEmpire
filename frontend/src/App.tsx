import React, { useState, useEffect } from 'react';
import {
  Building2, LayoutDashboard, MessageSquare, Briefcase,
  Users, GitFork, ShieldAlert, Key, FileText, Bell,
  PanelLeftClose, PanelLeftOpen, Cpu, UserCog, LogOut, CheckSquare, Menu, X, WifiOff
} from 'lucide-react';
import { VirtualOffice } from './office/VirtualOffice';
import { DashboardView } from './dashboard/DashboardView';
import { ChatView } from './chat/ChatView';
import { ProjectsView } from './projects/ProjectsView';
import { TasksView } from './tasks/TasksView';
import { AgentsView } from './agents/AgentsView';
import { WorkflowsView } from './workflows/WorkflowsView';
import { ApprovalsView } from './approvals/ApprovalsView';
import { IntegrationsView } from './integrations/IntegrationsView';
import { ArtifactsView } from './artifacts/ArtifactsView';
import { AuthView, FirstAccessSetupView } from './auth/AuthView';
import { AIProvidersView } from './ai/AIProvidersView';
import { AIModelManagerView } from './ai/AIModelManagerView';
import { ProfileSecurityView } from './profile/ProfileSecurityView';
import { ErrorBoundary } from './components/ErrorBoundary';
import { api, liveEvents, setAuthToken } from './services/api';

export const App: React.FC = () => {
  const [currentUser, setCurrentUser] = useState<any | null>(null);
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [activeTab, setActiveTab] = useState<string>('office');
  const [notifications, setNotifications] = useState<string[]>([]);
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);
  const [isOffline, setIsOffline] = useState<boolean>(!navigator.onLine);

  const loadCurrentUser = async () => {
    try {
      const me = await api.getMe();
      setCurrentUser(me);
    } catch {
      setCurrentUser(null);
    } finally {
      setCheckingAuth(false);
    }
  };

  useEffect(() => {
    loadCurrentUser();
    const onUnauthorized = () => setCurrentUser(null);
    const onOnline = () => setIsOffline(false);
    const onOffline = () => setIsOffline(true);
    window.addEventListener('spirandeli:unauthorized', onUnauthorized);
    window.addEventListener('online', onOnline);
    window.addEventListener('offline', onOffline);
    return () => {
      window.removeEventListener('spirandeli:unauthorized', onUnauthorized);
      window.removeEventListener('online', onOnline);
      window.removeEventListener('offline', onOffline);
    };
  }, []);

  useEffect(() => {
    if (!currentUser || currentUser.must_change_password) return;
    liveEvents.connect();
    const unsub = liveEvents.subscribe((event) => {
      let msg = '';
      if (event.event_type === 'AgentStarted') {
        msg = `Agente ${event.payload?.agent || event.agent_id} iniciou: ${event.payload?.action || event.payload?.task || ''}`;
      } else if (event.event_type === 'WorkflowStarted') {
        msg = `Workflow iniciado: ${event.payload?.title || event.workflow_id}`;
      } else if (event.event_type === 'WorkflowCompleted') {
        msg = `Workflow concluído com sucesso pelo Jeffrey!`;
      } else if (event.event_type === 'AgentWaitingApproval') {
        msg = `Atenção: aprovação necessária para ${event.payload?.action_name}`;
      }
      if (msg) {
        setNotifications((prev) => [msg, ...prev.slice(0, 4)]);
      }
    });
    return () => unsub();
  }, [currentUser]);

  const handleLogout = async () => {
    try {
      await api.logout();
    } catch {
      // ignore
    }
    setAuthToken(null);
    setCurrentUser(null);
  };

  if (checkingAuth) {
    return (
      <div className="min-h-screen bg-[#0B0F19] text-slate-400 flex items-center justify-center text-sm">
        Inicializando SpirandeliEmpire OS 3.2...
      </div>
    );
  }

  if (!currentUser) {
    return <AuthView onAuthenticated={(u) => setCurrentUser(u)} />;
  }

  if (currentUser.must_change_password) {
    return (
      <FirstAccessSetupView
        user={currentUser}
        onCompleted={() => loadCurrentUser()}
        onLogout={handleLogout}
      />
    );
  }

  const navItems = [
    { id: 'office', label: 'Escritório Virtual', icon: Building2 },
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'chat', label: 'Chat Jeffrey', icon: MessageSquare },
    { id: 'projects', label: 'Projetos', icon: Briefcase },
    { id: 'tasks', label: 'Tarefas', icon: CheckSquare },
    { id: 'agents', label: '14 Agentes', icon: Users },
    { id: 'workflows', label: 'Workflows', icon: GitFork },
    { id: 'approvals', label: 'Aprovações', icon: ShieldAlert },
    { id: 'ai-providers', label: 'AI Providers', icon: Key },
    { id: 'ai-models', label: 'AI Model Manager', icon: Cpu },
    { id: 'integrations', label: 'Integrações Legacy', icon: Key },
    { id: 'artifacts', label: 'Artefatos', icon: FileText },
    { id: 'profile', label: 'Perfil & Segurança', icon: UserCog },
  ];

  return (
    <div className="min-h-screen bg-[#0B0F19] text-gray-100 flex flex-col">
      {/* Top Header */}
      <header className="sticky top-0 z-40 bg-slate-950/80 backdrop-blur-md border-b border-slate-800/80 px-4 sm:px-6 py-2.5 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setSidebarCollapsed((c) => !c)}
            className="hidden md:flex p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white border border-slate-800 transition"
            title={sidebarCollapsed ? 'Expandir menu lateral' : 'Recolher menu lateral'}
          >
            {sidebarCollapsed ? <PanelLeftOpen className="w-4 h-4" /> : <PanelLeftClose className="w-4 h-4" />}
          </button>
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-400 flex items-center justify-center font-black text-white text-sm shadow-lg shadow-indigo-500/20">
            S
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="font-extrabold text-base tracking-tight text-white">SPIRANDELIEMPIRE</h1>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 font-bold border border-indigo-500/30">
                OS 3.2
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-medium">Multi-User AI Digital Company • BYOK</p>
          </div>
        </div>

        {/* Live Notification Toast & User */}
        <div className="flex items-center space-x-2">
          {notifications.length > 0 && (
            <div className="hidden lg:flex px-3 py-1 bg-slate-900 border border-indigo-500/40 rounded-full text-xs text-indigo-300 items-center space-x-1.5 shadow-sm">
              <Bell className="w-3.5 h-3.5 text-indigo-400 animate-bounce" />
              <span className="truncate max-w-xs">{notifications[0]}</span>
            </div>
          )}
          <button
            onClick={() => setActiveTab('profile')}
            className="hidden sm:flex items-center space-x-1.5 text-xs text-slate-300 hover:text-white px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-800"
          >
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span>{currentUser.full_name || currentUser.email}</span>
          </button>
          <button
            onClick={handleLogout}
            className="p-1.5 rounded-lg bg-slate-900 hover:bg-rose-950/60 text-slate-400 hover:text-rose-300 border border-slate-800 transition"
            title="Sair"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Main Layout Container */}
      <div className={`flex-1 flex flex-col md:flex-row w-full mx-auto gap-4 ${activeTab === 'office' ? 'max-w-none p-2 sm:p-3' : 'max-w-7xl p-4 sm:p-6 gap-6'}`}>
        {!sidebarCollapsed && (
          <nav className="hidden md:flex flex-col w-56 space-y-1 shrink-0">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`flex items-center space-x-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition ${
                    isActive
                      ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30 font-semibold'
                      : 'text-slate-400 hover:text-white hover:bg-slate-900/80'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>
        )}

        <main className="flex-1 min-w-0 pb-16 md:pb-0">
          <ErrorBoundary fallbackTitle="Erro ao carregar o módulo">
            {activeTab === 'office' && <VirtualOffice onOpenChatWithJeffrey={() => setActiveTab('chat')} />}
            {activeTab === 'dashboard' && <DashboardView onNavigate={(tab) => setActiveTab(tab)} />}
            {activeTab === 'chat' && <ChatView onNavigateToWorkflow={() => setActiveTab('workflows')} />}
            {activeTab === 'projects' && <ProjectsView />}
            {activeTab === 'tasks' && <TasksView />}
            {activeTab === 'agents' && <AgentsView />}
            {activeTab === 'workflows' && <WorkflowsView />}
            {activeTab === 'approvals' && <ApprovalsView />}
            {activeTab === 'ai-providers' && <AIProvidersView />}
            {activeTab === 'ai-models' && <AIModelManagerView />}
            {activeTab === 'integrations' && <IntegrationsView />}
            {activeTab === 'artifacts' && <ArtifactsView />}
            {activeTab === 'profile' && <ProfileSecurityView currentUser={currentUser} onUserUpdated={loadCurrentUser} />}
          </ErrorBoundary>
        </main>
      </div>

      {/* Offline Banner */}
      {isOffline && (
        <div className="bg-amber-950/90 border-b border-amber-700 px-4 py-1.5 text-xs text-amber-200 flex items-center justify-center gap-2">
          <WifiOff className="w-3.5 h-3.5" />
          <span>Modo offline: apenas a interface em cache está disponível. Ações de IA requerem conexão.</span>
        </div>
      )}

      {/* Mobile Bottom Nav + Full Menu Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-end">
          <div className="w-full bg-slate-900 border-t border-slate-800 rounded-t-2xl p-4 max-h-[75vh] overflow-y-auto">
            <div className="flex justify-between items-center pb-3 mb-3 border-b border-slate-800">
              <span className="text-sm font-bold text-white">Todos os Módulos</span>
              <button onClick={() => setMobileMenuOpen(false)} className="p-1 text-slate-400 hover:text-white"><X className="w-5 h-5" /></button>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => { setActiveTab(item.id); setMobileMenuOpen(false); }}
                    className={`flex flex-col items-center p-3 rounded-xl text-xs font-medium border ${
                      isActive ? 'bg-indigo-600 text-white border-indigo-500' : 'bg-slate-950 text-slate-300 border-slate-800'
                    }`}
                  >
                    <Icon className="w-4 h-4 mb-1" />
                    <span className="text-center leading-tight">{item.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}

      <div className="md:hidden fixed bottom-0 inset-x-0 bg-slate-950/95 backdrop-blur-lg border-t border-slate-800/80 px-2 py-1.5 flex justify-around items-center z-40">
        {navItems.slice(0, 4).map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`flex flex-col items-center justify-center py-1 px-2 rounded-lg text-[10px] font-medium transition ${
                isActive ? 'text-indigo-400 font-bold' : 'text-slate-400'
              }`}
            >
              <Icon className="w-4 h-4 mb-0.5" />
              <span>{item.label.split(' ')[0]}</span>
            </button>
          );
        })}
        <button
          onClick={() => setMobileMenuOpen(true)}
          className="flex flex-col items-center justify-center py-1 px-2 rounded-lg text-[10px] font-medium text-slate-400 hover:text-white"
        >
          <Menu className="w-4 h-4 mb-0.5" />
          <span>Mais</span>
        </button>
      </div>
    </div>
  );
};
