#!/usr/bin/env python3
import sys
import os
import time
import json
import math
import argparse
import subprocess
import threading
from collections import Counter
from datetime import datetime

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

# Lista de canales conocidos
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

def classify_voice_burst(raw_bytes_list):
    """
    Clasificador estadístico multicriterio para distinguir:
    - Voz cifrada (Stream cipher / PRNG keystream)
    - Voz en claro real (RPCELP LPC dinámico)
    - Ruido / Repeticiones / Glitches de sincronismo
    """
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
    print(f"  {C_BOLD}[M]{C_RESET} {C_BLUE}Introducir frecuencia manual personalizada{C_RESET}")
    print(f"{C_CYAN}------------------------------------------------------------{C_RESET}")

    # 1. Selección de frecuencias
    try:
        choice = input(f"{C_BOLD}1. Canales a sintonizar (ej: 1,3,4 o T) [Por defecto: T]: {C_RESET}").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nSaliendo...")
        sys.exit(0)

    if not choice or choice.upper() == "T" or choice.upper() == "TODOS":
        selected_freqs = [ch["freq"] for ch in DEFAULT_CHANNELS]
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

    selected_freqs = sorted(list(set(selected_freqs)))

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
    print(f"  {C_BOLD}[1]{C_RESET} {C_GREEN}Modo Limpio{C_RESET} {C_DIM}(Solo alertas de llamadas de voz y grabaciones){C_RESET}")
    print(f"  {C_BOLD}[2]{C_RESET} {C_YELLOW}Modo Informativo{C_RESET} {C_DIM}(Muestra grupos de conversación Z:Y:X, señalización y celdas de forma intuitiva){C_RESET}")
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

    return selected_freqs, selected_gain, bias_tee, save_encrypted, verbosity

class MultiChannelMonitor:
    def __init__(self, freqs, gain=0.0, bias_tee=False, sample_rate=2048000, key_hex=None, auto_play=True, out_dir="demod/tmp/live", min_duration=0.30, verbosity=0, save_encrypted=False):
        self.freqs = sorted(list(set(int(f) for f in freqs)))
        self.gain = gain
        self.bias_tee = bias_tee
        self.sample_rate = sample_rate
        self.key_hex = key_hex
        self.auto_play = auto_play
        self.out_dir = out_dir
        self.min_duration = min_duration
        self.min_frames = max(15, int(self.min_duration / 0.02))  # Mínimo 15 tramas (0.30s)
        self.verbosity = verbosity
        self.save_encrypted = save_encrypted
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
                "proc_dump": None,
                "in_hang": False,
            }

        self.proc_demod = None

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
        print(f" {C_BOLD}Filtro de voz mínima:{C_RESET} >= {self.min_duration:.2f}s ({self.min_frames} tramas)")
        print(f" {C_BOLD}Guardar audios cifrados:{C_RESET} {'SÍ' if self.save_encrypted else 'NO (Solo guardar voz en claro)'}")
        verb_str = "1 (Informativo: Grupos y Señalización)" if self.verbosity==1 else ("2 (Debug crudo)" if self.verbosity>=2 else "0 (Limpio: Solo voz)")
        print(f" {C_BOLD}Visualización:{C_RESET} {verb_str}")
        print(f" {C_BOLD}Directorio grabaciones:{C_RESET} {self.out_dir}")
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

        threading.Thread(target=self._burst_supervisor, daemon=True).start()

        try:
            while self.running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

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

                        st["voice_burst"].append(line)
                        frames_cnt = len(st["voice_burst"])
                        duration = now_t - st["voice_burst_start"]

                        if frames_cnt >= self.min_frames:
                            if frames_cnt == self.min_frames:
                                st["total_calls"] += 1
                                t_str = datetime.now().strftime("%H:%M:%S")
                                print(f"\n{C_BOLD}{C_GREEN}🔴 [{t_str}] {tag} ¡TRANSMISIÓN DE VOZ EN CURSO! (Llamada #{st['total_calls']}){C_RESET}")

                            sys.stdout.write(f"\r   {tag} {C_RED}▶ Hablando... {duration:.1f}s ({frames_cnt} tramas){C_RESET}   ")
                            sys.stdout.flush()

                elif ftype == "DATA":
                    with self.lock:
                        st["total_data_frames"] += 1

            elif ev_type == "tsdu" and self.verbosity >= 1:
                tsdu = event.get("tsdu", {})
                data_val = (tsdu.get("data") or {}).get("value", "")
                if data_val and data_val != "5812":
                    now = datetime.now().strftime("%H:%M:%S")
                    ch = tsdu.get("log_ch")
                    addr = tsdu.get("addr", {})
                    addr_key = f"Z:{addr.get('z')} Y:{addr.get('y')} X:{addr.get('x')}"
                    
                    if data_val == "5889":
                        if not st.get("in_hang"):
                            st["in_hang"] = True
                            print(f"\n[{now}] {tag} {C_YELLOW}⏸️ Canal en espera de respuesta (Hang Time 30s){C_RESET}")
                    else:
                        st["in_hang"] = False
                        if addr.get("x") != 4095:
                            print(f"\n[{now}] {tag} {C_MAGENTA}📢 Flota/Grupo activo: {addr_key} | Canal lógico: {ch}{C_RESET}")

    def _burst_supervisor(self):
        while self.running:
            time.sleep(0.15)
            now = time.time()
            for f, st in self.channel_states.items():
                if st["voice_burst"] and (now - st["last_voice_time"] > 0.8):
                    with self.lock:
                        burst = list(st["voice_burst"])
                        st["voice_burst"] = []
                    
                    if len(burst) >= self.min_frames:
                        self._finish_voice_burst(f, burst)
                    elif self.verbosity >= 2:
                        print(f"\n{C_DIM}[Descartado glitch de {len(burst)} tramas ({len(burst)*0.02:.3f}s) en {f/1e6:.4f}MHz]{C_RESET}")

    def _finish_voice_burst(self, freq, burst_lines):
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

        print(f"\n[{time_display}] {tag} {C_BOLD}⏹️ Fin llamada #{st['total_calls']}:{C_RESET} {len(burst_lines)} tramas ({duration:.2f}s) | Entropía: {ent:.3f} {status_tag}")

        if not is_clear and not self.save_encrypted and not self.key_hex:
            if is_encrypted:
                print(f"    ℹ️ {tag} {C_DIM}Audio cifrado descartado (no se guarda archivo WAV).{C_RESET}")
            return

        json_tmp = os.path.join(self.out_dir, f"call_{freq}_{now_str}.json")
        with open(json_tmp, "w") as f:
            for l in burst_lines:
                f.write(l + "\n")

        wav_suffix = "ENCRYPTED" if is_encrypted else ("CLEARTEXT" if is_clear else "NOISE")
        wav_file = os.path.join(self.out_dir, f"call_{freq}_{now_str}_{wav_suffix}.wav")
        vocoder_bin = os.path.abspath("./build/apps/tetrapol_vocoder")

        cmd = [vocoder_bin, "-i", json_tmp, "-o", wav_file]
        if self.key_hex:
            cmd.extend(["-k", self.key_hex])

        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            print(f"    📁 {tag} Grabación: {C_CYAN}{wav_file}{C_RESET}")

            if is_clear and self.auto_play:
                print(f"    🔊 {tag} {C_GREEN}¡Voz en claro confirmada! Reproduciendo en directo...{C_RESET}")
                threading.Thread(target=play_audio, args=(wav_file,), daemon=True).start()
            elif is_encrypted and self.verbosity >= 1:
                print(f"    ⚠️ {tag} {C_YELLOW}Voz cifrada ({reason}). Guardada para probar claves.{C_RESET}")

        except Exception as e:
            print(f"    {C_RED}Error vocoder: {e}{C_RESET}")

    def stop(self):
        self.running = False
        print(f"\n\n{C_YELLOW}Deteniendo monitor...{C_RESET}")
        if self.proc_demod:
            self.proc_demod.terminate()
        for f, st in self.channel_states.items():
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
        for f, st in self.channel_states.items():
            print(f" {st['color']}• Canal {f/1e6:.4f} MHz:{C_RESET} {st['total_calls']} llamadas reales | {st['total_voice_frames']} tramas voz | {st['total_data_frames']} tramas datos")
        print(f" • Directorio de audios: {self.out_dir}")
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
    parser.add_argument("--save-encrypted", action="store_true", help="Guardar archivos WAV de transmisiones cifradas")
    parser.add_argument("--min-duration", type=float, default=0.30, help="Duración mínima de audio en segundos (default: 0.30)")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Nivel de detalle (-v informativo, -vv debug completo)")
    parser.add_argument("--no-play", action="store_true", help="Desactivar auto-reproducción de voz en claro")
    parser.add_argument("-o", "--out-dir", type=str, default="demod/tmp/live", help="Directorio de grabaciones")
    args = parser.parse_args()

    save_enc = args.save_encrypted
    verb = args.verbose
    gain = args.gain
    bias_tee = args.bias_tee

    if args.freqs is None:
        freq_list, gain, bias_tee, save_enc, verb = show_interactive_menu()
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
        save_encrypted=save_enc
    )
    monitor.start()
