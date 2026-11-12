# Orquestração com LangGraph — SpirandeliEmpire OS 3.1

O LangGraph é o núcleo operacional de inteligência e transição de estados do SpirandeliEmpire OS 3.1.

## 1. Estado Unificado (`EmpireState`)

O estado é tipado com TypedDict e preserva apenas metadados e referências compactas:

```python
class EmpireState(TypedDict):
    workflow_id: str
    project_id: Optional[str]
    workflow_type: str
    user_request: str
    objective: str
    plan: List[Dict[str, Any]]
    tasks: List[Dict[str, Any]]
    active_agents: List[str]
    completed_tasks: List[Dict[str, Any]]
    failed_tasks: List[Dict[str, Any]]
    artifacts: List[Dict[str, Any]]
    approvals: List[Dict[str, Any]]
    messages: List[Dict[str, Any]]
    execution_context: Dict[str, Any]
    quality_results: List[Dict[str, Any]]
    errors: List[str]
    final_result: Optional[Dict[str, Any]]
    current_node: str
    iteration_count: int
    waiting_for_approval: bool
```

## 2. Checkpoints e Durabilidade

Cada etapa executada salva um snapshot estruturado persistido em disco e no banco de dados. Isso possibilita:
1. Interrupção segura para aprovação humana (Human-in-the-loop).
2. Retomada exata da execução sem reprocessar nós já concluídos.
3. Rastreamento e auditoria forense de todas as decisões do Jeffrey.

