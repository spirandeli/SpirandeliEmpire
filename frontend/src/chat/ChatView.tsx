import React, { useState, useEffect, useRef } from 'react';
import { api, liveEvents } from '../services/api';
import { Send, Sparkles, Bot, User, CheckCircle2, ArrowRight } from 'lucide-react';

interface ChatViewProps {
  onNavigateToWorkflow?: (workflowId: string) => void;
}

export const ChatView: React.FC<ChatViewProps> = ({ onNavigateToWorkflow }) => {
  const [messages, setMessages] = useState<any[]>([]);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [jeffreyStatus, setJeffreyStatus] = useState<string>('Disponível');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const loadHistory = async () => {
    try {
      const history = await api.getChatHistory();
      if (history.length === 0) {
        setMessages([
          {
            id: 'welcome',
            sender_type: 'agent',
            sender_name: 'Jeffrey (CEO)',
            message: 'Olá, proprietário! Sou Jeffrey, CEO e Principal AI Engineer do SpirandeliEmpire OS. Estou pronto para liderar nossos 13 especialistas. O que vamos construir hoje? Você pode me pedir novos negócios digitais, desenvolvimento de software, produção de vídeos, pesquisas ou cortes.'
          }
        ]);
      } else {
        setMessages(history);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadHistory();
    const unsub = liveEvents.subscribe((event) => {
      if (event.event_type === 'AgentThinking' && event.agent_id === 'jeffrey') {
        setJeffreyStatus('Analisando estratégia...');
      } else if (event.event_type === 'WorkflowStarted') {
        setJeffreyStatus('Orquestrando especialistas...');
      } else if (event.event_type === 'WorkflowCompleted') {
        setJeffreyStatus('Missão concluída');
        loadHistory();
      }
    });
    return () => unsub();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSend = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputText.trim() || loading) return;

    const userText = inputText;
    setInputText('');
    setLoading(true);
    setJeffreyStatus('Formulando plano executivo...');

    // Optimistically add user message
    setMessages((prev) => [
      ...prev,
      {
        id: `temp_${Date.now()}`,
        sender_type: 'user',
        sender_name: 'Proprietário',
        message: userText
      }
    ]);

    try {
      const res = await api.sendChatMessage(userText);
      setMessages((prev) => [
        ...prev,
        {
          id: `jeffrey_${Date.now()}`,
          sender_type: 'agent',
          sender_name: 'Jeffrey (CEO)',
          message: res.reply,
          workflow: res.workflow
        }
      ]);
      setJeffreyStatus('Disponível');
    } catch (e: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: `err_${Date.now()}`,
          sender_type: 'system',
          sender_name: 'Sistema',
          message: `Erro ao comunicar com Jeffrey: ${e.message}`
        }
      ]);
      setJeffreyStatus('Disponível');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[700px] bg-slate-900/90 rounded-2xl border border-slate-800 shadow-xl overflow-hidden">
      {/* Chat Header */}
      <div className="px-6 py-4 bg-slate-950/80 border-b border-slate-800 flex justify-between items-center">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-600/30 border border-indigo-500/50 flex items-center justify-center text-indigo-400">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-white text-base flex items-center gap-2">
              Jeffrey
              <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                CEO & Principal AI Engineer
              </span>
            </h3>
            <div className="flex items-center space-x-1.5 text-xs text-slate-400 mt-0.5">
              <span className={`w-2 h-2 rounded-full ${loading ? 'bg-amber-400 animate-pulse' : 'bg-emerald-400'}`} />
              <span>{jeffreyStatus}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.map((m) => {
          const isUser = m.sender_type === 'user';
          return (
            <div key={m.id} className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                  isUser ? 'bg-indigo-600 text-white' : 'bg-slate-800 border border-indigo-500/40 text-indigo-400'
                }`}
              >
                {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>

              <div className={`max-w-[80%] ${isUser ? 'items-end' : 'items-start'}`}>
                <div className="text-[11px] text-slate-400 font-medium mb-1 px-1">
                  {m.sender_name}
                </div>
                <div
                  className={`p-4 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap shadow-md ${
                    isUser
                      ? 'bg-indigo-600 text-white rounded-tr-none'
                      : 'bg-slate-800/90 border border-slate-700/70 text-slate-100 rounded-tl-none'
                  }`}
                >
                  {m.message}

                  {/* If this message triggered a workflow, show clickable banner */}
                  {m.workflow && (
                    <div className="mt-3 pt-3 border-t border-slate-700/60 flex items-center justify-between">
                      <span className="text-xs text-indigo-300 font-semibold flex items-center gap-1.5">
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        Workflow Orquestrado com Sucesso
                      </span>
                      {onNavigateToWorkflow && (
                        <button
                          onClick={() => onNavigateToWorkflow(m.workflow.workflow_id)}
                          className="text-xs text-white hover:text-indigo-300 flex items-center gap-1 font-medium transition"
                        >
                          Ver Grafo <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}

        {loading && (
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-full bg-slate-800 border border-indigo-500/40 flex items-center justify-center text-indigo-400">
              <Bot className="w-4 h-4" />
            </div>
            <div className="p-4 rounded-2xl bg-slate-800/90 border border-slate-700/70 text-slate-300 rounded-tl-none flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-indigo-400 animate-ping" />
              <span className="text-xs font-medium text-indigo-300">Jeffrey está coordenando os departamentos...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Field */}
      <form onSubmit={handleSend} className="p-4 bg-slate-950/80 border-t border-slate-800 flex items-center gap-2">
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Apresente uma ideia, solicite um novo negócio, sistema ou vídeo ao CEO Jeffrey..."
          className="flex-1 px-4 py-3 bg-slate-900 border border-slate-700/80 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition shadow-inner"
        />
        <button
          type="submit"
          disabled={loading || !inputText.trim()}
          className="px-5 py-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-xl text-sm font-semibold transition shadow-lg shadow-indigo-600/30 flex items-center space-x-2"
        >
          <span>Enviar</span>
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
};

