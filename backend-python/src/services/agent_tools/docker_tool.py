import os
from typing import Any
import httpx

DOCKER_SOCKET = os.getenv("DOCKER_SOCKET", "/var/run/docker.sock")


async def list_docker_containers(all_containers: bool = False) -> dict[str, Any]:
    """Lista o status operacional, imagem e saúde dos contêineres Docker rodando no ABVOS.

    Args:
        all_containers: Se True, lista também contêineres parados. Default é False (apenas ativos).

    Returns:
        Um resumo da lista de contêineres gerenciados pelo Docker.
    """
    if not os.path.exists(DOCKER_SOCKET):
        return {
            "error": "Socket do Docker (/var/run/docker.sock) não está acessível no container.",
            "containers": [],
        }

    try:
        transport = httpx.AsyncHTTPTransport(uds=DOCKER_SOCKET)
        async with httpx.AsyncClient(transport=transport, timeout=6.0) as client:
            res = await client.get(f"http://docker/containers/json?all={'1' if all_containers else '0'}")
            if res.status_code != 200:
                return {"error": f"Erro Docker API: {res.status_code}", "containers": []}

            data = res.json()
            containers = []
            for c in data:
                names = [n.lstrip("/") for n in c.get("Names", [])]
                containers.append({
                    "id": c.get("Id", "")[:12],
                    "name": names[0] if names else "unknown",
                    "image": c.get("Image", ""),
                    "state": c.get("State", ""),
                    "status": c.get("Status", ""),
                    "created": c.get("Created", 0),
                })

            return {
                "total": len(containers),
                "containers": containers,
            }
    except Exception as e:
        return {
            "error": f"Falha ao consultar Docker Engine: {str(e)}",
            "containers": [],
        }


async def get_docker_container_logs(container_name: str, lines: int = 50) -> dict[str, Any]:
    """Recupera os últimos logs (stdout e stderr) de um contêiner Docker específico para diagnóstico de erros.

    Args:
        container_name: Nome do contêiner (ex: 'abvos-app-py', 'abvos-db', 'abvos-redis', 'abvos-web').
        lines: Quantidade de linhas finais a recuperar (default 50, máx 200).

    Returns:
        Trecho dos últimos logs do contêiner.
    """
    if not os.path.exists(DOCKER_SOCKET):
        return {"error": "Socket do Docker (/var/run/docker.sock) não acessível."}

    lines = max(5, min(lines, 200))
    clean_name = container_name.lstrip("/")

    try:
        transport = httpx.AsyncHTTPTransport(uds=DOCKER_SOCKET)
        async with httpx.AsyncClient(transport=transport, timeout=8.0) as client:
            # Query container logs
            url = f"http://docker/containers/{clean_name}/logs?stdout=1&stderr=1&tail={lines}&timestamps=1"
            res = await client.get(url)
            if res.status_code == 404:
                return {"error": f"Contêiner '{clean_name}' não encontrado no Docker."}
            if res.status_code != 200:
                return {"error": f"Falha ao obter logs ({res.status_code}): {res.text[:200]}"}

            raw_bytes = res.content
            # Remove Docker multiplexing headers (8 bytes per chunk: 1 byte stream type, 3 padding, 4 bytes size)
            lines_list = []
            i = 0
            while i < len(raw_bytes):
                if i + 8 <= len(raw_bytes) and raw_bytes[i] in (1, 2) and raw_bytes[i+1:i+4] == b'\x00\x00\x00':
                    size = int.from_bytes(raw_bytes[i+4:i+8], byteorder='big')
                    chunk = raw_bytes[i+8:i+8+size]
                    lines_list.append(chunk.decode("utf-8", errors="replace"))
                    i += 8 + size
                else:
                    rest = raw_bytes[i:].decode("utf-8", errors="replace")
                    lines_list.append(rest)
                    break

            log_text = "".join(lines_list).strip()
            return {
                "container": clean_name,
                "lines_requested": lines,
                "logs": log_text[-4000:] if len(log_text) > 4000 else log_text,
            }
    except Exception as e:
        return {"error": f"Falha ao ler logs de {clean_name}: {str(e)}"}

