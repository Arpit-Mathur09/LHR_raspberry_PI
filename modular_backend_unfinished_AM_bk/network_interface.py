# network_interface.py
import os
import time
import requests
import subprocess
import threading

SERVER_URL = "http://localhost:5000"

class HttpNetworkInterface:
    def __init__(self, client_engine):
        self.engine = client_engine
        self.server_connected = False
        self.sync_fail_count = 0

    def start(self):
        threading.Thread(target=self._sync_loop, daemon=True).start()

    def _sync_loop(self):
        while True:
            self.sync_with_server()
            time.sleep(0.5)

    def sync_with_server(self):
        payload = self.engine.get_telemetry_snapshot()
        try:
            r = requests.post(f"{SERVER_URL}/pi/sync", json=payload, timeout=2.0)
            if r.status_code == 200:
                if not self.server_connected: self.engine.log("✅ Connected to Server")
                self.server_connected = True
                self.sync_fail_count = 0
                for cmd in r.json().get("commands", []): self.handle_server_command(cmd)
        except: 
            self.sync_fail_count += 1
            if self.sync_fail_count > 3 and self.server_connected:
                self.engine.log("⚠️ Lost connection to Server")
                self.server_connected = False

    def handle_server_command(self, cmd):
        ev = cmd.get("event")
        data = cmd.get("data")

        if ev == "PAUSE": self.engine.command_queue.put(("REMOTE_PAUSE", None))
        elif ev == "RESUME": self.engine.command_queue.put(("REMOTE_RESUME", None))
        elif ev == "CLEAR": self.engine.command_queue.put(("REMOTE_STOP", None))
        elif ev == "SET_THERMAL": self.engine.command_queue.put(("SET_THERMAL", data))
        elif ev in ["DOWNLOAD_AND_RUN", "NEW_FILE"]:
            if isinstance(data, list): filename, source = data
            elif isinstance(data, str): filename, source = data, "Remote"
            else: filename, source = cmd.get("filename"), "Remote"
            if filename:
                threading.Thread(target=self._download_worker, args=(filename, source), daemon=True).start()
        elif ev == "SERIAL_SEND" and data:
            self.engine.command_queue.put(("MANUAL", data))
        elif ev == "CALIB_START":
            self.engine.set_calibration_mode(True, "Remote")
            self.engine.send_initial_calibration_gcode()
        elif ev == "CALIB_END":
            self.engine.set_calibration_mode(False, None)

    def _download_worker(self, filename, source):
        self.engine.log(f"📥 Downloading: {filename}...")
        try:
            r = requests.get(f"{SERVER_URL}/download/{filename}", timeout=3)
            if r.status_code == 200:
                local_path = os.path.join(self.engine.DIR_RECENT, filename)
                with open(local_path, "wb") as f: f.write(r.content)
                self.engine.log("✅ Downloaded")
                self.engine.command_queue.put(("DOWNLOAD_AND_RUN", [filename, source]))
            else: self.engine.log(f"❌ Server Error: {r.status_code}")
        except Exception as e: self.engine.log(f"❌ Download Failed: {e}")

    def get_connected_ssid(self):
        try:
            output = subprocess.check_output(["iwgetid", "-r"], encoding="utf-8").strip()
            if output: return output
        except: pass
        try:
            result = subprocess.check_output(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show", "--active"], encoding="utf-8")
            for line in result.split("\n"):
                if "802-11-wireless" in line or "wifi" in line: return line.split(":")[0]
        except: pass
        return None

    def get_wifi_networks(self):
        current_ssid = self.get_connected_ssid()
        try:
            subprocess.run(["nmcli", "dev", "wifi", "rescan"], stderr=subprocess.DEVNULL)
            time.sleep(1.0) 
            result = subprocess.check_output(["nmcli", "-t", "-f", "SSID,SIGNAL", "dev", "wifi"], encoding="utf-8")
            unique_nets = {}
            for line in result.split("\n"):
                if not line: continue
                parts = line.split(":")
                if len(parts) < 2: continue
                ssid = ":".join(parts[:-1]).strip()
                if not ssid: continue
                try: signal = int(parts[-1])
                except: signal = 0
                is_connected = bool(current_ssid and ssid == current_ssid)
                if ssid not in unique_nets:
                    unique_nets[ssid] = {"ssid": ssid, "signal": signal, "connected": is_connected}
                else:
                    if is_connected: unique_nets[ssid]["connected"] = True
                    if signal > unique_nets[ssid]["signal"]: unique_nets[ssid]["signal"] = signal
            networks = list(unique_nets.values())
            networks.sort(key=lambda x: (not x["connected"], -x["signal"]))
            return networks[:15]
        except: return []

    def connect_wifi(self, ssid, password):
        def run_nmcli(args): return subprocess.run(["sudo", "nmcli"] + args, capture_output=True, text=True)
        try:
            run_nmcli(["connection", "delete", ssid])
            res_add = run_nmcli(["connection", "add", "type", "wifi", "ifname", "wlan0", "con-name", ssid, "ssid", ssid])
            if res_add.returncode != 0: return False
            res_sec = run_nmcli(["connection", "modify", ssid, "wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", password])
            if res_sec.returncode != 0: return False
            res_up = run_nmcli(["connection", "up", ssid])
            if res_up.returncode != 0:
                run_nmcli(["connection", "delete", ssid])
                return False
            time.sleep(2)
            try:
                subprocess.run(["sudo", "systemctl", "restart", "mediamtx"], check=True)
                subprocess.run(["sudo", "systemctl", "restart", "cloudflared"], check=True)
            except: pass
            return True
        except: return False