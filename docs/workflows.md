# Workflows Operacionais — SpirandeliEmpire OS 3.1

O sistema implementa 5 grafos especializados compilados e prontos para execução real:

## 1. Jeffrey Supervisor Graph
- **Interpret Request**: Interpreta a solicitação do proprietário com a Gemini API.
- **Classify Objective**: Classifica se a demanda pertence a desenvolvimento, conteúdo, clipagem ou negócios.
- **Plan Execution**: Decompõe tarefas atribuindo especialistas adequados.
- **Validate Plan & Approval Router**: Interrompe com interrupt caso a ação envolva riscos elevados ou deploys.
- **Execute Plan**: Dispara chamadas de ferramentas reais e produção de artefatos.
- **Quality Gate Murphy**: Avalia a integridade técnica dos artefatos produzidos.
- **Replan if Needed**: Replaneja automaticamente se a nota for inferior a 80%.
- **Consolidate Result**: Produz sumário executivo final entregue ao proprietário.

## 2. Development Graph
Requirements (Noé) ➔ Architecture (Noé) ➔ Task Breakdown ➔ Implementation (Balsini & Fonseca) ➔ Data Engineering (Ford) ➔ Testing (Murphy) ➔ Review ➔ Deployment Approval (Interrupt) ➔ Deployment (Jarvis) ➔ Final Report.

## 3. Content Production Graph (Vídeos & Shorts)
Research (News) ➔ Strategy ➔ Script (Script Agent) ➔ Review ➔ Visual Gen (Designer) ➔ Voice Gen (Voice Agent) ➔ Subtitles (Subtitle Agent) ➔ Video Assembly (Video Agent) ➔ QA (Murphy) ➔ Final Delivery.

## 4. Clip Production Graph
Video Input ➔ Transcript / Analysis ➔ Clipador ➔ Candidate Clips ➔ User Approval (Interrupt) ➔ Clip Extraction ➔ Subtitles ➔ Rendering ➔ QA ➔ Delivery.

## 5. Business Creation Graph (Novos Negócios Digitais)
Business Idea ➔ Market Research ➔ Business Model Canvas ➔ Feasibility ➔ Architecture ➔ MVP Spec ➔ Testing ➔ Deployment Approval ➔ Launch ➔ Monitoring ➔ Optimization.

