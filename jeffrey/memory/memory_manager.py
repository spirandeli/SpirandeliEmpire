"""
SpirandeliEmpire OS - Jeffrey Operational Persistent Memory Manager
Stores and retrieves business context, approved decisions and guidelines
WITHOUT storing credentials, tokens or sensitive passwords.
"""
from typing import List, Dict, Any, Optional

SENSITIVE_KEYS = ["password", "token", "secret", "api_key", "private_key", "credential"]

class MemoryManager:
    def sanitize_content(self, text: str) -> str:
        """Ensures no tokens or secrets are leaked into persistent operational memory."""
        sanitized = text
        for word in SENSITIVE_KEYS:
            sanitized = sanitized.replace(word, f"[REDACTED_{word.upper()}]")
        return sanitized

    def format_context_prompt(self, memories: List[Dict[str, Any]]) -> str:
        """Formats active memories into an injection-safe context block for agents."""
        if not memories:
            return "Nenhuma memória contextual específica carregada."

        lines = ["--- MEMÓRIA OPERACIONAL ATIVA ---"]
        for m in memories:
            category = m.get("category", "info").upper()
            content = self.sanitize_content(m.get("content", ""))
            lines.append(f"[{category}] {content}")
        lines.append("--------------------------------")
        return "\n".join(lines)

