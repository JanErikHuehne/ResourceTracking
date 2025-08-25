from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from get_info import collect_all, PersistentSSHManager
from dataclasses import dataclass
import paramiko
import time
import psycopg2
import os 
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo 
from psycopg2.extras import RealDictCursor


EU_BERLIN = ZoneInfo("Europe/Berlin")
DB_DSN = os.environ.get("DB_DSN", "postgresql://appuser:CompNeuro1234@localhost:5432/appdb")


app = Flask(__name__)
try:
    server_mapping = {'10.157.154.1' : 'Cortex (10.157.154.1)',
                    '10.157.154.2' : 'Cerebellum (10.157.154.2)',
                    '10.157.154.3' : 'Retina (10.157.154.3)',
                    '10.157.154.4' : 'Cochlea (10.157.154.4)',
                    '10.157.154.7' : 'Insula (10.157.154.7)',
                    '10.157.154.8' : 'Habenula (10.157.154.8)',
                    '10.157.154.9' : 'Amygdala (10.157.154.9)',
                    '10.157.154.11' : 'Thalamus (10.157.154.11)',
                    '10.157.154.12' : 'Hypthalamus (10.157.154.12)',
                    '10.157.154.13' : 'PFC (10.157.154.13)'
                    }
    ssh_mgr = PersistentSSHManager(
        servers=[
            "10.157.154.1","10.157.154.2","10.157.154.3","10.157.154.4",
            "10.157.154.7","10.157.154.8","10.157.154.9","10.157.154.11",
            "10.157.154.12","10.157.154.13"
        ],
        username="ge84yes",
        key_path="/home/deploy/.ssh/id_ed25519_cluster",
        known_hosts="/home/deploy/.ssh/known_hosts",  # optional; drop if you prefer AutoAddPolicy
        port=22,
        keepalive=30
    )
except FileNotFoundError:
    pass

def parse_iso_local(s: str | None, tz=EU_BERLIN):
    if not s:
        return None
    # Accept "YYYY-MM-DD" or "YYYY-MM-DDTHH:MM" or full ISO; assume Europe/Berlin if naive.
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt


def compute_window(args):
    preset = (args.get("range") or "").lower()
    now = datetime.now(EU_BERLIN)
    if preset == 'intraday':
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif preset == 'last_week':
        start, end = now - timedelta(days=7), now
    elif preset == 'last_month':
        start, end = now - timedelta(days=30), now
    elif preset == "last_year":
        start, end = now - timedelta(days=365), now
    else:
        start = parse_iso_local(args.get("start"))
        end   = parse_iso_local(args.get("end"))
        if end is None:
            end = now
    # convert to UTC for the DB (ts is TIMESTAMPTZ)
    start_utc = start.astimezone(timezone.utc) if start else None
    end_utc   = end.astimezone(timezone.utc)   if end else None
    return start_utc, end_utc
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/overview")
def overview():
    return render_template("overview.html")


@app.route("/history")
def history():
    return render_template("history.html")

@app.route("/docker")
def docker():
    return render_template("docker.html")

@app.route("/users")
def users():
    return render_template("user.html")


@app.get("/api/ssh/ping")
def ssh_ping():
    host = request.args.get("host")
    if not host:
        return jsonify(error="missing host"), 400
    output = ssh_mgr.exec_command(host, "hostname")
    return jsonify(host=host, output=output)


@app.route("/cpu2")
def cpu2():
    data = collect_all(ssh_mgr)  # each item must have "server"
    as_map = {
        server_mapping[d["server"]]: {k: v for k, v in d.items() if k != "server"}
        for d in data
    }
    print(as_map)
    return jsonify(as_map)



# Replace with your DB query; this is just a stub.
@dataclass
class Server:
    id: str
    name: str

def get_servers():
    return [
        Server(id="srv-a", name="Alpha"),
        Server(id="srv-b", name="Beta"),
        Server(id="srv-c", name="Gamma"),
    ]

@app.get("/servers")
def servers():
    return render_template("server.html", servers=get_servers())

@app.get("/api/history")
def db_history():
    try:
        if not DB_DSN:
            raise RuntimeError("DB_DSN is not set")
    
        
        start_utc, end_utc = compute_window(request.args)
        where = []
        params = []
        if start_utc is not None:
            where.append("ts >= %s"); params.append(start_utc)
        if end_utc is not None:
            where.append("ts < %s"); params.append(end_utc)
            
        sql = """
            SELECT server_id, ts, up, cpu_usage, memory, disk, gpu_usage
            FROM resource_history
            {where_clause}
            ORDER BY ts DESC
        """.format(where_clause=("WHERE " + " AND ".join(where)) if where else "") 
        
        with psycopg2.connect(DB_DSN) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            
        return jsonify(rows)
    except Exception as e:
        app.logger.exception("history failed")
        return jsonify({"error": str(e)}), 500
   
    

@app.post("/select_server")
def select_server():
    server_id = request.form.get("server")
    # Validate & use the selection (e.g., set session state, load details, etc.)
    if server_id not in {s.id for s in get_servers()}:
        flash("Unknown server", "error")
        return redirect(url_for("servers"))
    # Do something with server_id, then navigate:
    return redirect(url_for("overview", server_id=server_id))



