# SpirandeliEmpire OS v2.0
> **One Empire. Multiple Businesses. One Command Center.**

Plataforma central modular para planejar, implantar, automatizar, monitorar e administrar múltiplos negócios digitais independentes a partir de uma única dashboard unificada sob a orquestração do agente central **Jeffrey**.

---

## 🏛️ Visão Geral do Sistema

O **SpirandeliEmpire OS** nasceu para resolver o desafio de operar vários modelos de negócios digitais (canais YouTube Dark, publicação na Amazon KDP, produtos digitais em PDF e papelaria imprimível) com automação máxima, governança de custos e supervisão humana obrigatória.

```
SpirandeliEmpire OS
├── Core (Laravel 11 Backend + Vue 3 Frontend)
├── Jeffrey AI (Orquestrador & 11 Agentes Especializados)
├── Business Factory (Questionários, Viabilidade e Provisionamento)
├── AI Engine Local (Ollama + Piper Neural TTS + FFmpeg)
├── Automation Engine (Workflows & Agendamentos)
├── Empire Analytics (Controle Financeiro com Teto de R$ 200/mês)
└── Businesses (RISADA.exe, KDP Factory, Digital Products, Printables)
```

---

## 🚀 Como Subir para o Git e Instalar na VPS

### 1. No seu computador atual (Commit & Push)
```bash
git init
git add .
git commit -m "feat: initial commit of SpirandeliEmpire OS v2.0 master architecture"
git branch -M main
git remote add origin <URL_DO_SEU_REPOSITORIO_GIT>
git push -u origin main
```

---

### 2. Na sua VPS Linux Limpa (Ubuntu 24.04 LTS / Debian 12)
Conecte-se na VPS e rode apenas:

```bash
git clone <URL_DO_SEU_REPOSITORIO_GIT> spirandeli-empire-os
cd spirandeli-empire-os

# Copie e ajuste suas senhas e domínio
cp .env.example .env
nano .env

# Execute o instalador automatizado
chmod +x scripts/install.sh
./scripts/install.sh
```

O script `install.sh` fará todo o trabalho pesado:
- ✅ Instala Docker & Docker Compose plugin (se necessário)
- ✅ Valida permissões e pastas de armazenamento
- ✅ Sobe todos os containers (Caddy, Backend, Workers, PostgreSQL, Redis, Ollama, Uptime Kuma)
- ✅ Executa as migrations e os seeds do banco de dados
- ✅ Baixa o modelo leve local `qwen2.5:3b`
- ✅ Configura o SSL/HTTPS automático no Caddy
- ✅ Executa o healthcheck e entrega a URL pronta!

---

## 🛡️ Diretrizes Inegociáveis Implementadas

1. **Teto Financeiro:** Orçamento operacional padrão limitado a **R$ 200,00/mês**. Jeffrey bloqueia despesas não autorizadas.
2. **Modelos Locais First:** Inferência em texto via **Ollama** e narração via **Piper TTS** local em português brasileiro com **R$ 0,00 de custo de API**.
3. **Fidelidade Teológica e Histórica:** No canal de histórias bíblicas (**RISADA.exe**), é expressamente proibido alucinar ou inventar versículos.
4. **Isolamento de Negócios:** Cada negócio possui diretório próprio (`storage/businesses/<slug>`), limites de recursos e logs separados. A falha de um negócio nunca derruba a plataforma.
5. **Supervisão Humana:** Publicações, despesas financeiras e ações críticas exigem aprovação no painel.

---

## 🛠️ Stack Tecnológica

| Camada | Tecnologia | Propósito |
|---|---|---|
| **OS** | Ubuntu Server 24.04 LTS | Sistema operacional base |
| **Proxy Reverso** | Caddy 2 | HTTPS automático & headers de segurança |
| **Backend** | Laravel 11 / PHP 8.3 FPM | API REST, Autenticação & Regras de Negócio |
| **Frontend** | Vue 3 + Tailwind CSS | Dashboard central moderna e responsiva |
| **Banco de Dados** | PostgreSQL 16 | Persistência relacional robusta |
| **Filas & Cache** | Redis 7 + Laravel Queues | Desacoplamento assíncrono de tarefas |
| **IA Textual** | Ollama (`qwen2.5:3b`) | Planejamento, pesquisa e roteiros locais |
| **Síntese de Voz** | Piper Neural TTS | Narração local em pt-BR ultrarrápida na CPU |
| **Vídeo** | FFmpeg | Renderização automatizada de Shorts e vídeos |
| **Monitoramento** | Uptime Kuma | Monitoramento de uptime e saúde dos serviços |

---

## 📂 Negócios Iniciais Pré-Configurados

1. **RISADA.exe:** Canal de histórias bíblicas para YouTube (Shorts 9:16 e vídeos longos 16:9).
2. **KDP Factory:** Pipeline para publicação de eBooks, devocionais e estudos na Amazon KDP.
3. **Digital Products Factory:** Estudos bíblicos em PDF, cronologias e planners.
4. **Printable Factory:** Artes originais em alta resolução e quadros decorativos para impressão.

---

## 📜 Licença
Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.

