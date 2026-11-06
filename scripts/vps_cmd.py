#!/usr/bin/env python3
import sys
import paramiko

HOST = "187.41.117.220"
USER = "root"
PASSWORD = r"f'9RPh1yaHNfJCn'"

def run_remote(command):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(HOST, username=USER, password=PASSWORD, timeout=15)
        stdin, stdout, stderr = client.exec_command(command, get_pty=True)
        out = stdout.read().decode('utf-8', errors='replace')
        err = stderr.read().decode('utf-8', errors='replace')
        exit_status = stdout.channel.recv_exit_status()
        client.close()
        return exit_status, out, err
    except Exception as e:
        return 1, "", str(e)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        cmd = "uname -a && cat /etc/os-release && free -m && df -h / && docker --version 2>&1 && docker compose version 2>&1"
    else:
        cmd = " ".join(sys.argv[1:])
    status, out, err = run_remote(cmd)
    print(out)
    if err and status != 0:
        print("ERR:", err, file=sys.stderr)
    sys.exit(status)

