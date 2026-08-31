#!/bin/bash
# TETRAPOL Live Monitor & Audio Recorder Launcher

FREQ=""
GAIN=""
KEY=""
BIAS_TEE=""

VERBOSE=()
SAVE_ENC=""

while [[ "$#" -gt 0 ]]; do
    case $1 in
        -f|--freq) FREQ="$2"; shift ;;
        -g|--gain) GAIN="$2"; shift ;;
        -b|--bias-tee) BIAS_TEE="--bias-tee" ;;
        --scan) SCAN="--scan" ;;
        -aa|--auto-dynamic) AUTO_DYN="-aa" ;;
        --no-web) NO_WEB="--no-web" ;;
        -p|--port) PORT="-p $2"; shift ;;
        -k|--key) KEY="$2"; shift ;;
        -s|--save-encrypted) SAVE_ENC="--save-encrypted" ;;
        -v|-vv|-vvv) VERBOSE+=("$1") ;;
        -h|--help)
            echo "Uso: ./live.sh [-f FRECUENCIA(S)] [-g GANANCIA] [-b] [--scan] [-k CLAVE_HEX] [--save-encrypted] [-v|-vv]"
            echo "Ejemplos:"
            echo "  Menú interactivo guiado:     ./live.sh"
            echo "  Auto-descubrimiento BCH:     ./live.sh --scan"
            echo "  Con Bias-Tee activado:       ./live.sh -b"
            echo "  Ganancia específica (35 dB): ./live.sh -g 35.0"
            echo "  Guardar audios cifrados:     ./live.sh --save-encrypted"
            echo "  Con señalización (-v):       ./live.sh -v"
            echo "  Debug completo (-vv):        ./live.sh -vv"
            echo "  1 canal:                     ./live.sh -f 393.525e6"
            echo "  Varios canales:              ./live.sh -f 393.525e6,393.650e6,393.800e6"
            exit 0
            ;;
        *) echo "Opción desconocida: $1"; exit 1 ;;
    esac
    shift
done

CMD=(python3 live_monitor.py)
if [ -n "${FREQ}" ]; then
    CMD+=(-f "${FREQ}")
fi
if [ -n "${GAIN}" ]; then
    CMD+=(-g "${GAIN}")
fi
if [ -n "${BIAS_TEE}" ]; then
    CMD+=("${BIAS_TEE}")
fi
if [ -n "${SCAN}" ]; then
    CMD+=("${SCAN}")
fi
if [ -n "${AUTO_DYN}" ]; then
    CMD+=("${AUTO_DYN}")
fi
if [ -n "${NO_WEB}" ]; then
    CMD+=("${NO_WEB}")
fi
if [ -n "${PORT}" ]; then
    CMD+=(${PORT})
fi
if [ -n "${KEY}" ]; then
    CMD+=(-k "${KEY}")
fi
if [ -n "${SAVE_ENC}" ]; then
    CMD+=("${SAVE_ENC}")
fi
if [ ${#VERBOSE[@]} -gt 0 ]; then
    CMD+=("${VERBOSE[@]}")
fi

exec "${CMD[@]}"
