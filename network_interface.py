# network_interface.py
import os
import time
import requests
import subprocess
import threading

try:
    import socketio
except ImportError:  # pragma: no cover - runtime dependency check
    socketio = None

try:
    import websocket  # type: ignore
except ImportError:  # pragma: no cover - optional dependency check
    websocket = None

SERVER_URL = os.getenv("SERVER_URL", "https://remotemachinehandling.onrender.com")
MACHINE_ID = os.getenv("MACHINE_ID", "M1")
SOCKET_NAMESPACE = "/hardware"


class HttpNetworkInterface:
    def __init__(self, client_engine):
        self.engine = client_engine
        self.server_connected = False
        self.sync_fail_count = 0
        self.machine_id = MACHINE_ID
        self.sio = None
        self._stop_event = threading.Event()
        self._socket_thread = None
        self._last_payload = None
        self._last_emit_time = 0.0
        self._log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "WSap.log")
        os.makedirs(os.path.dirname(self._log_path), exist_ok=True)
        self._socket_transports = ["websocket", "polling"] if websocket is not None else ["polling"]

        if socketio is None:
            self._log("❌ python-socketio is not installed. Install it and restart the client.")
        elif websocket is None:
            self._log("⚠️ websocket-client is not installed; using polling transport only.")

    def _log(self, message):
        try:
            self.engine.log(message)
        except Exception:
            print(message, flush=True)
        try:
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
        except Exception:
            pass

    def start(self):
        if socketio is None:
            return
        self._stop_event.clear()
        self._socket_thread = threading.Thread(target=self._socket_loop, daemon=True)
        self._socket_thread.start()

    def stop(self):
        self._stop_event.set()
        if self.sio:
            try:
                self.sio.disconnect()
            except Exception:
                pass

    def _socket_loop(self):
        while not self._stop_event.is_set():
            self._connect_socket()
            if self._stop_event.is_set():
                break
            try:
                while not self._stop_event.is_set() and self.sio and self.sio.connected:
                    self.sync_with_server()
                    time.sleep(0.3)
            except Exception as exc:
                self._log(f"⚠️ Socket loop error: {exc}")
            self._mark_disconnected()
            time.sleep(2.0)

    def _connect_socket(self):
        if self.sio is not None:
            try:
                self.sio.disconnect()
            except Exception:
                pass

        self.sio = socketio.Client(
            reconnection=True,
            reconnection_delay=2,
            reconnection_delay_max=10,
            logger=False,
            engineio_logger=False,
        )
        self.sio.on("connect", self._on_socket_connect, namespace=SOCKET_NAMESPACE)
        self.sio.on("connect_error", self._on_socket_connect_error, namespace=SOCKET_NAMESPACE)
        self.sio.on("connect_timeout", self._on_socket_connect_error, namespace=SOCKET_NAMESPACE)
        self.sio.on("disconnect", self._on_socket_disconnect, namespace=SOCKET_NAMESPACE)
        self.sio.on("error", self._on_socket_error, namespace=SOCKET_NAMESPACE)
        self.sio.on("hw_event", self._handle_socket_event, namespace=SOCKET_NAMESPACE)

        socket_url = self._build_socket_url()
        self._log(f"🔌 Connecting to Socket.IO: {socket_url} namespace={SOCKET_NAMESPACE}")
        try:
            self.sio.connect(
                socket_url,
                namespaces=[SOCKET_NAMESPACE],
                transports=self._socket_transports,
            )
            if self.sio.connected:
                self._log("✅ Connected to Server")
        except Exception as exc:
            self._log(f"❌ Socket.IO connect failed: {exc}")
            self._mark_disconnected()

    def _build_socket_url(self):
        base = SERVER_URL.rstrip("/")
        return f"{base}?machine_id={self.machine_id}"

    def _on_socket_connect_error(self, data=None):
        self._log(f"❌ Socket.IO connect error: {data}")

    def _on_socket_error(self, data=None):
        self._log(f"⚠️ Socket.IO error: {data}")

    def _on_socket_connect(self):
        self.sync_fail_count = 0
        self.engine.sync_fail_count = self.sync_fail_count
        self.server_connected = True
        self.engine.server_connected = True
        self._emit_state_update(force=True)

    def _on_socket_disconnect(self):
        self._mark_disconnected()

    def _mark_disconnected(self):
        if self.server_connected:
            self._log("⚠️ Lost connection to Server")
        self.server_connected = False
        self.engine.server_connected = False

    def sync_with_server(self):
        if self.sio and self.sio.connected:
            self._emit_state_update()

    def _emit_state_update(self, force=False):
        if not self.sio or not self.sio.connected:
            return

        telemetry = self.engine.get_telemetry_snapshot()
        payload = dict(telemetry)
        payload["machine_id"] = self.machine_id
        payload.update(
            {
                "status": telemetry.get("status", self.engine.state.get("status", "Idle")),
                "filename": telemetry.get("file") or telemetry.get("filename") or "None",
                "started_by": telemetry.get("started_by", self.engine.state.get("started_by", "Unknown")),
                "progress": telemetry.get("progress", self.engine.state.get("progress", 0)),
                "current_line": telemetry.get("line") or self.engine.state.get("current_line", "Ready"),
                "current_desc": self.engine.state.get("current_desc", ""),
                "calib_active": self.engine.state.get("calibration_active", False),
                "calib_source": self.engine.state.get("calibration_source", None),
                "calib_status": self.engine.state.get("calib_status", "Idle"),
                "is_calibrated": self.engine.state.get("is_calibrated", False),
            }
        )

        now = time.time()
        should_send = force or (now - self._last_emit_time) >= 0.3 or self._last_payload != payload
        if not should_send:
            return

        self._last_payload = payload
        self._last_emit_time = now
        try:
            self.sio.emit("state_update", payload, namespace=SOCKET_NAMESPACE)
        except Exception as exc:
            self._log(f"⚠️ State emit failed: {exc}")

    def _handle_socket_event(self, cmd):
        if not isinstance(cmd, dict):
            return
        target_machine = cmd.get("machine_id")
        if target_machine and str(target_machine) != str(self.machine_id):
            return
        self.handle_server_command(cmd)

    def handle_server_command(self, cmd):
        ev = cmd.get("event")
        data = cmd.get("data")

        if ev == "PAUSE":
            self.engine.command_queue.put(("REMOTE_PAUSE", None))
        elif ev == "RESUME":
            self.engine.command_queue.put(("REMOTE_RESUME", None))
        elif ev == "CLEAR":
            self.engine.command_queue.put(("REMOTE_STOP", None))
        elif ev == "SET_THERMAL":
            self.engine.command_queue.put(("SET_THERMAL", data))
        elif ev in ["DOWNLOAD_AND_RUN", "NEW_FILE"]:
            if isinstance(data, list):
                filename, source = data
            elif isinstance(data, str):
                filename, source = data, "Remote"
            else:
                filename = cmd.get("filename") or cmd.get("file")
                source = cmd.get("source") or "Remote"
            if filename:
                download_url = cmd.get("download_url")
                threading.Thread(
                    target=self._download_worker,
                    args=(filename, source, download_url),
                    daemon=True,
                ).start()
        elif ev == "SERIAL_SEND" and data:
            self.engine.command_queue.put(("MANUAL", data))
        elif ev == "CALIB_START":
            self.engine.set_calibration_mode(True, "Remote")
            self.engine.send_initial_calibration_gcode()
        elif ev == "CALIB_END":
            self.engine.set_calibration_mode(False, None)

    def _download_worker(self, filename, source, download_url=None):
        self._log(f"📥 Downloading: {filename}...")
        try:
            if download_url:
                url = download_url
            else:
                url = f"{SERVER_URL.rstrip('/')}/uploads/{self.machine_id}/{filename}"
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                local_path = os.path.join(self.engine.DIR_RECENT, filename)
                with open(local_path, "wb") as f:
                    f.write(r.content)
                self._log("✅ Downloaded")
                self.engine.command_queue.put(("DOWNLOAD_AND_RUN", [filename, source]))
            else:
                self._log(f"❌ Server Error: {r.status_code}")
        except Exception as exc:
            self._log(f"❌ Download Failed: {exc}")

    def get_connected_ssid(self):
        try:
            output = subprocess.check_output(["iwgetid", "-r"], encoding="utf-8").strip()
            if output:
                return output
        except Exception:
            pass
        try:
            result = subprocess.check_output(
                ["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show", "--active"],
                encoding="utf-8",
            )
            for line in result.split("\n"):
                if "802-11-wireless" in line or "wifi" in line:
                    return line.split(":")[0]
        except Exception:
            pass
        return None

    def get_wifi_networks(self):
        current_ssid = self.get_connected_ssid()
        try:
            subprocess.run(["nmcli", "dev", "wifi", "rescan"], stderr=subprocess.DEVNULL)
            time.sleep(1.0)
            result = subprocess.check_output(["nmcli", "-t", "-f", "SSID,SIGNAL", "dev", "wifi"], encoding="utf-8")
            unique_nets = {}
            for line in result.split("\n"):
                if not line:
                    continue
                parts = line.split(":")
                if len(parts) < 2:
                    continue
                ssid = ":".join(parts[:-1]).strip()
                if not ssid:
                    continue
                try:
                    signal = int(parts[-1])
                except ValueError:
                    signal = 0
                is_connected = bool(current_ssid and ssid == current_ssid)
                if ssid not in unique_nets:
                    unique_nets[ssid] = {"ssid": ssid, "signal": signal, "connected": is_connected}
                else:
                    if is_connected:
                        unique_nets[ssid]["connected"] = True
                    if signal > unique_nets[ssid]["signal"]:
                        unique_nets[ssid]["signal"] = signal
            networks = list(unique_nets.values())
            networks.sort(key=lambda x: (not x["connected"], -x["signal"]))
            return networks[:15]
        except Exception:
            return []

    def connect_wifi(self, ssid, password):
        def run_nmcli(args):
            return subprocess.run(["sudo", "nmcli"] + args, capture_output=True, text=True)

        try:
            run_nmcli(["connection", "delete", ssid])
            res_add = run_nmcli(["connection", "add", "type", "wifi", "ifname", "wlan0", "con-name", ssid, "ssid", ssid])
            if res_add.returncode != 0:
                return False
            res_sec = run_nmcli(["connection", "modify", ssid, "wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", password])
            if res_sec.returncode != 0:
                return False
            res_up = run_nmcli(["connection", "up", ssid])
            if res_up.returncode != 0:
                run_nmcli(["connection", "delete", ssid])
                return False
            time.sleep(2)
            try:
                subprocess.run(["sudo", "systemctl", "restart", "mediamtx"], check=True)
                subprocess.run(["sudo", "systemctl", "restart", "cloudflared"], check=True)
            except Exception:
                pass
            return True
        except Exception:
            return False