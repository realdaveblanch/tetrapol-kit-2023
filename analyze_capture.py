#!/usr/bin/env python3
import sys
import os
import json
from collections import Counter

def analyze_file(path, channel_mode):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return None
    
    total_frames = 0
    frame_types = Counter()
    frame_states = Counter()
    tsdu_channels = Counter()
    tsdu_types = Counter()
    addresses = Counter()
    non_idle_data = []
    scramblers = set()

    with open(path, "r", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except Exception:
                continue
            
            ev = msg.get("event")
            if ev == "scr":
                scramblers.add(msg.get("scr"))
            elif ev == "frame":
                total_frames += 1
                fr = msg.get("frame", {})
                ftype = fr.get("type", "UNKNOWN")
                frame_types[ftype] += 1
                fst = fr.get("state", "UNKNOWN")
                frame_states[fst] += 1
            elif ev == "tsdu":
                t = msg.get("tsdu", {})
                log_ch = t.get("log_ch", "UNKNOWN")
                tsdu_channels[log_ch] += 1
                tp_type = t.get("tpdu_type", "UNKNOWN")
                tsap_id = t.get("tsap_id")
                tsdu_types[f"{tp_type} (tsap:{tsap_id})"] += 1
                
                addr = t.get("addr", {})
                addr_str = f"Z:{addr.get('z')} Y:{addr.get('y')} X:{addr.get('x')}"
                addresses[addr_str] += 1
                
                # Check for non-idle data
                data_val = (t.get("data") or {}).get("value", "")
                if data_val and data_val != "5812":
                    non_idle_data.append((log_ch, addr_str, data_val))

    return {
        "path": path,
        "mode": channel_mode,
        "total_frames": total_frames,
        "frame_types": dict(frame_types),
        "frame_states": dict(frame_states),
        "tsdu_channels": dict(tsdu_channels),
        "tsdu_types": dict(tsdu_types),
        "addresses": dict(addresses),
        "non_idle_data": non_idle_data,
        "scramblers": list(scramblers),
    }

def print_report(res_cch, res_tch):
    print("\n" + "="*60)
    print("        INFORME DE ANÁLISIS DE CAPTURA TETRAPOL")
    print("="*60)
    
    scr_list = set()
    if res_cch and res_cch["scramblers"]:
        scr_list.update(res_cch["scramblers"])
    if res_tch and res_tch["scramblers"]:
        scr_list.update(res_tch["scramblers"])
    
    print(f"[*] Código de Color / Scrambler (SCR): {', '.join(map(str, scr_list)) if scr_list else 'No detectado'}")
    
    for res in [res_cch, res_tch]:
        if not res:
            continue
        print(f"\n--- Modo {res['mode']} ({os.path.basename(res['path'])}) ---")
        print(f"  • Total tramas recibidas: {res['total_frames']}")
        print(f"  • Tipos de trama: {res['frame_types']}")
        print(f"  • Calidad/Estados: {res['frame_states']}")
        if res['tsdu_channels']:
            print(f"  • Canales lógicos (TSDU): {res['tsdu_channels']}")
        if res['tsdu_types']:
            print(f"  • Protocolos/TPDU: {res['tsdu_types']}")
        if res['addresses']:
            print(f"  • Direcciones detectadas: {res['addresses']}")

    print("\n" + "-"*60)
    print("               DIAGNÓSTICO DE TRÁFICO")
    print("-"*60)
    
    voice_frames = 0
    for r in [res_cch, res_tch]:
        if r:
            voice_frames += r["frame_types"].get("VOICE", 0)

    if voice_frames > 0:
        print(f"[!] SE DETECTARON {voice_frames} TRAMAS DE VOZ ACTIVA (VOICE).")
    else:
        print("[i] NO se detectó voz activa en este intervalo.")

    # Check for active vs idle data
    all_non_idle = []
    if res_cch:
        all_non_idle.extend(res_cch["non_idle_data"])
    if res_tch:
        all_non_idle.extend(res_tch["non_idle_data"])

    if all_non_idle:
        print(f"[!] Se detectaron {len(all_non_idle)} paquetes de datos/señalización con contenido útil:")
        for ch, addr, d in all_non_idle[:10]:
            print(f"    - Canal: {ch} | Dirección: {addr} | Datos Hex: {d}")
    else:
        print("[i] Canal en reposo (tramas de relleno / sincronismo desocupado '5812' en 0x7FFF).")
    
    print("="*60 + "\n")

if __name__ == "__main__":
    cch_path = sys.argv[1] if len(sys.argv) > 1 else "demod/tmp/latest_cch.json"
    tch_path = sys.argv[2] if len(sys.argv) > 2 else "demod/tmp/latest_tch.json"

    res_cch = analyze_file(cch_path, "CCH")
    res_tch = analyze_file(tch_path, "TCH")

    if not res_cch and not res_tch:
        print("No se encontraron archivos de log para analizar en", cch_path, tch_path)
        sys.exit(1)

    print_report(res_cch, res_tch)
