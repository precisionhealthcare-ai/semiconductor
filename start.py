#!/usr/bin/env python3
"""
Quick-start script for Precision Ops Guide.
Run this file to start the server.
"""
import subprocess, sys, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Install dependencies if needed
try:
    import flask, flask_cors, jwt, werkzeug
except ImportError:
    print("Installing dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install",
                           "flask", "flask-cors", "pyjwt", "werkzeug"])

from server.app import app, init_db

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    print(f"\n  ╔══════════════════════════════════════╗")
    print(f"  ║  Precision HCC — Ops Guide           ║")
    print(f"  ║  http://localhost:{port}               ║")
    print(f"  ║                                      ║")
    print(f"  ║  Invite code: precision2024          ║")
    print(f"  ║  (set INVITE_CODE env var to change) ║")
    print(f"  ╚══════════════════════════════════════╝\n")
    app.run(host='0.0.0.0', port=port, debug=False)
