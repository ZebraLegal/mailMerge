import sys, subprocess, time
from pathlib import Path

app = Path(__file__).with_name("mailMerge.py")
p = subprocess.Popen([sys.executable, "-m", "streamlit", "run", str(app)], cwd=app.parent)

print("Streamlit gestart. Druk Ctrl+C om alleen de launcher te beëindigen; de app blijft draaien.")
try:
    while p.poll() is None:
        time.sleep(0.5)
except KeyboardInterrupt:
    print("\n[run_mailmerge] Launcher gestopt; Streamlit draait mogelijk nog (pid:", p.pid, ")")