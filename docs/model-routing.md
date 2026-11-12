# Roteamento Dinâmico de Modelos no LangGraph (SpirandeliEmpire OS 3.2)

O `ModelResolver` e o `ModelRouter` ([model_resolver.py](file:///home/spira/spirandeliempire/backend/app/providers/model_resolver.py)) resolvem qual provedor, credencial e modelo cada nó LangGraph / agente utilizará em tempo de execução.

## Hierarquia de Precedência
1. **Override explícito** da execução ou tarefa
2. **Configuração do projeto / workflow** (`project.metadata_json.model_config`)
3. **Configuração específica do agente** (`agent_model_configs`)
4. **Perfil de tipo de tarefa** (`task_model_configs`)
5. **Modelo padrão global do usuário** (`user_ai_preferences`)

## Regras de Segurança e Confiabilidade
- API Keys **nunca** são armazenadas no `EmpireState` do LangGraph; o backend resolve a credencial pelo `credential_id` validando `user_id == owner`.
- Se o modelo configurado estiver indisponível/retired ou sem capacidade exigida e o fallback estiver desabilitado, uma falha explícita é retornada sem troca silenciosa de provedor.

