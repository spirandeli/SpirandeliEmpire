from typing import Any
from src.services.knowledge_service import search_knowledge


async def search_knowledge_tool(query: str, limit: int = 3) -> dict[str, Any]:
    """Realiza busca semântica na base de conhecimento oficial do SpirandeliEmpire OS (RAG).

    Consulte esta ferramenta sempre que precisar de regras de negócio específicas,
    guias dos modelos (TikTok Shop, Dropshipping, SaaS), schemas do banco ou SOPs de infraestrutura.

    Args:
        query: Pergunta ou termos de busca (ex: 'regras de comissão do TikTok Shop').
        limit: Quantidade de trechos mais relevantes a retornar (default 3).

    Returns:
        Trechos documentais encontrados ordenados por relevância.
    """
    results = await search_knowledge(query, limit=limit)
    if not results:
        return {
            "found": False,
            "message": "Nenhum documento relevante encontrado para a consulta na base vetorial.",
            "results": [],
        }

    return {
        "found": True,
        "count": len(results),
        "results": results,
    }

