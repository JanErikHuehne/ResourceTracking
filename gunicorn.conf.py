import multiprocessing
bind = "unix:/run/yourapp.sock"   # nginx will proxy to this socket
workers = max(2, multiprocessing.cpu_count() * 2 + 1)
worker_class = "gthread"          # good general default
threads = 4
timeout = 60
graceful_timeout = 30
keepalive = 5
accesslog = "-"
errorlog = "-"
umask = 0o007
