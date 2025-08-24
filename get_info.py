import paramiko
import threading
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict    
class PersistentSSHManager:
    def __init__(
        self,
        servers,
        username,
        key_path,                      # e.g. "/home/deploy/.ssh/id_ed25519_cluster"
        passphrase=None,               # only if your key is encrypted
        port=22,
        known_hosts=None,              # e.g. "/home/deploy/.ssh/known_hosts"
        keepalive=30,                  # seconds; 0 disables keepalives
        conn_timeout=5,                # TCP/connect timeout
        auth_timeout=10,               # auth timeout
        banner_timeout=10              # banner timeout
    ):
        self.servers = servers
        self.username = username
        self.key_path = key_path
        self.passphrase = passphrase
        self.port = port
        self.known_hosts = known_hosts
        self.keepalive = keepalive
        self.conn_timeout = conn_timeout
        self.auth_timeout = auth_timeout
        self.banner_timeout = banner_timeout

        self.connections = {}                 # server -> SSHClient
        self._locks = defaultdict(threading.Lock)

        # Preload private key once
        self._pkey = self._load_private_key(key_path, passphrase)

    @staticmethod
    def _load_private_key(path, passphrase):
        # Try Ed25519 first (your generated key), then fall back to RSA if needed
        try:
            return paramiko.Ed25519Key.from_private_key_file(path, password=passphrase)
        except paramiko.PasswordRequiredException:
            raise
        except Exception:
            return paramiko.RSAKey.from_private_key_file(path, password=passphrase)

    def _new_client(self, host):
        c = paramiko.SSHClient()
        # Prefer strict host-key checking if you’ve pre-populated known_hosts
        if self.known_hosts and os.path.exists(self.known_hosts):
            c.load_host_keys(self.known_hosts)
            c.set_missing_host_key_policy(paramiko.RejectPolicy())
        else:
            # Falls back to system known_hosts and auto-adds unknown keys
            c.load_system_host_keys()
            c.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        c.connect(
            hostname=host,
            port=self.port,
            username=self.username,
            pkey=self._pkey,
            look_for_keys=False,        # don’t search other keys
            allow_agent=False,          # don’t use ssh-agent
            timeout=self.conn_timeout,
            auth_timeout=self.auth_timeout,
            banner_timeout=self.banner_timeout,
            compress=True
        )
        tr = c.get_transport()
        if tr and self.keepalive:
            tr.set_keepalive(self.keepalive)
        return c

    def get_connection(self, host):
        lock = self._locks[host]
        with lock:
            client = self.connections.get(host)
            if client:
                tr = client.get_transport()
                if tr and tr.is_active():
                    return client
                try:
                    client.close()
                except Exception:
                    pass

            # (Re)connect
            client = self._new_client(host)
            self.connections[host] = client
            return client

    def exec_command(self, host, cmd, timeout=None):
        """Run a command and return (rc, stdout, stderr) as strings."""
        client = self.get_connection(host)
        if client is None:
            return {'server': host, 'error': 'Connection failed'}
        try:
            stdin, stdout, stderr = client.exec_command(cmd)
            output = stdout.read().decode()
            error = stderr.read().decode()
        
            if error:
                return {'server': host, 'error': 'Errpr during exec'}
            return {'server': host, 'output': output}
        except Exception as e:
            return {'server': host, 'error': f'Exception during exec {str(e)}'}
    def close(self):
        for c in list(self.connections.values()):
            try:
                c.close()
            except Exception:
                pass
        self.connections.clear()
METRICS_SH = r"""
set -euo pipefail

# --- CPU (mpstat if available; otherwise /proc/stat 1s delta) ---
cpu_val=""
if command -v mpstat >/dev/null 2>&1; then
  # user% = 100 - idle%
  cpu_val=$(mpstat 1 1 | awk '/Average:.*all/ {printf "%.2f", 100 - $NF}')
else
  read -r _ a b c d e f g _ < /proc/stat
  idle1="$d"; total1=$((a+b+c+d+e+f+g))
  sleep 1
  read -r _ a b c d e f g _ < /proc/stat
  idle2="$d"; total2=$((a+b+c+d+e+f+g))
  idle=$((idle2-idle1)); total=$((total2-total1))
  cpu_val=$(awk -v idle="$idle" -v total="$total" 'BEGIN{ if(total>0){printf "%.2f", (100*(total-idle)/total)} else{print "0.00"}}')
fi
echo "cpu_usage=${cpu_val}"

# --- Memory (from /proc/meminfo) ---
# usage% = (MemTotal - MemAvailable) / MemTotal * 100
mem_val=$(awk '
  /MemTotal:/ {t=$2}
  /MemAvailable:/ {a=$2}
  END{ if(t>0){ printf "%.2f", (t-a)/t*100 } else {print "0.00"} }
' /proc/meminfo)
echo "memory=${mem_val}"
# --- Disk (root fs percent via df) ---
disk_val=$(df -P / | awk 'NR==2 {gsub("%","",$5); printf "%.2f", $5}')
echo "disk=${disk_val}"

# --- GPU (average utilization across GPUs if nvidia-smi present) ---
if command -v nvidia-smi >/dev/null 2>&1; then
  gpu_util=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits 2>/dev/null | \
             awk '{s+=$1; n++} END{ if(n>0){printf "%.2f", s/n} }')
  if [ -n "${gpu_util:-}" ]; then
    echo "gpu_usage=${gpu_util}"
  fi
fi
"""



_keyval_re = re.compile(r"^\s*([A-Za-z_]+)\s*=\s*([-+]?\d+(?:\.\d+)?)\s*$")

def parse_keyvals(s: str) -> dict:
    out = {}
    for line in s.splitlines():
      m = _keyval_re.match(line)
      if m:
          k, v = m.group(1), float(m.group(2))
          out[k] = v
    return out

def collect_one(ssh_mgr, server: str) -> dict:
    res = ssh_mgr.exec_command(server, METRICS_SH)
    kv = parse_keyvals(res["output"])
    kv['server'] = server
    return kv
   
    

def collect_all(ssh_mgr, max_workers: int = 16, timeout: float = 30.0) -> list[dict]:
    results = []
    with ThreadPoolExecutor(max_workers=min(max_workers, len(ssh_mgr.servers) or 1)) as ex:
        futs = {ex.submit(collect_one, ssh_mgr, srv): srv for srv in ssh_mgr.servers}
        try:
            for fut in as_completed(futs, timeout=timeout):
                try:
                    results.append(fut.result())
                except Exception as e:
                    results.append({"server": futs[fut], "error": str(e)})
        except TimeoutError:
            pass
    # Include servers that never returned (if any)
    seen = {r["server"] for r in results if "server" in r}
    for srv in ssh_mgr.servers:
        if srv not in seen:
            results.append({"server": srv, "error": "timeout"})
    print(results)
    return results
