import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { FileText, Download, Code, Film, Music, Eye, X } from 'lucide-react';

export const ArtifactsView: React.FC = () => {
  const [artifacts, setArtifacts] = useState<any[]>([]);
  const [selectedArtifact, setSelectedArtifact] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getArtifacts()
      .then(setArtifacts)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handlePreview = async (id: string) => {
    try {
      const art = await api.getArtifact(id);
      setSelectedArtifact(art);
    } catch (e) {
      console.error(e);
    }
  };

  const getIcon = (type: string) => {
    switch (type) {
      case 'code': return <Code className="w-5 h-5 text-cyan-400" />;
      case 'video': return <Film className="w-5 h-5 text-pink-400" />;
      case 'audio': return <Music className="w-5 h-5 text-purple-400" />;
      default: return <FileText className="w-5 h-5 text-indigo-400" />;
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white">Entregáveis & Artefatos</h2>
        <p className="text-sm text-slate-400">Arquivos, relatórios, códigos e mídias geradas pelos especialistas da empresa.</p>
      </div>

      {loading ? (
        <div className="text-center py-12 text-slate-400 text-sm">Carregando entregáveis...</div>
      ) : artifacts.length === 0 ? (
        <div className="p-12 text-center bg-slate-900/60 rounded-2xl border border-slate-800">
          <FileText className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-slate-300">Nenhum artefato produzido ainda</h3>
          <p className="text-sm text-slate-500 mt-1">Inicie um workflow para os agentes gerarem entregáveis.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {artifacts.map((art) => (
            <div
              key={art.id}
              className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 hover:border-slate-700 transition shadow-md flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center space-x-3">
                  <div className="p-2.5 rounded-xl bg-slate-800 border border-slate-700">
                    {getIcon(art.artifact_type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-bold text-white truncate">{art.name}</h3>
                    <span className="text-[10px] font-mono uppercase text-indigo-400">{art.artifact_type}</span>
                  </div>
                </div>
                <p className="text-xs text-slate-400 mt-3 font-mono truncate">{art.file_path}</p>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between">
                <span className="text-xs text-slate-500">Criado por: <b className="text-slate-300 capitalize">{art.creator_agent}</b></span>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => handlePreview(art.id)}
                    className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition"
                    title="Visualizar"
                  >
                    <Eye className="w-4 h-4" />
                  </button>
                  <a
                    href={`/api/v1/artifacts/${art.id}/download`}
                    download
                    className="p-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition"
                    title="Baixar"
                  >
                    <Download className="w-4 h-4" />
                  </a>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Preview Modal */}
      {selectedArtifact && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl flex flex-col max-h-[85vh]">
            <div className="flex justify-between items-center pb-3 border-b border-slate-800">
              <div>
                <h3 className="text-base font-bold text-white">{selectedArtifact.name}</h3>
                <span className="text-xs font-mono text-indigo-400">{selectedArtifact.file_path}</span>
              </div>
              <button onClick={() => setSelectedArtifact(null)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="mt-4 flex-1 overflow-y-auto">
              <pre className="p-4 bg-slate-950 rounded-xl text-xs font-mono text-slate-200 whitespace-pre-wrap">
                {selectedArtifact.preview || 'Nenhum preview de texto disponível para este formato de arquivo.'}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

