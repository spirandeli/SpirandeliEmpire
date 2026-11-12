import React, { useEffect, useRef, useState } from 'react';
import Phaser from 'phaser';
import { OfficeScene, AgentVisualData } from './OfficeScene';
import { api, liveEvents } from '../services/api';
import {
  X,
  Play,
  Sparkles,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Minimize2,
  Compass,
  Users,
  MessageSquare,
  RotateCcw,
} from 'lucide-react';

interface VirtualOfficeProps {
  onOpenChatWithJeffrey?: () => void;
}

const ROOM_SHORTCUTS = [
  { id: 'all', label: 'Tudo' },
  { id: 'ceo', label: 'CEO' },
  { id: 'dev', label: 'Dev' },
  { id: 'infra', label: 'Infra' },
  { id: 'content', label: 'Conteúdo' },
  { id: 'meeting', label: 'Reunião' },
  { id: 'qa', label: 'QA' },
  { id: 'audiovisual', label: 'Studio AV' },
  { id: 'lounge', label: 'Lounge' },
];

export const VirtualOffice: React.FC<VirtualOfficeProps> = ({ onOpenChatWithJeffrey }) => {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const gameRef = useRef<Phaser.Game | null>(null);
  const sceneRef = useRef<OfficeScene | null>(null);

  const [agentsList, setAgentsList] = useState<any[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<any | null>(null);
  const [hoveredAgent, setHoveredAgent] = useState<{ data: AgentVisualData; x: number; y: number } | null>(null);
  const [loadingAgent, setLoadingAgent] = useState(false);
  const [taskInput, setTaskInput] = useState('');
  const [actionFeedback, setActionFeedback] = useState('');
  const [phaserError, setPhaserError] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [inMeeting, setInMeeting] = useState(false);

  useEffect(() => {
    if (!containerRef.current || gameRef.current) return;

    try {
      const scene = new OfficeScene();
      scene.setAgentClickHandler(async (agentId: string) => {
        setLoadingAgent(true);
        try {
          const [data, realTasks] = await Promise.all([
            api.getAgent(agentId),
            api.getTasks({ agent_id: agentId }).catch(() => []),
          ]);
          setSelectedAgent({ ...data, assigned_tasks: realTasks });
        } catch (e) {
          console.error('Error fetching agent details:', e);
        } finally {
          setLoadingAgent(false);
        }
      });

      scene.setAgentHoverHandler((agent, sx, sy) => {
        if (!agent) {
          setHoveredAgent(null);
        } else {
          setHoveredAgent({ data: agent, x: sx, y: sy });
        }
      });

      scene.setSceneReadyHandler(() => {
        api.getAgents()
          .then((list) => {
            setAgentsList(list);
            scene.setInitialAgentStates(list);
          })
          .catch(() => {});
      });

      sceneRef.current = scene;

      const rect = containerRef.current.getBoundingClientRect();
      const config: Phaser.Types.Core.GameConfig = {
        type: Phaser.AUTO,
        parent: containerRef.current,
        width: Math.max(320, Math.floor(rect.width || window.innerWidth)),
        height: Math.max(420, Math.floor(rect.height || 680)),
        backgroundColor: '#0B0F19',
        pixelArt: true,
        roundPixels: true,
        antialias: false,
        scene: [scene],
        scale: {
          mode: Phaser.Scale.RESIZE,
          autoCenter: Phaser.Scale.CENTER_BOTH,
        },
      };

      const game = new Phaser.Game(config);
      gameRef.current = game;
    } catch (err: any) {
      console.error('Phaser initialization error:', err);
      setPhaserError(err.message || 'Erro ao inicializar visualização gráfica.');
    }

    const unsubscribe = liveEvents.subscribe((event) => {
      if (!event.agent_id || !sceneRef.current) return;
      const s = sceneRef.current;
      if (event.event_type === 'AgentStarted') {
        s.updateAgentVisualState(event.agent_id, 'Working');
      } else if (event.event_type === 'AgentThinking') {
        s.updateAgentVisualState(event.agent_id, 'Planning');
      } else if (event.event_type === 'AgentCompleted' || event.event_type === 'TaskCompleted') {
        s.updateAgentVisualState(event.agent_id, 'Completed');
      } else if (event.event_type === 'AgentWaitingApproval') {
        s.updateAgentVisualState(event.agent_id, 'Waiting');
      } else if (event.event_type === 'TaskAssigned') {
        s.updateAgentVisualState(event.agent_id, 'Working');
      } else if (event.event_type === 'AgentFailed') {
        s.updateAgentVisualState(event.agent_id, 'error');
      }
    });

    const handleFsChange = () => {
      setIsFullscreen(Boolean(document.fullscreenElement));
    };
    document.addEventListener('fullscreenchange', handleFsChange);

    return () => {
      document.removeEventListener('fullscreenchange', handleFsChange);
      unsubscribe();
      if (gameRef.current) {
        gameRef.current.destroy(true);
        gameRef.current = null;
        sceneRef.current = null;
      }
    };
  }, []);

  const toggleFullscreen = () => {
    if (!wrapperRef.current) return;
    if (!document.fullscreenElement) {
      wrapperRef.current.requestFullscreen?.().catch(() => {});
    } else {
      document.exitFullscreen?.().catch(() => {});
    }
  };

  const handleToggleMeeting = () => {
    if (!sceneRef.current) return;
    if (!inMeeting) {
      sceneRef.current.summonAllHandsMeeting();
      setInMeeting(true);
    } else {
      sceneRef.current.dismissToDesks();
      setInMeeting(false);
    }
  };

  const handleAssignDirectTask = async () => {
    if (!taskInput.trim() || !selectedAgent) return;
    setActionFeedback('Enviando tarefa...');
    try {
      await api.startWorkflow({
        user_request: `Tarefa direta para ${selectedAgent.name}: ${taskInput}`,
        workflow_type: 'supervisor',
      });
      setActionFeedback('✓ Tarefa delegada com sucesso pelo CEO Jeffrey!');
      setTaskInput('');
      sceneRef.current?.updateAgentVisualState(selectedAgent.id, 'Working');
      setTimeout(() => setActionFeedback(''), 4000);
    } catch (e: any) {
      setActionFeedback(`Erro: ${e.message}`);
    }
  };

  const activeCount = agentsList.filter((a) => (a.operational_state || 'idle').toLowerCase() !== 'idle').length;

  return (
    <div
      ref={wrapperRef}
      className="relative w-full h-[calc(100vh-110px)] min-h-[540px] bg-[#0B0F19] rounded-2xl overflow-hidden border border-slate-800/90 shadow-2xl select-none"
    >
      {phaserError ? (
        <div className="w-full h-full flex flex-col items-center justify-center p-8 text-center text-slate-400">
          <p className="text-sm font-semibold text-rose-400">Ambiente WebGL em modo de compatibilidade.</p>
          <p className="text-xs text-slate-500 mt-1">{phaserError}</p>
        </div>
      ) : (
        <div
          ref={containerRef}
          className="w-full h-full cursor-grab active:cursor-grabbing"
          style={{ imageRendering: 'pixelated' }}
        />
      )}

      {/* Top Floating HUD: Status + Quick Department Camera Shortcuts */}
      <div className="absolute top-3 left-3 right-3 flex flex-wrap items-center justify-between gap-2 pointer-events-none z-20">
        <div className="pointer-events-auto flex items-center gap-1.5 bg-slate-950/85 backdrop-blur-md px-2.5 py-1.5 rounded-xl border border-slate-700/70 shadow-lg overflow-x-auto max-w-full">
          <span className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400 pr-2 border-r border-slate-700/70 shrink-0">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>14 Agentes</span>
            {activeCount > 0 && (
              <span className="px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 text-[10px]">
                {activeCount} ativos
              </span>
            )}
          </span>
          <div className="flex items-center gap-1 overflow-x-auto">
            {ROOM_SHORTCUTS.map((r) => (
              <button
                key={r.id}
                onClick={() => sceneRef.current?.focusOnRoom(r.id)}
                className="px-2 py-1 rounded-lg text-[11px] font-medium text-slate-300 hover:text-white hover:bg-slate-800 transition shrink-0"
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>

        {/* Top-Right Action Controls */}
        <div className="pointer-events-auto flex items-center gap-1.5">
          <button
            onClick={handleToggleMeeting}
            className={`px-2.5 py-1.5 rounded-xl text-xs font-semibold border shadow-lg backdrop-blur-md flex items-center gap-1.5 transition ${
              inMeeting
                ? 'bg-amber-500/20 border-amber-400/50 text-amber-200 hover:bg-amber-500/30'
                : 'bg-slate-950/85 border-slate-700/70 text-slate-200 hover:bg-slate-800'
            }`}
            title="Convocar ou encerrar reunião na Sala de Reunião"
          >
            {inMeeting ? <RotateCcw className="w-3.5 h-3.5" /> : <Users className="w-3.5 h-3.5 text-amber-400" />}
            <span className="hidden sm:inline">{inMeeting ? 'Voltar às Mesas' : 'Reunião Geral'}</span>
          </button>

          {onOpenChatWithJeffrey && (
            <button
              onClick={onOpenChatWithJeffrey}
              className="px-2.5 py-1.5 rounded-xl text-xs font-semibold bg-indigo-600/90 hover:bg-indigo-500 text-white border border-indigo-400/40 shadow-lg backdrop-blur-md flex items-center gap-1.5 transition"
            >
              <MessageSquare className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Chat Jeffrey</span>
            </button>
          )}

          <button
            onClick={toggleFullscreen}
            className="p-1.5 rounded-xl bg-slate-950/85 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-700/70 shadow-lg backdrop-blur-md transition"
            title={isFullscreen ? 'Sair da tela cheia' : 'Tela cheia'}
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Bottom-Right Camera Controls */}
      <div className="absolute bottom-3 right-3 flex flex-col gap-1.5 z-20">
        <button
          onClick={() => sceneRef.current?.zoomIn()}
          className="p-2 rounded-xl bg-slate-950/85 hover:bg-slate-800 text-slate-200 border border-slate-700/70 shadow-lg backdrop-blur-md transition"
          title="Aproximar zoom"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          onClick={() => sceneRef.current?.zoomOut()}
          className="p-2 rounded-xl bg-slate-950/85 hover:bg-slate-800 text-slate-200 border border-slate-700/70 shadow-lg backdrop-blur-md transition"
          title="Afastar zoom"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <button
          onClick={() => sceneRef.current?.resetCamera()}
          className="p-2 rounded-xl bg-slate-950/85 hover:bg-slate-800 text-indigo-300 border border-slate-700/70 shadow-lg backdrop-blur-md transition"
          title="Centralizar escritório"
        >
          <Compass className="w-4 h-4" />
        </button>
      </div>

      {/* Pixel-Art Hover Tooltip */}
      {hoveredAgent && !selectedAgent && (
        <div
          className="absolute pointer-events-none z-30 bg-slate-950/95 border border-indigo-500/50 rounded-lg px-2.5 py-1.5 shadow-xl text-xs"
          style={{
            left: Math.min(Math.max(12, hoveredAgent.x + 14), (containerRef.current?.clientWidth || 800) - 200),
            top: Math.max(56, hoveredAgent.y - 44),
          }}
        >
          <div className="font-bold text-white leading-tight">{hoveredAgent.data.name}</div>
          <div className="text-[10px] text-slate-400">{hoveredAgent.data.role}</div>
          <div className="mt-1 inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 text-[10px] font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span>{hoveredAgent.data.state}</span>
          </div>
        </div>
      )}

      {/* Agent Detail Side Drawer / Mobile Bottom Sheet */}
      {selectedAgent && (
        <div className="absolute inset-x-0 bottom-0 md:inset-x-auto md:inset-y-0 md:right-0 w-full md:max-w-sm max-h-[75vh] md:max-h-none bg-slate-950/95 backdrop-blur-xl border-t md:border-t-0 md:border-l border-slate-700/80 p-5 flex flex-col shadow-2xl z-30 rounded-t-2xl md:rounded-none">
          <div className="flex justify-between items-start pb-4 border-b border-slate-800">
            <div className="flex items-center gap-3">
              <img
                src={`/sprites/agents/${selectedAgent.id.replace('_', '-')}/avatar.png`}
                alt={selectedAgent.name}
                className="w-14 h-14 rounded-xl bg-slate-900 border border-indigo-500/40 p-1 shrink-0"
                style={{ imageRendering: 'pixelated' }}
              />
              <div>
                <span className="text-[10px] uppercase tracking-wider text-indigo-400 font-semibold">
                  {selectedAgent.department}
                </span>
                <h3 className="text-lg font-bold text-white leading-tight">{selectedAgent.name}</h3>
                <p className="text-xs text-slate-400">{selectedAgent.role}</p>
              </div>
            </div>
            <button
              onClick={() => setSelectedAgent(null)}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {loadingAgent ? (
            <div className="py-8 text-center text-xs text-slate-400">Carregando dados do agente...</div>
          ) : (
            <div className="mt-4 space-y-4 text-sm overflow-y-auto pr-1 flex-1">
              <div>
                <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">Especialidade</h4>
                <p className="text-slate-200 text-xs mt-1 leading-relaxed">{selectedAgent.specialty}</p>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-2.5">
                  <h4 className="text-[10px] font-semibold text-slate-400 uppercase">Status</h4>
                  <div className="mt-1 flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                    <span className="capitalize text-xs font-semibold text-emerald-400">
                      {selectedAgent.operational_state || 'idle'}
                    </span>
                  </div>
                </div>
                <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-2.5">
                  <h4 className="text-[10px] font-semibold text-slate-400 uppercase">Modelo IA</h4>
                  <span className="block mt-1 text-indigo-300 font-mono text-[11px] truncate">
                    {selectedAgent.model}
                  </span>
                </div>
              </div>

              <div>
                <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">Ferramentas Autorizadas</h4>
                <div className="flex flex-wrap gap-1.5 mt-1.5">
                  {(selectedAgent.allowed_tools || []).map((t: string) => (
                    <span key={t} className="px-2 py-0.5 bg-slate-800/90 text-slate-300 rounded text-[11px] border border-slate-700/80">
                      {t}
                    </span>
                  ))}
                </div>
              </div>

              {(selectedAgent.assigned_tasks || []).length > 0 && (
                <div>
                  <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">Tarefas Recentes</h4>
                  <div className="mt-1.5 space-y-1.5">
                    {selectedAgent.assigned_tasks.slice(0, 3).map((tk: any) => (
                      <div key={tk.id} className="px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs flex justify-between items-center">
                        <span className="text-slate-200 truncate pr-2">{tk.title}</span>
                        <span className="text-[10px] font-mono text-indigo-300 shrink-0">{tk.status}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {selectedAgent.id === 'jeffrey' && onOpenChatWithJeffrey && (
                <button
                  onClick={() => {
                    setSelectedAgent(null);
                    onOpenChatWithJeffrey();
                  }}
                  className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold transition shadow-lg shadow-indigo-600/30 flex items-center justify-center gap-2"
                >
                  <Sparkles className="w-4 h-4" />
                  <span>Abrir Chat Executivo com Jeffrey</span>
                </button>
              )}

              <div className="pt-3 border-t border-slate-800">
                <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">Atribuir Nova Tarefa</h4>
                <div className="mt-2 space-y-2">
                  <input
                    type="text"
                    value={taskInput}
                    onChange={(e) => setTaskInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleAssignDirectTask()}
                    placeholder={`O que ${selectedAgent.name} deve fazer?`}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                  />
                  <button
                    onClick={handleAssignDirectTask}
                    className="w-full py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white rounded-lg text-xs font-semibold transition border border-slate-700 flex items-center justify-center gap-2"
                  >
                    <Play className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Delegar para {selectedAgent.name}</span>
                  </button>
                  {actionFeedback && (
                    <p className="text-xs text-emerald-400 font-medium text-center">{actionFeedback}</p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
