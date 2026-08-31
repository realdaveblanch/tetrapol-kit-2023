#!/bin/bash
set -e

FREQ=393525000
FREQ_HZ=393.525e6
GAIN=35.0
SAMP_RATE=2048000
DURATION=40
OUT_DIR="demod/tmp"

mkdir -p "${OUT_DIR}"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BITFILE="${OUT_DIR}/channel_${FREQ}_${TIMESTAMP}.bits"
CCH_LOG="${OUT_DIR}/dump_cch_${FREQ}_${TIMESTAMP}.json"
TCH_LOG="${OUT_DIR}/dump_tch_${FREQ}_${TIMESTAMP}.json"

echo "=== Capturando y demodulando en 393.525 MHz durante ${DURATION} segundos ==="
timeout ${DURATION} python3 demod/demod.py \
    -a "rtl=0" \
    -f ${FREQ_HZ} \
    -l ${FREQ} \
    -g ${GAIN} \
    -s ${SAMP_RATE} \
    -o "${BITFILE}" || true

if [ ! -s "${BITFILE}" ]; then
    echo "No se recibieron bits o el archivo está vacío: ${BITFILE}"
    exit 1
fi

# Actualizar enlaces al último archivo
cp -f "${BITFILE}" "${OUT_DIR}/latest_bits.bits"

echo "=== Decodificando Canal de Control (CCH) ==="
./build/apps/tetrapol_dump -b UHF -t CCH -d DOWN -i "${BITFILE}" > "${CCH_LOG}" 2>"${OUT_DIR}/cch_${FREQ}_${TIMESTAMP}.err" || true
cp -f "${CCH_LOG}" "${OUT_DIR}/latest_cch.json"

echo "=== Decodificando Canal de Tráfico (TCH) ==="
./build/apps/tetrapol_dump -b UHF -t TCH -d DOWN -i "${BITFILE}" > "${TCH_LOG}" 2>"${OUT_DIR}/tch_${FREQ}_${TIMESTAMP}.err" || true
cp -f "${TCH_LOG}" "${OUT_DIR}/latest_tch.json"

echo "=== Analizando resultados ==="
python3 ./analyze_capture.py "${CCH_LOG}" "${TCH_LOG}"

WAV_OUT="${OUT_DIR}/audio_${FREQ}_${TIMESTAMP}.wav"
./build/apps/tetrapol_vocoder -i "${TCH_LOG}" -o "${WAV_OUT}" 2>/dev/null || true
if [ -f "${WAV_OUT}" ]; then
    cp -f "${WAV_OUT}" "${OUT_DIR}/latest_audio.wav"
fi

echo "=== Proceso completado. Archivos guardados en ${OUT_DIR}/ con marca de tiempo ${TIMESTAMP} ==="
