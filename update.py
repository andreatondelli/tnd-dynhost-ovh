#!/usr/bin/env python3
import os
import time
import json
import signal
import requests

from datetime import datetime

next_ip_service_idx = 0

get_ip_services = [
    "https://api.ipify.org",
    "https://ipv4.icanhazip.com",
    "https://v4.ident.me",
    "https://checkip.amazonaws.com",
    "https://ipinfo.io/ip"
]

OVH_HOST = os.getenv("OVH_HOST")
OVH_USER = os.getenv("OVH_USER")
OVH_PASS = os.getenv("OVH_PASS")
MAX_RETRIES = int(os.getenv("MAX_RETRIES_PER_UPDATE", "1"))
CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "60"))
MIN_SECONDS_BETWEEN_UPDATES = int(os.getenv("MIN_SECONDS_BETWEEN_UPDATES", "120"))
FORCE_UPDATE_HOURS = int(os.getenv("FORCE_UPDATE_HOURS", "24"))
FORCE_UPDATE_SECONDS = FORCE_UPDATE_HOURS * 3600

STATE_FILE = f"/data/{OVH_HOST}.json"
RETRY_INTERVAL = 10  # seconds between retries

running = True

def log(msg):
    print(f"{datetime.utcnow().isoformat()}Z | {msg}", flush=True)

def handle_stop(signum, frame):
    global running
    log("Received stop signal, exiting gracefully.")
    running = False

signal.signal(signal.SIGTERM, handle_stop)
signal.signal(signal.SIGINT, handle_stop)

def log_configuration():
    log("Configuration:")
    log(f"  OVH_HOST: {OVH_HOST}")
    log(f"  OVH_USER: {OVH_USER}")
    log(f"  OVH_PASS: {'*' * len(OVH_PASS) if OVH_PASS else ''}")
    log(f"  CHECK_INTERVAL_SECONDS: {CHECK_INTERVAL_SECONDS}")
    log(f"  MIN_SECONDS_BETWEEN_UPDATES: {MIN_SECONDS_BETWEEN_UPDATES}")
    log(f"  MAX_RETRIES_PER_UPDATE: {MAX_RETRIES}")
    log(f"  FORCE_UPDATE_HOURS: {FORCE_UPDATE_HOURS}")

def init_state():
    if not os.path.exists(STATE_FILE):
        data = {"hostname": "", "ip": "", "timestamp": ""}
        with open(STATE_FILE, "w") as f:
            json.dump(data, f)

def load_state():
    with open(STATE_FILE) as f:
        return json.load(f)

def save_state(ip):
    data = {
        "hostname": OVH_HOST,
        "ip": ip,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    with open(STATE_FILE, "w") as f:
        json.dump(data, f)

def get_public_ip():
    global next_ip_service_idx
    n = len(get_ip_services)
    for i in range(n):
        service_idx = (next_ip_service_idx + i) % n
        url = get_ip_services[service_idx]
        try:
            ip = requests.get(url, timeout=5).text.strip()
            log(f"Retrieved public IP {ip} from {url}")
            if ip:
                next_ip_service_idx = (service_idx + 1) % n
                return ip
        except:
            continue
    return None


def update_ovh(ip):
    url = f"https://dns.eu.ovhapis.com/nic/update?system=dyndns&hostname={OVH_HOST}&myip={ip}"
    #url = f"https://www.ovh.com/nic/update?system=dyndns&hostname={OVH_HOST}&myip={ip}"
    resp = requests.get(url, auth=(OVH_USER, OVH_PASS), timeout=10)
    log(f"OVH update response: {resp.status_code} - {resp.text.strip()}")
    return resp.text.strip()

def should_force_update(last_timestamp):
    if not last_timestamp:
        return True
    try:
        last_dt = datetime.fromisoformat(last_timestamp.replace("Z", ""))
        elapsed = (datetime.utcnow() - last_dt).total_seconds()
        return elapsed >= FORCE_UPDATE_SECONDS
    except Exception as e:
        log(f"Error parsing timestamp: {e}")
        return True

log_configuration()

log(f"Starting OVH DynHost updater for: {OVH_HOST}")

init_state()

while running:
    public_ip = get_public_ip()
    if not public_ip:
        log("ERROR: Unable to retrieve public IP")
        time.sleep(CHECK_INTERVAL_SECONDS)
        continue
    else:
        log(f"Current public IP: {public_ip}")

    state = load_state()
    last_ip = state.get("ip")
    last_timestamp = state.get("timestamp")
    force_update = should_force_update(last_timestamp)

    if public_ip == last_ip and not force_update:
        last_dt = datetime.fromisoformat(last_timestamp.replace("Z", ""))
        elapsed = (datetime.utcnow() - last_dt).total_seconds()
        elapsed_hh_mm_ss = str(int(elapsed // 3600)).zfill(2) + ":" + str(int((elapsed % 3600) // 60)).zfill(2) + ":" + str(int(elapsed % 60)).zfill(2)
        log(f"IP unchanged ({public_ip}) and last update was {elapsed_hh_mm_ss} ago at {last_timestamp}.")
        time.sleep(CHECK_INTERVAL_SECONDS)
        continue

    if force_update and public_ip == last_ip:
        log(f"Force update triggered after {FORCE_UPDATE_HOURS}h even if IP unchanged.")

    log(f"IP changed: {last_ip} -> {public_ip}. Updating OVH…")

    retries = 0
    while retries < MAX_RETRIES and running:
        log(f"Attempt {retries + 1} of {MAX_RETRIES} to update OVH…")
        resp = update_ovh(public_ip)
        if resp.startswith("good") or resp.startswith("nochg"):
            log(f"Update OK: {resp}")
            save_state(public_ip)
            break
        else:
            log(f"Update failed: {resp}")
            retries += 1
            if retries >= MAX_RETRIES:
                log(f"Max retries ({MAX_RETRIES}) reached, giving up for this cycle.")
                break
            log(f"Retrying in {RETRY_INTERVAL}s…")
            time.sleep(RETRY_INTERVAL)

    time.sleep(CHECK_INTERVAL_SECONDS)

log("Exited.")
