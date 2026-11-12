Aqui é o **Fonseca, Frontend Engineer sênior do SpirandeliEmpire OS**.

Recebi a especificação arquitetural definida pelo **Noé**. Com base nos contratos e requisitos estipulados, implementei a arquitetura de interface client-side. O foco está em **desempenho mobile-first, segurança de tipos de ponta a ponta com TypeScript, acessibilidade (WCAG 2.1 AA) e integração resiliente com o backend FastAPI do Balsini**.

Abaixo apresento a especificação técnica e implementação dos artefatos do Frontend.

---

# 🚀 Arquitetura Frontend — SpirandeliEmpire OS

## 1. Tech Stack & Ferramentas
* **Core:** React 18 + TypeScript + Vite (Build tool de alta performance).
* **Styling:** Tailwind CSS (Mobile-first, utilitários otimizados).
* **State Management:** 
  * **Server State:** `@tanstack/react-query` v5 (Caching, revalidação e estado assíncrono).
  * **Client State:** `Zustand` (Estado global leve para UI/Sessão).
* **Game Engine Canvas:** Phaser 3 (Englobado via React Wrapper com React Lifecycle isolation).
* **HTTP Client:** Axios com Interceptors centralizados para JWT e tratamento uniforme de erros.
* **Ícones & Acessibilidade:** `lucide-react` + Radix UI Primitives (Acessibilidade nativa).

---

## 2. Estrutura de Diretórios (Feature-First)

```text
src/
├── app/                  # Providers globais, rotas e wrappers principais
├── assets/               # Sprites do Phaser, fontes e imagens estáticas
├── components/           # Design System Atomizado (Button, Modal, Toast)
│   ├── ui/               # Componentes visuais genéricos
│   └── phaser/           # Container de integração do Canvas Phaser 3
├── features/             # Módulos baseados em domínio de negócio
│   ├── empire/           # Módulo de Gestão do Império
│   │   ├── api/          # Custom hooks do React Query (queries & mutations)
│   │   ├── components/   # UI específica da feature
│   │   ├── hooks/        # Hooks de regras de negócio locais
│   │   └── types/        # Tipos restritos ao domínio
├── lib/                  # Configurações de terceiros (axios, query-client)
├── stores/               # Stores do Zustand (UI e Auth session)
├── types/                # DTOs compartilhados (Espelho do Backend)
└── utils/                # Formatadores, validadores e parsers
```

---

## 3. Implementação dos Artefatos Core

### 3.1. Definição de Tipos / Contrato de Dados (`src/types/empire.ts`)

```typescript
export interface ResourceState {
  gold: number;
  wood: number;
  food: number;
  population: number;
}

export interface EmpireData {
  id: string;
  name: string;
  level: number;
  resources: ResourceState;
  updatedAt: string;
}

export interface UpgradeBuildingPayload {
  buildingId: string;
  targetLevel: number;
}

export interface ApiErrorResponse {
  code: string;
  message: string;
  details?: Record<string, string[]>;
}
```

---

### 3.2. Cliente API & Interceptor FastAPI (`src/lib/api-client.ts`)

```typescript
import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { ApiErrorResponse } from '@/types/empire';

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor: Injeção de Token JWT
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('empire_auth_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response Interceptor: Normalização de Erros vindos do FastAPI
apiClient.interceptors.response.use(
  (response) => response.data,
  (error: AxiosError<ApiErrorResponse>) => {
    const formattedError: ApiErrorResponse = error.response?.data || {
      code: 'ERR_NETWORK',
      message: 'Falha de conexão com o servidor do SpirandeliEmpire.',
    };
    return Promise.reject(formattedError);
  }
);
```

---

### 3.3. React Query Hooks para Estado Server-side (`src/features/empire/api/useEmpire.ts`)

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { EmpireData, UpgradeBuildingPayload } from '@/types/empire';

const EMPIRE_QUERY_KEY = ['empire', 'state'];

export function useEmpireData() {
  return useQuery<EmpireData>({
    queryKey: EMPIRE_QUERY_KEY,
    queryFn: () => apiClient.get('/empire/state'),
    staleTime: 1000 * 30, // 30 segundos de cache fresco
    refetchInterval: 1000 * 10, // Polling resiliente a cada 10s
  });
}

export function useUpgradeBuilding() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: UpgradeBuildingPayload) =>
      apiClient.post('/empire/building/upgrade', payload),
    onSuccess: () => {
      // Invalidação imediata do cache após ação bem-sucedida
      queryClient.invalidateQueries({ queryKey: EMPIRE_QUERY_KEY });
    },
  });
}
```

---

### 3.4. Componente Canvas Phaser 3 Resiliente (`src/components/phaser/EmpireCanvas.tsx`)

Garante a inicialização e o destruimento seguro do ciclo de vida do Phaser no React sem memory leaks.

```typescript
import React, { useEffect, useRef } from 'react';
import Phaser from 'phaser';

interface EmpireCanvasProps {
  resources: { gold: number; wood: number };
}

export const EmpireCanvas: React.FC<EmpireCanvasProps> = ({ resources }) => {
  const gameRef = useRef<HTMLDivElement | null>(null);
  const phaserInstanceRef = useRef<Phaser.Game | null>(null);

  useEffect(() => {
    if (!gameRef.current) return;

    const config: Phaser.Types.Core.GameConfig = {
      type: Phaser.AUTO,
      parent: gameRef.current,
      width: '100%',
      height: '100%',
      transparent: true,
      physics: { default: 'arcade' },
      scene: {
        preload() {
          // Preload de sprites
        },
        create() {
          const scene = this;
          scene.add.text(16, 16, 'Spirandeli Empire Zone', {
            fontSize: '18px',
            color: '#FACD15',
          });
        },
      },
      scale: {
        mode: Phaser.Scale.RESIZE,
        autoCenter: Phaser.Scale.CENTER_BOTH,
      },
    };

    phaserInstanceRef.current = new Phaser.Game(config);

    return () => {
      if (phaserInstanceRef.current) {
        phaserInstanceRef.current.destroy(true);
        phaserInstanceRef.current = null;
      }
    };
  }, []);

  return (
    <div 
      className="w-full h-[300px] sm:h-[450px] rounded-xl overflow-hidden border border-slate-800 bg-slate-950/80 shadow-2xl relative"
      aria-label="Visualização interativa do Império"
      role="region"
    >
      <div ref={gameRef} className="w-full h-full" />
    </div>
  );
};
```

---

### 3.5. Componente Principal da UI Mobile-First (`src/features/empire/components/Dashboard.tsx`)

Design totalmente responsivo (Mobile-first), acessível, com Tailwind e integrando a comunicação assíncrona.

```typescript
import React from 'react';
import { useEmpireData, useUpgradeBuilding } from '../api/useEmpire';
import { EmpireCanvas } from '@/components/phaser/EmpireCanvas';
import { Coins, Trees, Wheat, ShieldAlert, Hammer, Loader2 } from 'lucide-react';

export const EmpireDashboard: React.FC = () => {
  const { data: empire, isLoading, isError, error } = useEmpireData();
  const upgradeMutation = useUpgradeBuilding();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center gap-3">
        <Loader2 className="w-8 h-8 animate-spin text-amber-500" />
        <p className="text-sm font-medium tracking-wide">Carregando dados do Império...</p>
      </div>
    );
  }

  if (isError || !empire) {
    return (
      <div className="min-h-screen bg-slate-950 p-4 flex items-center justify-center">
        <div className="bg-red-950/40 border border-red-800/60 rounded-xl p-6 max-w-md w-full text-center">
          <ShieldAlert className="w-12 h-12 text-red-500 mx-auto mb-3" />
          <h2 className="text-lg font-bold text-red-200">Falha ao carregar estado</h2>
          <p className="text-sm text-red-300/80 mt-1">
            {(error as any)?.message || 'Erro inesperado na comunicação com o servidor.'}
          </p>
        </div>
      </div>
    );
  }

  const handleUpgrade = (buildingId: string) => {
    upgradeMutation.mutate({ buildingId, targetLevel: empire.level + 1 });
  };

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 p-4 sm:p-6 md:p-8 max-w-7xl mx-auto space-y-6">
      {/* Header & Status do Império */}
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-amber-400">
            {empire.name}
          </h1>
          <p className="text-xs sm:text-sm text-slate-400">Nível do Império: <span className="font-semibold text-slate-200">{empire.level}</span></p>
        </div>

        {/* Resource Bar */}
        <div className="grid grid-cols-3 gap-2 sm:gap-4 bg-slate-900/90 p-3 rounded-lg border border-slate-800" aria-label="Recursos do Império">
          <div className="flex items-center gap-2">
            <Coins className="w-4 h-4 text-amber-400 shrink-0" />
            <div className="flex flex-col">
              <span className="text-[10px] text-slate-400 uppercase font-bold">Ouro</span>
              <span className="text-xs sm:text-sm font-bold">{empire.resources.gold.toLocaleString()}</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Trees className="w-4 h-4 text-emerald-400 shrink-0" />
            <div className="flex flex-col">
              <span className="text-[10px] text-slate-400 uppercase font-bold">Madeira</span>
              <span className="text-xs sm:text-sm font-bold">{empire.resources.wood.toLocaleString()}</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Wheat className="w-4 h-4 text-yellow-500 shrink-0" />
            <div className="flex flex-col">
              <span className="text-[10px] text-slate-400 uppercase font-bold">Comida</span>
              <span className="text-xs sm:text-sm font-bold">{empire.resources.food.toLocaleString()}</span>
            </div>
          </div>
        </div>
      </header>

      {/* Phaser Canvas Container */}
      <section aria-label="Mapa Visual do Império">
        <EmpireCanvas resources={empire.resources} />
      </section>

      {/* Actions & Upgrades Section */}
      <section className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 sm:p-6 space-y-4">
        <h2 className="text-lg font-semibold text-slate-200 flex items-center gap-2">
          <Hammer className="w-5 h-5 text-amber-400" /> Edificações & Expansão
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          <div className="bg-slate-900 border border-slate-800 p-4 rounded-lg flex flex-col justify-between gap-3">
            <div>
              <h3 className="font-bold text-slate-200">Centro da Cidade</h3>
              <p className="text-xs text-slate-400 mt-1">Aumenta a capacidade de produção global.</p>
            </div>
            <button
              onClick={() => handleUpgrade('town_center')}
              disabled={upgradeMutation.isPending}
              className="w-full py-2.5 px-4 bg-amber-500 hover:bg-amber-600 disabled:bg-slate-800 disabled:text-slate-500 text-slate-950 font-bold text-xs sm:text-sm rounded-lg transition-colors focus:ring-2 focus:ring-amber-400 focus:outline-none flex items-center justify-center gap-2"
              aria-label="Evoluir Centro da Cidade"
            >
              {upgradeMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                'Evoluir Edifício'
              )}
            </button>
          </div>
        </div>
      </section>
    </main>
  );
};
```

---

## 4. Garantia de Qualidade e Handover

### Para Murphy (QA):
1. **Pontos de Teste E2E/Componente:**
   * Validar renderização das 3 variantes de estado do React Query (`isLoading`, `isError`, `isSuccess`).
   * Testar responsividade da barra de recursos em breakpoints `320px`, `640px` e `1024px`.
   * Verificar se o canvas Phaser é montado e desmontado sem re-renders infinitos ou vazamento de memória DOM.
2. **Acessibilidade:**
   * Teclado navega completamente através de elementos interativos (`button`, `region`).
   * Suporte a leitores de tela estruturado via atributos `aria-*`.

### Para Jarvis (DevOps):
* **Build Command:** `npm run build` (Gera artefatos estáticos otimizados via Rollup na pasta `/dist`).
* **Vite Config:** Configurado com suporte a env vars dinâmicas (`VITE_API_BASE_URL`).

---

**Status:** Prontos para integração completa com os endpoints da API FastAPI desenvolvidos por Balsini e validação pela suíte de testes de Murphy.