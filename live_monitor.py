#!/usr/bin/env python3
import sys
import os
import time
import json
import math
import argparse
import subprocess
import threading
import re
from collections import Counter
from datetime import datetime

from web_dashboard import start_web_dashboard

# ANSI Color Codes
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_RED = "\033[91m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_BLUE = "\033[94m"
C_MAGENTA = "\033[95m"
C_CYAN = "\033[96m"
C_DIM = "\033[2m"

CH_COLORS = [C_CYAN, C_YELLOW, C_MAGENTA, C_GREEN, C_BLUE, C_RED]

DEFAULT_CHANNELS = [
    {"id": "1", "freq": 392662500, "label": "392.6625 MHz", "desc": "Canal 1"},
    {"id": "2", "freq": 392800000, "label": "392.8000 MHz", "desc": "Canal 2"},
    {"id": "3", "freq": 393525000, "label": "393.5250 MHz", "desc": "Canal 3 (Principal)"},
    {"id": "4", "freq": 393650000, "label": "393.6500 MHz", "desc": "Canal 4"},
    {"id": "5", "freq": 393800000, "label": "393.8000 MHz", "desc": "Canal 5"},
]

GAIN_PRESETS = [
    {"id": "1", "val": 0.0, "label": "0.0 dB", "desc": "Mínima / Directa"},
    {"id": "2", "val": 14.4, "label": "14.4 dB", "desc": "Baja"},
    {"id": "3", "val": 28.0, "label": "28.0 dB", "desc": "Media-Baja"},
    {"id": "4", "val": 35.0, "label": "35.0 dB", "desc": "Media"},
    {"id": "5", "val": 40.2, "label": "40.2 dB", "desc": "Media-Alta"},
    {"id": "6", "val": 49.6, "label": "49.6 dB", "desc": "Máxima"},
    {"id": "7", "val": None, "label": "AGC", "desc": "Automática por hardware"},
]

SECURITY_OPCODES = {
    "13": ("D_AUTHENTICATION", "Desafío de Autenticación de Terminal (KMC -> Terminal)", True),
    "14": ("U_AUTHENTICATION", "Respuesta Criptográfica de Terminal (Terminal -> KMC)", True),
    "16": ("D_AUTHORISATION", "Autorización de Seguridad / Claves de Acceso", True),
    "63": ("D_DATA_AUTHENTICATION", "Sesión de Seguridad y Actualización de Claves (OTAR)", True),
    "60": ("D_CONNECT_DCH", "Conexión a Canal de Datos Dedicado (DCH)", False),
    "65": ("D_DCH_OPEN", "Apertura de Canal de Datos Seguro", False),
    "20": ("U_REGISTRATION_REQ", "Petición de Registro de Terminal", False),
    "21": ("D_REGISTRATION_NAK", "Registro Denegado por Fallo de Autenticación/Clave", True),
    "22": ("D_REGISTRATION_ACK", "Registro Aceptado de Terminal", False),
    "23": ("D_FORCED_REGISTRATION", "Re-Autenticación Forzada de Terminal", True),
}

def load_talkgroup_aliases(json_path="talkgroups.json"):
    aliases = {}
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in data.items():
                    if not k.startswith("_"):
                        aliases[k] = str(v)
        except Exception:
            pass
    return aliases

def parse_gps_payload(hex_str):
    if not hex_str or len(hex_str) < 12:
        return None
    try:
        raw = bytes.fromhex(hex_str)
    except Exception:
        return None

    # 1. NMEA ASCII
    try:
        text = raw.decode("latin1", errors="ignore")
        nmea_match = re.search(r"\$(GP|GN)(RMC|GGA|GLL),([^,\*]+),([0-9\.]+),([NS]),([0-9\.]+),([EW])", text)
        if nmea_match:
            lat_str = nmea_match.group(4)
            lat_dir = nmea_match.group(5)
            lon_str = nmea_match.group(6)
            lon_dir = nmea_match.group(7)
            lat_deg = float(lat_str[:2]) + float(lat_str[2:]) / 60.0
            if lat_dir == "S": lat_deg = -lat_deg
            lon_deg = float(lon_str[:3]) + float(lon_str[3:]) / 60.0
            if lon_dir == "W": lon_deg = -lon_deg
            return lat_deg, lon_deg, "NMEA ASCII"
    except Exception:
        pass

    # 2. LIP Binario
    for offset in range(0, max(1, len(raw) - 6), 2):
        chunk = raw[offset:offset+6]
        if len(chunk) == 6:
            lat_raw = int.from_bytes(chunk[0:3], byteorder="big", signed=True)
            lon_raw = int.from_bytes(chunk[3:6], byteorder="big", signed=True)
            lat = lat_raw * (90.0 / (1 << 23))
            lon = lon_raw * (180.0 / (1 << 23))
            if (-89.0 <= lat <= 89.0) and (-179.0 <= lon <= 179.0) and not (abs(lat) < 0.001 and abs(lon) < 0.001):
                if abs(lat) > 5.0:
                    return lat, lon, "LIP Binario"

    return None

def extract_tetrapol_channels(hex_str):
    try:
        raw = bytes.fromhex(hex_str)
    except Exception:
        return []
    channels = []
    if len(raw) >= 3:
        for i in range(len(raw) - 1):
            val1 = ((raw[i] & 0x0F) << 8) | raw[i+1]
            val2 = (raw[i] << 4) | (raw[i+1] >> 4)
            for v in (val1, val2):
                if 800 <= v <= 1600:
                    f = 380000000 + v * 12500
                    channels.append((v, f))
    return list(set(channels))

def auto_scan_bch_frequencies(control_freq=393.525e6, gain=0.0, bias_tee=False, scan_seconds=6):
    print(f"\n{C_BOLD}{C_CYAN}============================================================{C_RESET}")
    print(f"{C_BOLD}{C_CYAN}   AUTO-DESCUBRIMIENTO DE CELDAS Y CANALES (BCH SCANNER)    {C_RESET}")
    print(f"{C_BOLD}{C_CYAN}============================================================{C_RESET}")
    print(f" Sintonizando Canal de Control ({control_freq/1e6:.4f} MHz) durante {scan_seconds}s...")

    fifo_path = "/tmp/tetrapol_scan.fifo"
    if os.path.exists(fifo_path):
        try: os.remove(fifo_path)
        except Exception: pass
    os.mkfifo(fifo_path)

    dump_bin = os.path.abspath("./build/apps/tetrapol_dump")
    proc_dump = subprocess.Popen(
        [dump_bin, "-b", "UHF", "-t", "CCH", "-d", "DOWN", "-i", fifo_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1
    )

    osmosdr_args = "rtl=0"
    if bias_tee: osmosdr_args += ",bias=1"

    demod_script = os.path.abspath("demod/demod.py")
    cmd_demod = [
        sys.executable, demod_script,
        "-a", osmosdr_args,
        "-f", str(control_freq),
        "-l", str(int(control_freq)),
        "-s", "2048000",
        "-o", fifo_path
    ]
    if gain is not None:
        cmd_demod.extend(["-g", str(gain)])

    proc_demod = subprocess.Popen(cmd_demod, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    discovered_freqs = set([int(control_freq)])
    cell_scrambler = None
    start_t = time.time()

    try:
        while time.time() - start_t < scan_seconds:
            line = proc_dump.stdout.readline()
            if not line:
                time.sleep(0.1)
                continue
            try:
                event = json.loads(line.strip())
            except Exception:
                continue

            if event.get("event") == "scr":
                cell_scrambler = event.get("scr")
            elif event.get("event") == "tsdu":
                tsdu = event.get("tsdu", {})
                data_val = (tsdu.get("data") or {}).get("value", "")
                if data_val:
                    for ch_id, f in extract_tetrapol_channels(data_val):
                        discovered_freqs.add(f)
    except Exception:
        pass
    finally:
        proc_demod.terminate()
        proc_dump.terminate()
        if os.path.exists(fifo_path):
            try: os.remove(fifo_path)
            except Exception: pass

    for ch in DEFAULT_CHANNELS:
        discovered_freqs.add(ch["freq"])

    res_list = sorted(list(discovered_freqs))
    print(f"\n {C_GREEN}✓ Escaneo completado.{C_RESET}")
    if cell_scrambler is not None:
        print(f" • Código de Color / Celda detectada: {C_BOLD}SCR = {cell_scrambler}{C_RESET}")
    print(f" • Canales activos encontrados en la red ({len(res_list)}):")
    for idx, f in enumerate(res_list):
        print(f"   {idx+1}) {f/1e6:.4f} MHz ({f} Hz)")
    print(f"{C_CYAN}============================================================{C_RESET}\n")
    return res_list

def classify_voice_burst(raw_bytes_list):
    if len(raw_bytes_list) < 15:
        return "GLITCH", 0.0, 0.0, 0.0, "Ráfaga corta (< 0.3s)"

    all_b = b"".join(raw_bytes_list)
    total = len(all_b)
    cnt = Counter(all_b)

    ent = -sum((c / total) * math.log2(c / total) for c in cnt.values())
    max_possible = math.log2(min(total, 256))
    norm_ent = ent / max_possible if max_possible > 0 else 1.0

    ones = sum(bin(byte).count("1") for byte in all_b)
    bit_ratio = ones / (total * 8)

    hamming_diffs = []
    for i in range(len(raw_bytes_list) - 1):
        f1 = raw_bytes_list[i]
        f2 = raw_bytes_list[i+1]
        diff = sum(bin(b1 ^ b2).count("1") for b1, b2 in zip(f1, f2))
        hamming_diffs.append(diff)
    avg_hamming = sum(hamming_diffs) / len(hamming_diffs) if hamming_diffs else 60.0

    if (norm_ent >= 0.83 and 0.46 <= bit_ratio <= 0.54 and avg_hamming >= 48.0):
        return "ENCRYPTED", ent, norm_ent, avg_hamming, f"Cifrado de flujo (Norm:{norm_ent:.2f}, Ham:{avg_hamming:.1f})"

    if avg_hamming < 18.0 or norm_ent < 0.65:
        return "NOISE", ent, norm_ent, avg_hamming, f"Ruido/Reposo (Ham:{avg_hamming:.1f})"

    if (0.65 <= norm_ent <= 0.82 and 18.0 <= avg_hamming <= 48.0 and len(raw_bytes_list) >= 20):
        return "CLEAR", ent, norm_ent, avg_hamming, f"Voz en claro (Norm:{norm_ent:.2f}, Ham:{avg_hamming:.1f})"

    return "ENCRYPTED", ent, norm_ent, avg_hamming, f"Cifrada/Indeterminada (Norm:{norm_ent:.2f})"

def play_audio(wav_path):
    for player in ["paplay", "aplay", "pw-play"]:
        try:
            res = subprocess.run([player, wav_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res.returncode == 0:
                return
        except Exception:
            pass
    try:
        w_path = subprocess.check_output(["wslpath", "-w", wav_path], text=True).strip()
        ps_cmd = f"(New-Object Media.SoundPlayer '{w_path}').PlaySync()"
        subprocess.run(["powershell.exe", "-Command", ps_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def show_interactive_menu():
    print(f"\n{C_BOLD}{C_CYAN}============================================================{C_RESET}")
    print(f"{C_BOLD}{C_CYAN}          TETRAPOL KIT - PANEL DE CONTROL EN VIVO           {C_RESET}")
    print(f"{C_BOLD}{C_CYAN}============================================================{C_RESET}")
    for ch in DEFAULT_CHANNELS:
        print(f"  {C_BOLD}[{ch['id']}]{C_RESET} {C_GREEN}{ch['label']}{C_RESET}  {C_DIM}({ch['desc']}){C_RESET}")
    print(f"\n  {C_BOLD}[T]{C_RESET} {C_YELLOW}TODOS los 5 canales a la vez{C_RESET} {C_DIM}(Trunking simultáneo - Span: 1.14 MHz){C_RESET}")
    print(f"  {C_BOLD}[AA]{C_RESET} {C_MAGENTA}TODOS + Auto-descubrimiento en caliente y sintonización dinámica{C_RESET} {C_DIM}(Recomendado){C_RESET}")
    print(f"  {C_BOLD}[A]{C_RESET} {C_MAGENTA}Auto-descubrimiento previo{C_RESET} {C_DIM}(Escanear celda CCH){C_RESET}")
    print(f"  {C_BOLD}[M]{C_RESET} {C_BLUE}Introducir frecuencia manual personalizada{C_RESET}")
    print(f"{C_CYAN}------------------------------------------------------------{C_RESET}")

    # 1. Selección de frecuencias
    try:
        choice = input(f"{C_BOLD}1. Canales a sintonizar (ej: 1,3,4 o T o AA) [Por defecto: AA]: {C_RESET}").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nSaliendo...")
        sys.exit(0)

    auto_dynamic = False
    is_auto_scan_once = (choice.upper() == "A")

    if not choice or choice.upper() == "AA":
        selected_freqs = [ch["freq"] for ch in DEFAULT_CHANNELS]
        auto_dynamic = True
    elif choice.upper() == "T" or choice.upper() == "TODOS":
        selected_freqs = [ch["freq"] for ch in DEFAULT_CHANNELS]
        auto_dynamic = False
    elif is_auto_scan_once:
        selected_freqs = None
    elif choice.upper() == "M":
        try:
            manual = input(f"{C_BOLD}Introduce frecuencia(s) separadas por coma (ej: 393.525e6): {C_RESET}").strip()
            selected_freqs = parse_freq_arg(manual)
        except (KeyboardInterrupt, EOFError):
            sys.exit(0)
    else:
        selected_freqs = []
        for token in choice.replace(" ", "").split(","):
            token = token.strip()
            found = False
            for ch in DEFAULT_CHANNELS:
                if token == ch["id"] or token == str(ch["freq"]) or token == ch["label"].replace(" MHz", ""):
                    selected_freqs.append(ch["freq"])
                    found = True
                    break
            if not found and token:
                try:
                    val = float(token)
                    if val < 1e6:
                        val *= 1e6
                    selected_freqs.append(int(val))
                except Exception:
                    pass

        if not selected_freqs:
            selected_freqs = [ch["freq"] for ch in DEFAULT_CHANNELS]

    # 2. Ganancia SDR
    print(f"\n{C_BOLD}2. Ajuste de Ganancia SDR:{C_RESET}")
    for g in GAIN_PRESETS:
        print(f"  {C_BOLD}[{g['id']}]{C_RESET} {C_YELLOW}{g['label']:<8}{C_RESET} {C_DIM}({g['desc']}){C_RESET}")
    print(f"  {C_BOLD}[M]{C_RESET} {C_BLUE}Valor manual en dB (ej: 38.6){C_RESET}")
    try:
        gain_choice = input(f"  {C_BOLD}Selecciona ganancia (1..7 o M) [Por defecto: 1 (0.0 dB)]: {C_RESET}").strip()
    except (KeyboardInterrupt, EOFError):
        gain_choice = "1"

    selected_gain = 0.0
    if not gain_choice or gain_choice == "1":
        selected_gain = 0.0
    elif gain_choice.upper() == "M":
        try:
            g_man = input(f"  {C_BOLD}Introduce ganancia en dB (ej: 35.0): {C_RESET}").strip()
            selected_gain = float(g_man)
        except Exception:
            selected_gain = 0.0
    else:
        for g in GAIN_PRESETS:
            if gain_choice == g["id"]:
                selected_gain = g["val"]
                break

    # 3. Bias-Tee
    print(f"\n{C_BOLD}3. Alimentación Bias-Tee (LNA/Antena activa):{C_RESET}")
    try:
        bias_in = input(f"  {C_BOLD}¿Activar Bias-Tee 4.5V? (s/N) [Por defecto: N - Desactivado]: {C_RESET}").strip().lower()
    except (KeyboardInterrupt, EOFError):
        bias_in = "n"
    bias_tee = (bias_in in ["s", "si", "y", "yes"])

    if is_auto_scan_once:
        selected_freqs = auto_scan_bch_frequencies(
            control_freq=393.525e6,
            gain=selected_gain,
            bias_tee=bias_tee,
            scan_seconds=6
        )

    selected_freqs = sorted(list(set(selected_freqs)))

    # 4. Guardar cifradas o no
    print(f"\n{C_BOLD}4. Gestión de llamadas cifradas:{C_RESET}")
    print(f"  {C_DIM}• Por defecto (N), las llamadas cifradas se descartan en memoria y no llenan el disco.{C_RESET}")
    try:
        save_enc_in = input(f"  {C_BOLD}¿Deseas guardar archivos WAV de transmisiones cifradas? (s/N) [Por defecto: N]: {C_RESET}").strip().lower()
    except (KeyboardInterrupt, EOFError):
        save_enc_in = "n"
    save_encrypted = (save_enc_in in ["s", "si", "y", "yes"])

    # 5. Nivel de visualización
    print(f"\n{C_BOLD}5. Nivel de visualización en consola:{C_RESET}")
    print(f"  {C_BOLD}[1]{C_RESET} {C_GREEN}Modo Limpio{C_RESET} {C_DIM}(Alertas de voz, GPS, OTAR, nuevas frecuencias y grabaciones){C_RESET}")
    print(f"  {C_BOLD}[2]{C_RESET} {C_YELLOW}Modo Informativo{C_RESET} {C_DIM}(Muestra grupos Z:Y:X, señalización, celdas, GPS y OTAR){C_RESET}")
    print(f"  {C_BOLD}[3]{C_RESET} {C_BLUE}Modo Depuración Total{C_RESET} {C_DIM}(Muestra todas las tramas y JSON en crudo){C_RESET}")
    try:
        verb_in = input(f"  {C_BOLD}Selecciona modo (1/2/3) [Por defecto: 1]: {C_RESET}").strip()
    except (KeyboardInterrupt, EOFError):
        verb_in = "1"

    if verb_in == "2":
        verbosity = 1
    elif verb_in == "3":
        verbosity = 2
    else:
        verbosity = 0

    return selected_freqs, selected_gain, bias_tee, save_encrypted, verbosity, auto_dynamic

class MultiChannelMonitor:
    def __init__(self, freqs, gain=0.0, bias_tee=False, sample_rate=2048000, key_hex=None, auto_play=True, out_dir="demod/tmp/live", min_duration=0.30, verbosity=0, save_encrypted=False, aliases_file="talkgroups.json", auto_dynamic=False, web_port=8080, enable_web=True):
        self.freqs = sorted(list(set(int(f) for f in freqs)))
        self.gain = gain
        self.bias_tee = bias_tee
        self.sample_rate = sample_rate
        self.key_hex = key_hex
        self.auto_play = auto_play
        self.out_dir = out_dir
        self.min_duration = min_duration
        self.min_frames = max(15, int(self.min_duration / 0.02))
        self.verbosity = verbosity
        self.save_encrypted = save_encrypted
        self.auto_dynamic = auto_dynamic
        self.web_port = web_port
        self.enable_web = enable_web
        self.aliases = load_talkgroup_aliases(aliases_file)
        self.gps_log_file = os.path.join(self.out_dir, "gps_positions.log")
        self.new_freqs_file = "nuevas_frecuencias.txt"
        self.known_channels = set(self.freqs)
        
        # Estructuras de datos para el Dashboard Web y Mapa
        self.gps_emitters = {}
        self.recent_calls = []
        self.recent_events = []
        self.web_server = None
        os.makedirs(self.out_dir, exist_ok=True)

        min_f = min(self.freqs)
        max_f = max(self.freqs)
        self.center_freq = (min_f + max_f) / 2
        self.span = max_f - min_f

        if self.span > 1.5e6:
            self.sample_rate = 2400000

        self.running = True
        self.lock = threading.Lock()

        self.channel_states = {}
        for idx, f in enumerate(self.freqs):
            color = CH_COLORS[idx % len(CH_COLORS)]
            fifo = os.path.join(self.out_dir, f"live_stream_{f}.fifo")
            if os.path.exists(fifo):
                try:
                    os.remove(fifo)
                except Exception:
                    pass
            os.mkfifo(fifo)

            self.channel_states[f] = {
                "idx": idx + 1,
                "color": color,
                "fifo": fifo,
                "scrambler": None,
                "voice_burst": [],
                "voice_burst_start": None,
                "last_voice_time": 0,
                "total_calls": 0,
                "total_voice_frames": 0,
                "total_data_frames": 0,
                "total_otar_events": 0,
                "total_gps_events": 0,
                "proc_dump": None,
                "in_hang": False,
                "active_group": None,
                "burst_active_group": None,
            }

        self.proc_demod = None

    def get_dashboard_data(self):
        with self.lock:
            channels_data = []
            total_calls = 0
            total_otar = 0
            for f in self.freqs:
                st = self.channel_states.get(f)
                if st:
                    total_calls += st["total_calls"]
                    total_otar += st["total_otar_events"]
                    grp_str = ""
                    if st.get("active_group"):
                        bg = st["active_group"]
                        grp_str = f"{bg['key']}" + (f" ({bg['alias']})" if bg['alias'] else "")
                    channels_data.append({
                        "idx": st["idx"],
                        "freq": f,
                        "total_calls": st["total_calls"],
                        "total_voice": st["total_voice_frames"],
                        "total_data": st["total_data_frames"],
                        "active_group": grp_str
                    })
            return {
                "center_freq": self.center_freq,
                "sample_rate": self.sample_rate,
                "total_calls": total_calls,
                "total_otar": total_otar,
                "channels": channels_data,
                "gps_emitters": self.gps_emitters,
                "recent_calls": self.recent_calls[-20:],
                "events": self.recent_events[-30:]
            }

    def start(self):
        gain_str = f"{self.gain} dB" if self.gain is not None else "AGC (Automática)"
        print(f"\n{C_BOLD}{C_CYAN}============================================================{C_RESET}")
        print(f"{C_BOLD}{C_CYAN}    TETRAPOL MULTI-CANAL SDR (TRUNKING / SIMULTÁNEO)       {C_RESET}")
        print(f"{C_BOLD}{C_CYAN}============================================================{C_RESET}")
        print(f" {C_BOLD}Canales activos ({len(self.freqs)}):{C_RESET}")
        for f in self.freqs:
            st = self.channel_states[f]
            print(f"   • {st['color']}Canal #{st['idx']}: {f/1e6:.4f} MHz ({f} Hz){C_RESET}")
        print(f" {C_BOLD}Frecuencia central SDR:{C_RESET} {self.center_freq/1e6:.4f} MHz | Span: {self.span/1e3:.1f} kHz")
        print(f" {C_BOLD}Ganancia SDR:{C_RESET} {gain_str} | Bias-Tee: {'ACTIVADO (4.5V)' if self.bias_tee else 'DESACTIVADO'}")
        print(f" {C_BOLD}Auto-descubrimiento dinámico [AA]:{C_RESET} {C_GREEN + 'ACTIVADO' if self.auto_dynamic else C_DIM + 'DESACTIVADO'}{C_RESET}")
        print(f" {C_BOLD}Detección GPS / AVL:{C_RESET} {C_GREEN}ACTIVA (Latitud / Longitud){C_RESET}")
        print(f" {C_BOLD}Detección OTAR / Seguridad:{C_RESET} {C_GREEN}ACTIVA{C_RESET}")
        print(f" {C_BOLD}Mapa de flotas (Talkgroups):{C_RESET} {len(self.aliases)} alias cargados")
        print(f" {C_BOLD}Filtro de voz mínima:{C_RESET} >= {self.min_duration:.2f}s ({self.min_frames} tramas)")
        print(f" {C_BOLD}Guardar audios cifrados:{C_RESET} {'SÍ' if self.save_encrypted else 'NO (Solo guardar voz en claro)'}")
        verb_str = "1 (Informativo)" if self.verbosity==1 else ("2 (Debug crudo)" if self.verbosity>=2 else "0 (Limpio)")
        print(f" {C_BOLD}Visualización:{C_RESET} {verb_str}")
        print(f" {C_BOLD}Directorio grabaciones:{C_RESET} {self.out_dir}")
        
        # Iniciar Servidor Web
        if self.enable_web:
            try:
                self.web_server = start_web_dashboard(port=self.web_port, data_callback=self.get_dashboard_data)
                threading.Thread(target=self.web_server.serve_forever, daemon=True).start()
                print(f" {C_BOLD}🌐 Panel Web & Mapa GPS en Vivo:{C_RESET} {C_BOLD}{C_GREEN}http://localhost:{self.web_port}{C_RESET} {C_DIM}(Abrir en navegador o móvil){C_RESET}")
            except Exception as e:
                print(f" {C_YELLOW}Aviso: No se pudo iniciar el panel web en el puerto {self.web_port}: {e}{C_RESET}")

        if self.key_hex:
            print(f" {C_BOLD}Clave de descifrado:{C_RESET} {self.key_hex}")
        print(f"{C_CYAN}------------------------------------------------------------{C_RESET}")
        print(f"{C_DIM}Escuchando en vivo... (Presione Ctrl+C para salir){C_RESET}\n")

        dump_bin = os.path.abspath("./build/apps/tetrapol_dump")

        for f, st in self.channel_states.items():
            proc = subprocess.Popen(
                [dump_bin, "-b", "UHF", "-t", "TCH", "-d", "DOWN", "-i", st["fifo"]],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE if self.verbosity >= 2 else subprocess.DEVNULL,
                text=True,
                bufsize=1
            )
            st["proc_dump"] = proc
            threading.Thread(target=self._channel_reader, args=(f, proc.stdout), daemon=True).start()

        self._start_demodulator()
        threading.Thread(target=self._burst_supervisor, daemon=True).start()

        try:
            while self.running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def _start_demodulator(self):
        freqs_str = ",".join(str(f) for f in self.freqs)
        output_template = os.path.join(self.out_dir, "live_stream_%%.fifo")
        demod_script = os.path.abspath("demod/demod.py")

        osmosdr_args = "rtl=0"
        if self.bias_tee:
            osmosdr_args += ",bias=1"

        cmd_demod = [
            sys.executable, demod_script,
            "-a", osmosdr_args,
            "-f", str(self.center_freq),
            "-l", freqs_str,
            "-s", str(self.sample_rate),
            "-o", output_template
        ]
        if self.gain is not None:
            cmd_demod.extend(["-g", str(self.gain)])

        self.proc_demod = subprocess.Popen(
            cmd_demod,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE if self.verbosity >= 2 else subprocess.DEVNULL,
            text=True
        )

    def _add_channel_dynamically(self, new_freq, ch_id):
        with self.lock:
            if new_freq in self.freqs:
                return
            idx = len(self.channel_states) + 1
            color = CH_COLORS[(idx - 1) % len(CH_COLORS)]
            fifo = os.path.join(self.out_dir, f"live_stream_{new_freq}.fifo")
            if os.path.exists(fifo):
                try: os.remove(fifo)
                except Exception: pass
            os.mkfifo(fifo)

            st = {
                "idx": idx,
                "color": color,
                "fifo": fifo,
                "scrambler": None,
                "voice_burst": [],
                "voice_burst_start": None,
                "last_voice_time": 0,
                "total_calls": 0,
                "total_voice_frames": 0,
                "total_data_frames": 0,
                "total_otar_events": 0,
                "total_gps_events": 0,
                "proc_dump": None,
                "in_hang": False,
                "active_group": None,
                "burst_active_group": None,
            }
            self.channel_states[new_freq] = st
            self.freqs.append(new_freq)
            self.freqs.sort()

            dump_bin = os.path.abspath("./build/apps/tetrapol_dump")
            proc = subprocess.Popen(
                [dump_bin, "-b", "UHF", "-t", "TCH", "-d", "DOWN", "-i", fifo],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1
            )
            st["proc_dump"] = proc
            threading.Thread(target=self._channel_reader, args=(new_freq, proc.stdout), daemon=True).start()

            if self.proc_demod:
                self.proc_demod.terminate()
                time.sleep(0.2)
            self._start_demodulator()

            now = datetime.now().strftime("%H:%M:%S")
            print(f"\n{C_BOLD}{C_GREEN}✨ [{now}] 🔄 [AUTO-SINTONIZACIÓN DINÁMICA EXITOSA]{C_RESET} {color}Canal #{idx} ({new_freq/1e6:.4f} MHz / ID {ch_id}) añadido a la escucha multicanal en directo.{C_RESET}")

    def _channel_reader(self, freq, stdout_pipe):
        st = self.channel_states[freq]
        tag = f"{st['color']}[CH#{st['idx']} {freq/1e6:.4f}MHz]{C_RESET}"

        for line in stdout_pipe:
            line = line.strip()
            if not line:
                continue
            
            if self.verbosity >= 2:
                print(f"{C_DIM}{tag} {line}{C_RESET}")

            try:
                event = json.loads(line)
            except Exception:
                continue

            ev_type = event.get("event")

            if ev_type == "scr":
                scr = event.get("scr")
                if scr != st["scrambler"]:
                    st["scrambler"] = scr
                    if self.verbosity >= 1:
                        now = datetime.now().strftime("%H:%M:%S")
                        print(f"[{now}] {tag} {C_BLUE}ℹ️ Celda TETRAPOL identificada - Scrambler: {scr}{C_RESET}")

            elif ev_type == "frame":
                frame = event.get("frame", {})
                ftype = frame.get("type")
                state = frame.get("state")

                if ftype == "VOICE" and state == "ok":
                    with self.lock:
                        st["total_voice_frames"] += 1
                        now_t = time.time()
                        st["last_voice_time"] = now_t

                        if not st["voice_burst"]:
                            st["voice_burst_start"] = now_t
                            grp = st.get("active_group")
                            if grp and (now_t - grp["time"] < 120):
                                st["burst_active_group"] = grp
                            else:
                                st["burst_active_group"] = None

                        st["voice_burst"].append(line)
                        frames_cnt = len(st["voice_burst"])
                        duration = now_t - st["voice_burst_start"]

                        if frames_cnt >= self.min_frames:
                            if frames_cnt == self.min_frames:
                                st["total_calls"] += 1
                                t_str = datetime.now().strftime("%H:%M:%S")
                                grp_info = ""
                                if st.get("burst_active_group"):
                                    bg = st["burst_active_group"]
                                    grp_info = f" {C_YELLOW}[Grupo: {bg['key']}" + (f" ({bg['alias']})" if bg['alias'] else "") + f"]{C_RESET}"
                                print(f"\n{C_BOLD}{C_GREEN}🔴 [{t_str}] {tag} ¡TRANSMISIÓN DE VOZ EN CURSO! (Llamada #{st['total_calls']}){grp_info}{C_RESET}")

                            sys.stdout.write(f"\r   {tag} {C_RED}▶ Hablando... {duration:.1f}s ({frames_cnt} tramas){C_RESET}   ")
                            sys.stdout.flush()

                elif ftype == "DATA":
                    with self.lock:
                        st["total_data_frames"] += 1

            elif ev_type == "tsdu":
                tsdu = event.get("tsdu", {})
                data_val = (tsdu.get("data") or {}).get("value", "")
                if data_val and data_val != "5812":
                    now = datetime.now().strftime("%H:%M:%S")
                    ch = tsdu.get("log_ch")
                    addr = tsdu.get("addr", {})
                    z = addr.get("z", 0)
                    y = addr.get("y", 7)
                    x = addr.get("x", 4095)
                    addr_key = f"{z}:{y}:{x}"
                    alias = self.aliases.get(addr_key, "")
                    alias_str = f" ({C_BOLD}{alias}{C_RESET})" if alias else ""

                    # 1. Detección de Frecuencias
                    found_channels = extract_tetrapol_channels(data_val)
                    for ch_id, ch_freq in found_channels:
                        if ch_freq not in self.known_channels:
                            self.known_channels.add(ch_freq)
                            try:
                                with open(self.new_freqs_file, "a") as ff:
                                    ff.write(f"[{datetime.now().isoformat()}] Frecuencia: {ch_freq/1e6:.4f} MHz ({ch_freq} Hz) | Canal ID: {ch_id} | Detectada en: {freq/1e6:.4f} MHz | Celda SCR: {st['scrambler']}\n")
                            except Exception:
                                pass

                            in_span = abs(ch_freq - self.center_freq) <= (self.sample_rate / 2.0 - 50000)
                            if in_span:
                                print(f"\n{C_BOLD}{C_MAGENTA}✨ [{now}] {tag} 📡 [NUEVA FRECUENCIA DESCUBIERTA EN BANDA]{C_RESET} {C_BOLD}{ch_freq/1e6:.4f} MHz{C_RESET} (Canal ID: {ch_id})")
                                if self.auto_dynamic:
                                    threading.Thread(target=self._add_channel_dynamically, args=(ch_freq, ch_id), daemon=True).start()
                            else:
                                print(f"\n{C_BOLD}{C_YELLOW}📝 [{now}] {tag} 📋 [NUEVA FRECUENCIA FUERA DE BANDA]{C_RESET} {ch_freq/1e6:.4f} MHz (ID: {ch_id}) -> Guardada en {self.new_freqs_file}")

                    # 2. Detección de Telemetría GPS / AVL (Solo en terminales individuales o tramas NMEA)
                    gps_res = None
                    is_nmea = ("244750" in data_val.lower() or "24474e" in data_val.lower()) # "$GP" o "$GN" en hex
                    if x != 4095 or is_nmea:
                        gps_res = parse_gps_payload(data_val)

                    if gps_res:
                        lat, lon, gps_type = gps_res
                        st["total_gps_events"] += 1
                        lat_dir = "N" if lat >= 0 else "S"
                        lon_dir = "E" if lon >= 0 else "W"
                        print(f"\n{C_BOLD}{C_GREEN}📍 [{now}] {tag} 🛰️ [TELEMETRÍA GPS / AVL]{C_RESET} {C_BOLD}Lat: {abs(lat):.6f}° {lat_dir}, Lon: {abs(lon):.6f}° {lon_dir}{C_RESET} | Terminal: Z:{z} Y:{y} X:{x}{alias_str} | {C_DIM}{gps_type}{C_RESET}")
                        
                        # Actualizar diccionario para el mapa web con historial de ruta
                        with self.lock:
                            if addr_key not in self.gps_emitters:
                                self.gps_emitters[addr_key] = {
                                    "terminal": addr_key,
                                    "alias": alias,
                                    "lat": lat,
                                    "lon": lon,
                                    "time": now,
                                    "freq": freq,
                                    "history": []
                                }
                            em = self.gps_emitters[addr_key]
                            em["lat"] = lat
                            em["lon"] = lon
                            em["time"] = now
                            em["freq"] = freq
                            if alias:
                                em["alias"] = alias
                            # Añadir a la ruta si se ha desplazado o es nuevo
                            if not em["history"] or (abs(em["history"][-1][0] - lat) > 0.00005 or abs(em["history"][-1][1] - lon) > 0.00005):
                                em["history"].append([lat, lon, now])

                            self.recent_events.append({
                                "time": now,
                                "type": "gps",
                                "text": f"GPS: {abs(lat):.4f}° {lat_dir}, {abs(lon):.4f}° {lon_dir} de {alias or addr_key}"
                            })

                        try:
                            with open(self.gps_log_file, "a") as gf:
                                gf.write(f"[{datetime.now().isoformat()}] Freq: {freq} Hz | Terminal: {addr_key} {alias} | Lat: {lat:.6f}, Lon: {lon:.6f} | Type: {gps_type}\n")
                        except Exception:
                            pass

                    # 3. Detección de Opcodes de Seguridad y OTAR
                    op_hex = data_val[:2].lower()
                    sec_info = SECURITY_OPCODES.get(op_hex)
                    if sec_info:
                        op_name, op_desc, is_critical = sec_info
                        st["total_otar_events"] += 1
                        with self.lock:
                            self.recent_events.append({
                                "time": now,
                                "type": "otar",
                                "text": f"Seguridad {op_name}: Terminal {alias or addr_key}"
                            })
                        if is_critical or self.verbosity >= 1:
                            print(f"\n{C_BOLD}{C_CYAN}🔑 [{now}] {tag} 🛡️ [GESTIÓN OTAR / SEGURIDAD]{C_RESET} {C_YELLOW}{op_name}{C_RESET} | Terminal: Z:{z} Y:{y} X:{x}{alias_str} | {C_DIM}{op_desc}{C_RESET}")

                    # 4. Control de Tiempos de Retención (Hang Time) y Grupos
                    if data_val == "5889":
                        if not st.get("in_hang"):
                            st["in_hang"] = True
                            if self.verbosity >= 1:
                                print(f"\n[{now}] {tag} {C_YELLOW}⏸️ Canal en espera de respuesta (Hang Time 30s){C_RESET}")
                    else:
                        st["in_hang"] = False
                        if x != 4095:
                            st["active_group"] = {
                                "z": z, "y": y, "x": x,
                                "key": addr_key,
                                "alias": alias,
                                "time": time.time()
                            }
                            if self.verbosity >= 1 and not sec_info and not gps_res and not found_channels:
                                print(f"\n[{now}] {tag} {C_MAGENTA}📢 Flota/Grupo activo: Z:{z} Y:{y} X:{x}{alias_str} | Canal lógico: {ch}{C_RESET}")

    def _burst_supervisor(self):
        while self.running:
            time.sleep(0.15)
            now = time.time()
            for f, st in list(self.channel_states.items()):
                if st["voice_burst"] and (now - st["last_voice_time"] > 0.8):
                    with self.lock:
                        burst = list(st["voice_burst"])
                        st["voice_burst"] = []
                        burst_grp = st.get("burst_active_group")
                        st["burst_active_group"] = None
                    
                    if len(burst) >= self.min_frames:
                        self._finish_voice_burst(f, burst, burst_grp)
                    elif self.verbosity >= 2:
                        print(f"\n{C_DIM}[Descartado glitch de {len(burst)} tramas ({len(burst)*0.02:.3f}s) en {f/1e6:.4f}MHz]{C_RESET}")

    def _finish_voice_burst(self, freq, burst_lines, burst_group=None):
        st = self.channel_states[freq]
        tag = f"{st['color']}[CH#{st['idx']} {freq/1e6:.4f}MHz]{C_RESET}"
        duration = len(burst_lines) * 0.02
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        time_display = datetime.now().strftime("%H:%M:%S")

        raw_bytes = []
        for l in burst_lines:
            try:
                d = json.loads(l)
                val = d.get("frame", {}).get("data", {}).get("value", "")
                if val:
                    raw_bytes.append(bytes.fromhex(val))
            except Exception:
                pass

        v_class, ent, norm_ent, avg_hamming, reason = classify_voice_burst(raw_bytes)

        if v_class == "ENCRYPTED":
            status_tag = f"{C_RED}[🔒 CIFRADA]{C_RESET}"
            is_encrypted = True
            is_clear = False
        elif v_class == "CLEAR":
            status_tag = f"{C_GREEN}[🔊 EN CLARO]{C_RESET}"
            is_encrypted = False
            is_clear = True
        else:
            status_tag = f"{C_DIM}[⚪ RUIDO/CORRUPTA]{C_RESET}"
            is_encrypted = False
            is_clear = False

        grp_str = ""
        tg_tag = ""
        group_display = ""
        if burst_group:
            group_display = burst_group['alias'] or burst_group['key']
            grp_str = f" | {C_YELLOW}Grupo: {burst_group['key']}" + (f" ({burst_group['alias']})" if burst_group['alias'] else "") + f"{C_RESET}"
            tg_tag = f"_TG_{burst_group['z']}_{burst_group['y']}_{burst_group['x']}"

        print(f"\n[{time_display}] {tag} {C_BOLD}⏹️ Fin llamada #{st['total_calls']}:{C_RESET} {len(burst_lines)} tramas ({duration:.2f}s) | Entropía: {ent:.3f}{grp_str} {status_tag}")

        wav_url = None
        if is_clear or self.save_encrypted or self.key_hex:
            json_tmp = os.path.join(self.out_dir, f"call_{freq}{tg_tag}_{now_str}.json")
            with open(json_tmp, "w") as f:
                for l in burst_lines:
                    f.write(l + "\n")

            wav_suffix = "ENCRYPTED" if is_encrypted else ("CLEARTEXT" if is_clear else "NOISE")
            wav_filename = f"call_{freq}{tg_tag}_{now_str}_{wav_suffix}.wav"
            wav_file = os.path.join(self.out_dir, wav_filename)
            vocoder_bin = os.path.abspath("./build/apps/tetrapol_vocoder")

            cmd = [vocoder_bin, "-i", json_tmp, "-o", wav_file]
            if self.key_hex:
                cmd.extend(["-k", self.key_hex])

            try:
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                print(f"    📁 {tag} Grabación etiquetada: {C_CYAN}{wav_file}{C_RESET}")
                wav_url = f"/audio/{wav_filename}"

                if is_clear and self.auto_play:
                    print(f"    🔊 {tag} {C_GREEN}¡Voz en claro confirmada! Reproduciendo en directo...{C_RESET}")
                    threading.Thread(target=play_audio, args=(wav_file,), daemon=True).start()
                elif is_encrypted and self.verbosity >= 1:
                    print(f"    ⚠️ {tag} {C_YELLOW}Voz cifrada ({reason}). Guardada para probar claves.{C_RESET}")

            except Exception as e:
                print(f"    {C_RED}Error vocoder: {e}{C_RESET}")

        with self.lock:
            self.recent_calls.append({
                "freq": freq,
                "duration": duration,
                "entropy": ent,
                "is_clear": is_clear,
                "group": group_display,
                "time": time_display,
                "wav_url": wav_url
            })
            self.recent_events.append({
                "time": time_display,
                "type": "voice",
                "text": f"Llamada {'EN CLARO' if is_clear else 'Cifrada'} ({duration:.1f}s) en {freq/1e6:.4f} MHz"
            })

    def stop(self):
        self.running = False
        print(f"\n\n{C_YELLOW}Deteniendo monitor...{C_RESET}")
        if self.proc_demod:
            self.proc_demod.terminate()
        for f, st in list(self.channel_states.items()):
            if st["proc_dump"]:
                st["proc_dump"].terminate()
            if os.path.exists(st["fifo"]):
                try:
                    os.remove(st["fifo"])
                except Exception:
                    pass

        print(f"\n{C_BOLD}{C_CYAN}============================================================{C_RESET}")
        print(f"{C_BOLD}             RESUMEN MULTICANAL DE LA SESIÓN{C_RESET}")
        print(f"{C_CYAN}============================================================{C_RESET}")
        for f, st in list(self.channel_states.items()):
            grp_name = f" | Último grupo: {st['active_group']['key']}" if st.get("active_group") else ""
            otar_count = f" | OTAR: {st['total_otar_events']}" if st['total_otar_events'] > 0 else ""
            gps_count = f" | GPS: {st['total_gps_events']}" if st['total_gps_events'] > 0 else ""
            print(f" {st['color']}• Canal {f/1e6:.4f} MHz:{C_RESET} {st['total_calls']} llamadas | {st['total_voice_frames']} tramas voz | {st['total_data_frames']} tramas datos{grp_name}{otar_count}{gps_count}")
        print(f" • Directorio de audios: {self.out_dir}")
        if os.path.exists(self.gps_log_file):
            print(f" • Registro de posiciones GPS: {self.gps_log_file}")
        if os.path.exists(self.new_freqs_file):
            print(f" • Registro de frecuencias descubiertas: {self.new_freqs_file}")
        print(f"{C_CYAN}============================================================{C_RESET}\n")

def parse_freq_arg(arg_str):
    res = []
    for item in str(arg_str).split(","):
        item = item.strip().strip("'\"").strip()
        if not item:
            continue
        val = float(item)
        if val < 1e6:
            val *= 1e6
        res.append(int(val))
    return res

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TETRAPOL Multi-Channel SDR Trunking Monitor")
    parser.add_argument("-f", "--freqs", type=str, default=None, help="Lista de frecuencias separadas por coma")
    parser.add_argument("-g", "--gain", type=float, default=0.0, help="Ganancia SDR en dB (default: 0.0)")
    parser.add_argument("-b", "--bias-tee", action="store_true", help="Activar Bias-Tee (4.5V)")
    parser.add_argument("-s", "--sample-rate", type=int, default=2048000, help="Tasa de muestreo SDR (default: 2048000)")
    parser.add_argument("-k", "--key", type=str, default=None, help="Clave de descifrado hexadecimal (opcional)")
    parser.add_argument("--scan", action="store_true", help="Ejecutar auto-descubrimiento de canales en el Canal de Control")
    parser.add_argument("-aa", "--auto-dynamic", action="store_true", help="Auto-descubrimiento y sintonización dinámica en caliente")
    parser.add_argument("--save-encrypted", action="store_true", help="Guardar archivos WAV de transmisiones cifradas")
    parser.add_argument("--min-duration", type=float, default=0.30, help="Duración mínima de audio en segundos (default: 0.30)")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Nivel de detalle (-v informativo, -vv debug completo)")
    parser.add_argument("--no-play", action="store_true", help="Desactivar auto-reproducción de voz en claro")
    parser.add_argument("--no-web", action="store_true", help="Desactivar servidor web dashboard")
    parser.add_argument("-p", "--port", type=int, default=8080, help="Puerto del servidor web dashboard (default: 8080)")
    parser.add_argument("-o", "--out-dir", type=str, default="demod/tmp/live", help="Directorio de grabaciones")
    parser.add_argument("-a", "--aliases", type=str, default="talkgroups.json", help="Archivo JSON con mapa de alias de Talkgroups")
    args = parser.parse_args()

    save_enc = args.save_encrypted
    verb = args.verbose
    gain = args.gain
    bias_tee = args.bias_tee
    auto_dyn = args.auto_dynamic

    if args.scan:
        freq_list = auto_scan_bch_frequencies(
            control_freq=393.525e6 if not args.freqs else parse_freq_arg(args.freqs)[0],
            gain=gain,
            bias_tee=bias_tee,
            scan_seconds=6
        )
    elif args.freqs is None:
        freq_list, gain, bias_tee, save_enc, verb, auto_dyn = show_interactive_menu()
    else:
        freq_list = parse_freq_arg(args.freqs)

    monitor = MultiChannelMonitor(
        freqs=freq_list,
        gain=gain,
        bias_tee=bias_tee,
        sample_rate=args.sample_rate,
        key_hex=args.key,
        auto_play=not args.no_play,
        out_dir=args.out_dir,
        min_duration=args.min_duration,
        verbosity=verb,
        save_encrypted=save_enc,
        aliases_file=args.aliases,
        auto_dynamic=auto_dyn,
        web_port=args.port,
        enable_web=not args.no_web
    )
    monitor.start()
