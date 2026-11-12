# Arquitetura — SpirandeliEmpire OS 3.1

O **SpirandeliEmpire OS 3.1** é uma empresa digital autônoma operada por 14 agentes de inteligência artificial especializados, orquestrados através de **LangGraph** e potencializados pela API oficial do **Google Gemini**.

## 1. Visão Arquitetural

```text
Frontend (React + Vite + Phaser 3 + PWA)
        │
        ▼ (HTTP REST / WebSockets)
FastAPI API Gateway (v1)
        │
        ├─► Agent Registry (14 Agentes Oficiais)
        ├─► Project Hub & Business Wizard
        ├─► Task Manager Persistente
        ├─► Tool Registry & Sandbox Executores
        ├─► Integration Hub (Fernet AES-256 Secrets)
        ├─► Human-in-the-Loop Approvals
        ├─► Artifact Manager
        ├─► Real-Time Event Bus
        │
        ▼
   LangGraph Core
   (StateGraph • Nodes • Conditional Edges • Checkpoints)
        │
   ┌────┴───────────────────────────┐
   ▼                                ▼
Jeffrey Supervisor Graph     Specialist Subgraphs
(Interpret, Plan, Evaluate)  (Dev, Content, Clip, Business)
        │
        ▼
   Google Gemini API (google-genai SDK)
        │
        ▼
Celery Heavy Workers + PostgreSQL / SQLite + Redis
```

## 2. Princípio da Separação

O LangGraph é o motor de execução e transição de estados dos workflows multiagente duráveis. Ele **não** substitui a camada de aplicação:
- **FastAPI**: Gateway de entrada, autenticação e documentação OpenAPI.
- **SQLAlchemy 2**: Modelagem de dados relacional e persistência de longo prazo.
- **Artifact Manager**: Armazenamento de arquivos binários e entregáveis fora do estado do grafo.
- **Integration Hub**: Gestão de credenciais com criptografia Fernet em repouso.

