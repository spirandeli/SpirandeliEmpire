# Comparativo de Geradores de Vídeo IA — Risco de Detecção

| Gerador | C2PA Embutido | SynthID | Requer Limpeza | Custo/vídeo (5s) |
|---|---|---|---|---|
| **Wan2.1 14B local** | ❌ Não | ❌ Não | Apenas grain | ~R$ 0,25 (GPU alugada) |
| **Wan2.1 1.3B local** | ❌ Não | ❌ Não | Apenas grain | ~R$ 0,05 (GPU alugada) |
| **CogVideoX local** | ❌ Não | ❌ Não | Apenas grain | ~R$ 0,10 (GPU alugada) |
| **Runway Gen-4 Turbo** | ✅ Sim | ✅ Sim | Strip completo | ~$0,25 |
| **Runway Gen-4.5** | ✅ Sim | ✅ Sim | Strip completo | ~$0,60 |
| **Kling v2.5 Turbo** | ✅ Sim | ⚠️ Parcial | Strip completo | ~$0,31 |
| **Kling v3 Standard** | ✅ Sim | ⚠️ Parcial | Strip completo | ~$0,50 |
| **HeyGen** | ✅ Sim | ❌ Não | Strip simples | ~$0,30/min |

## Recomendação Operacional
- **Volume diário (9 vídeos/dia):** Wan2.1 local + RunPod on-demand
- **Produtos premium (1–2/semana):** Kling v2.5 Turbo com pipeline completo de limpeza
- **Canal com apresentador:** HeyGen (strip simples de metadados suficiente)
