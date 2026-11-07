#!/usr/bin/env python3
import os
import sys
import tarfile
import paramiko
from scp import SCPClient

HOST = "187.41.117.220"
USER = "root"
PASSWORD = r"f'9RPh1yaHNfJCn'"
REMOTE_DIR = "/opt/abvos"
LOCAL_ROOT = "/home/spira/spirandeliempire"
TARBALL = "/tmp/abvos_release.tar.gz"

def create_tarball():
    print("==> Criando pacote de release de produção...")
    excludes = [
        '.git',
        'node_modules',
        'frontend/node_modules',
        '.system_generated',
        'tests',
        '.phpunit.cache',
        'storage/logs/*.log',
        'abvos_release.tar.gz'
    ]
    
    def filter_tar(tarinfo):
        for excl in excludes:
            if excl in tarinfo.name:
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

    # 1. Limpa projeto antigo se ainda existir
    print("\n==> Removendo resquícios do projeto anterior em /opt/spirandeliempire...")
    run_ssh(client, "rm -rf /opt/spirandeliempire")

    # 2. Cria diretório do ABVOS
    run_ssh(client, f"mkdir -p {REMOTE_DIR}")

    # 3. Transfere tarball via SCP
    print(f"\n==> Enviando release ({TARBALL}) para a VPS via SCP...")
    with SCPClient(client.get_transport(), socket_timeout=60.0) as scp:
        scp.put(TARBALL, f"{REMOTE_DIR}/release.tar.gz")
    print("==> Upload concluído.")

    # 4. Extrai na VPS
    print("\n==> Descompactando release na VPS...")
    run_ssh(client, f"cd {REMOTE_DIR} && tar -xzf release.tar.gz && rm -f release.tar.gz")

    # 5. Configura permissões e variáveis de ambiente
    print("\n==> Configurando variáveis de ambiente e permissões...")
    run_ssh(client, f"cd {REMOTE_DIR} && cp .env.production .env && cp .env.production backend/.env")
    run_ssh(client, f"cd {REMOTE_DIR} && chmod -R 777 backend/storage backend/bootstrap/cache")

    # 6. Build e Subida dos Containers de Produção
    print("\n==> Subindo containers de produção com Docker Compose...")
    run_ssh(client, f"cd {REMOTE_DIR} && docker compose -f docker-compose.prod.yml up -d --build")

    # 7. Aguarda inicialização dos serviços (MySQL e Redis)
    print("\n==> Aguardando containers de banco de dados e fila ficarem saudáveis (20s)...")
    import time
    time.sleep(20)

    # 8. Executa Migrações e Otimizações de Produção
    print("\n==> Executando migrações do banco de dados MySQL...")
    run_ssh(client, f"cd {REMOTE_DIR} && docker compose -f docker-compose.prod.yml exec -T app php artisan migrate --force")

    print("\n==> Criando link de storage público...")
    run_ssh(client, f"cd {REMOTE_DIR} && docker compose -f docker-compose.prod.yml exec -T app php artisan storage:link || true")

    print("\n==> Otimizando caches do Laravel (config, rotas, views, eventos)...")
    run_ssh(client, f"cd {REMOTE_DIR} && docker compose -f docker-compose.prod.yml exec -T app php artisan config:cache")
    run_ssh(client, f"cd {REMOTE_DIR} && docker compose -f docker-compose.prod.yml exec -T app php artisan route:cache")
    run_ssh(client, f"cd {REMOTE_DIR} && docker compose -f docker-compose.prod.yml exec -T app php artisan view:cache")

    # 9. Criação do Usuário Executivo Inicial / Administrador e Usuário de Demonstração
    print("\n==> Provisionando conta Root Admin executiva e conta Demo...")
    seed_cmd = (
        f"cd {REMOTE_DIR} && docker compose -f docker-compose.prod.yml exec -T app php artisan tinker --execute=\""
        "\\$admin = \\App\\Models\\User::firstOrCreate(["
        "    'email' => 'admin@spirandeli.com'"
        "], ["
        "    'name' => 'Alexander Spirandeli (Admin)',"
        "    'password' => \\Illuminate\\Support\\Facades\\Hash::make('Spirandeli2026!'),"
        "    'timezone' => 'America/Sao_Paulo',"
        "    'agent_enabled' => true,"
        "    'is_admin' => true,"
        "    'is_ai_active' => true,"
        "    'monthly_token_limit' => 10000000,"
        "]);"
        "\\$admin->update(['is_admin' => true, 'is_ai_active' => true]);"
        "echo 'ADMIN_USER_READY: ' . \\$admin->email . PHP_EOL;"
        "\\$demo = \\App\\Models\\User::firstOrCreate(["
        "    'email' => 'demo@spirandeliempire.tech'"
        "], ["
        "    'name' => 'Visitante Convidado',"
        "    'password' => \\Illuminate\\Support\\Facades\\Hash::make('Demo2026!'),"
        "    'timezone' => 'America/Sao_Paulo',"
        "    'agent_enabled' => true,"
        "    'is_admin' => false,"
        "    'is_ai_active' => true,"
        "    'monthly_token_limit' => 5000000,"
        "]);"
        "echo 'DEMO_USER_READY: ' . \\$demo->email;"
        "\""
    )
    run_ssh(client, seed_cmd)

    print("\n==> Executando Database Seeder para popular dados operacionais...")
    run_ssh(client, f"cd {REMOTE_DIR} && docker compose -f docker-compose.prod.yml exec -T app php artisan db:seed --force || true")

    print("\n==> Provisionando Starter Kits para todos os usuários (Admin e Não-Admins)...")
    run_ssh(client, f"cd {REMOTE_DIR} && docker compose -f docker-compose.prod.yml exec -T app php artisan abvos:provision-starter-kits")

    # 10. Reinicia o Nginx para reconectar com o novo IP do app
    print("\n==> Reiniciando proxy reverso Nginx para garantir conexão FastCGI...")
    run_ssh(client, f"cd {REMOTE_DIR} && docker compose -f docker-compose.prod.yml restart web")

    # 11. Verificação Final de Healthcheck
    print("\n==> Verificando status dos containers de produção...")
    run_ssh(client, f"cd {REMOTE_DIR} && docker compose -f docker-compose.prod.yml ps")

    print("\n==> Testando respostas HTTP da VPS...")
    run_ssh(client, "curl -skI https://spirandeliempire.tech/up || curl -sI http://127.0.0.1/up")
    run_ssh(client, "curl -skI https://spirandeliempire.tech/ || curl -sI http://127.0.0.1/")

    client.close()
    print("\n=======================================================")
    print("DEPLOY EM PRODUÇÃO CONCLUÍDO COM SUCESSO NA VPS!")
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

