#!/usr/bin/env python3
import os
import sys
import tarfile
import time
import paramiko
from scp import SCPClient

HOST = "187.41.117.220"
USER = "root"
PASSWORD = r"f'9RPh1yaHNfJCn'"
REMOTE_DIR = "/opt/abvos"
LOCAL_ROOT = "/home/spira/spirandeliempire"
TARBALL = "/tmp/abvos_release.tar.gz"


def create_tarball():
    print("==> Criando pacote de release de produção (Python FastAPI + Vue 3)...")
    excludes = [
        '.git',
        'node_modules',
        'frontend/node_modules',
        '.venv',
        '__pycache__',
        '.pytest_cache',
        '.system_generated',
        'abvos_release.tar.gz',
    ]

    def filter_tar(tarinfo):
        for excl in excludes:
            if excl in tarinfo.name.split("/"):
                return None
            if tarinfo.name.endswith(".pyc") or "/.venv/" in tarinfo.name:
                return None
        return tarinfo

    with tarfile.open(TARBALL, "w:gz") as tar:
        tar.add(LOCAL_ROOT, arcname=".", filter=filter_tar)

    size_mb = os.path.getsize(TARBALL) / (1024 * 1024)
    print(f"==> Pacote criado com sucesso: {TARBALL} ({size_mb:.2f} MB)")


def run_ssh(client, cmd, print_output=True):
    if print_output:
        print(f"\n[VPS] $ {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
    out = stdout.read().decode('utf-8', errors='replace')
    status = stdout.channel.recv_exit_status()
    if print_output and out.strip():
        print(out.strip())
    if status != 0:
        print(f"==> Comando falhou com código {status}")
    return status, out


def main():
    create_tarball()

    print(f"\n==> Conectando via SSH em {USER}@{HOST}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASSWORD, timeout=30)
    print("==> Conexão SSH estabelecida com sucesso.")

    # 1. Cria diretório do ABVOS
    run_ssh(client, f"mkdir -p {REMOTE_DIR}")

    # 2. Transfere tarball via SCP
    print(f"\n==> Enviando release ({TARBALL}) para a VPS via SCP...")
    with SCPClient(client.get_transport(), socket_timeout=60.0) as scp:
        scp.put(TARBALL, f"{REMOTE_DIR}/release.tar.gz")
    print("==> Upload concluído.")

    # 3. Extrai na VPS e limpa legados PHP / Laravel
    print("\n==> Descompactando release na VPS e removendo todos os arquivos legados...")
    run_ssh(client, f"cd {REMOTE_DIR} && tar -xzf release.tar.gz && rm -f release.tar.gz && rm -rf backend docker/php docker/supervisor")

    # 4. Configura variáveis de ambiente
    print("\n==> Configurando variáveis de ambiente...")
    run_ssh(client, f"cd {REMOTE_DIR} && cp -f .env.production .env")

    # 5. Remove volumes e imagens antigas do PHP / Laravel
    print("\n==> Limpando imagens e volumes legados do Docker...")
    run_ssh(client, "docker stop abvos-prod-app abvos-prod-worker 2>/dev/null || true")
    run_ssh(client, "docker rm abvos-prod-app abvos-prod-worker 2>/dev/null || true")
    run_ssh(client, "docker volume rm abvos-prod_composer_cache 2>/dev/null || true")
    run_ssh(client, "docker rmi abvos/app:prod abvos/worker:prod spirandeliempire-core-app:latest spirandeliempire-core-worker:latest 2>/dev/null || true")
    run_ssh(client, "docker image prune -f")

    # 6. Sobe stack moderna em Python (FastAPI + Nginx + MySQL + Redis)
    print("\n==> Subindo containers Python FastAPI em produção com Docker Compose...")
    run_ssh(client, f"cd {REMOTE_DIR} && docker compose -f docker-compose.prod.yml up -d --build --remove-orphans")

    # 8. Aguarda inicialização (MySQL + Redis + FastAPI)
    print("\n==> Aguardando containers ficarem saudáveis (15s)...")
    time.sleep(15)

    # 9. Provisiona contas de Administrador e Demonstração
    print("\n==> Provisionando dados iniciais no banco de dados...")
    run_ssh(client, f"cd {REMOTE_DIR} && docker compose -f docker-compose.prod.yml exec -T app-py python3 src/seed.py")

    # 10. Reinicia o Nginx para aplicar configuração reversa ao FastAPI
    print("\n==> Reiniciando Nginx com proxy reverso apontando para o FastAPI...")
    run_ssh(client, f"cd {REMOTE_DIR} && docker compose -f docker-compose.prod.yml restart web")

    # 11. Verificação Final de Healthcheck
    print("\n==> Verificando status dos containers de produção...")
    run_ssh(client, f"cd {REMOTE_DIR} && docker compose -f docker-compose.prod.yml ps")

    print("\n==> Testando respostas HTTP da VPS...")
    run_ssh(client, "curl -skI https://spirandeliempire.tech/up || curl -sI http://127.0.0.1/up")
    run_ssh(client, "curl -skI https://spirandeliempire.tech/ || curl -sI http://127.0.0.1/")

    client.close()
    print("\n=======================================================")
    print("DEPLOY PYTHON FASTAPI EM PRODUÇÃO CONCLUÍDO COM SUCESSO!")
    print("Domínio Seguro (SSL): https://spirandeliempire.tech")
    print("Credenciais de Acesso:")
    print("  1. Painel Master / Admin:")
    print("     E-mail: admin@spirandeli.com")
    print("     Senha:  Spirandeli2026!")
    print("  2. Acesso Não-Admin / Apresentação Demo:")
    print("     E-mail: demo@spirandeliempire.tech")
    print("     Senha:  Demo2026!")
    print("=======================================================")


if __name__ == "__main__":
    main()
