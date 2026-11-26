import os
import subprocess
import sys
import time
from pathlib import Path

SERVICES = ["seller","node","partner","drive","fleet","atlas","wild"]
if __name__ == "__main__":
    os.chdir(Path(__file__).resolve().parent)
    subprocess.run([sys.executable,"manage.py","migrate"],check=True)
    children=[]
    try:
        for port,name in enumerate(SERVICES,8100):
            children.append(subprocess.Popen([sys.executable,"manage.py","runserver",f"127.0.0.1:{port}","--noreload"],env={**os.environ,"WB_SERVICE":name}))
        while all(p.poll() is None for p in children):
            time.sleep(1)
        sys.exit("Service exited")
    except KeyboardInterrupt:
        pass
    finally:
        for p in children:
            p.terminate()
        for p in children:
            p.wait()