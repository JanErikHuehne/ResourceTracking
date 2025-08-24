from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from get_info import collect_all, PersistentSSHManager
from dataclasses import dataclass

import paramiko
import time
app = Flask(__name__)
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

@app.post("/select_server")
def select_server():
    server_id = request.form.get("server")
    # Validate & use the selection (e.g., set session state, load details, etc.)
    if server_id not in {s.id for s in get_servers()}:
        flash("Unknown server", "error")
        return redirect(url_for("servers"))
    # Do something with server_id, then navigate:
    return redirect(url_for("overview", server_id=server_id))


