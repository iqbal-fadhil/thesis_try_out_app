import psutil
import time
from datetime import datetime

# CHANGE PER PLATFORM IF YOU WANT SEPARATE FILES
LOG_FILE = "cpu_mem_monolith_go.csv"   # for microservices: "cpu_mem_micro.csv"
INTERVAL = 1  # seconds

if __name__ == "__main__":
    with open(LOG_FILE, "w") as f:
        f.write("timestamp,cpu_percent,mem_used_mb\n")

    print(f"Monitoring CPU & memory... logging to {LOG_FILE}")

    try:
        while True:
            cpu = psutil.cpu_percent(interval=None)
            mem_mb = psutil.virtual_memory().used / 1024 / 1024
            ts = datetime.now().isoformat()
            line = f"{ts},{cpu:.2f},{mem_mb:.2f}\n"
            print(line.strip())
            with open(LOG_FILE, "a") as f:
                f.write(line)
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        print("Monitoring stopped.")
