# monitor_resources.py
import psutil
import time
import csv
import os
from datetime import datetime

RESULTS_DIR = "results"
os.makedirs(RESULTS_DIR, exist_ok=True)

ARCHITECTURE_NAME = "php_mysql"  # samakan dengan load_full_flow.py untuk sinkron analisis

# substring nama proses yang ingin dilacak
TARGET_PROCESSES = ["auth_service", "test_service", "postgres"]  # sesuaikan nama binary/command

SAMPLE_INTERVAL_SEC = 1.0     # sampling tiap 1 detik
DURATION_SEC = 600            # total 10 menit (bisa disesuaikan)


def find_target_pids():
    pids = {}
    for proc in psutil.process_iter(attrs=["pid", "name", "cmdline"]):
        name = proc.info["name"] or ""
        cmd = " ".join(proc.info["cmdline"] or [])
        for tag in TARGET_PROCESSES:
            if tag in name or tag in cmd:
                pids.setdefault(tag, []).append(proc.info["pid"])
    return pids


def main():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(RESULTS_DIR, f"resource_{ARCHITECTURE_NAME}_{ts}.csv")

    with open(filename, "w", newline="") as f:
        fieldnames = [
            "timestamp",
            "architecture",
            "cpu_percent_system",
            "mem_percent_system",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        start = time.time()
        print(f"[+] Monitoring resources for {ARCHITECTURE_NAME} ...")
        while time.time() - start < DURATION_SEC:
            row = {
                "timestamp": datetime.now().isoformat(),
                "architecture": ARCHITECTURE_NAME,
                "cpu_percent_system": psutil.cpu_percent(interval=None),
                "mem_percent_system": psutil.virtual_memory().percent,
            }

            pids_by_tag = find_target_pids()
            # tambahkan kolom dinamis untuk tiap PID
            for tag, pid_list in pids_by_tag.items():
                for pid in pid_list:
                    cpu_key = f"{tag}_{pid}_cpu"
                    mem_key = f"{tag}_{pid}_mem"
                    if cpu_key not in writer.fieldnames:
                        writer.fieldnames.append(cpu_key)
                    if mem_key not in writer.fieldnames:
                        writer.fieldnames.append(mem_key)
                    try:
                        p = psutil.Process(pid)
                        row[cpu_key] = p.cpu_percent(interval=0.0)
                        row[mem_key] = p.memory_info().rss  # bytes
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        row[cpu_key] = ""
                        row[mem_key] = ""

            writer.writerow(row)
            f.flush()
            time.sleep(SAMPLE_INTERVAL_SEC)

    print(f"[+] Resource CSV written: {filename}")


if __name__ == "__main__":
    main()
