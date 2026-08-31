# Capítulo 4: Decodificación de Voz y el Vocoder RPCELP

---

## 4.1. El Reto de la Compresión de Voz en Banda Estrecha

Una señal de audio de voz telefónica estándar digitalizada sin compresión (PCM lineal a $8000\text{ Hz}$ y 16 bits por muestra) genera una tasa de datos de:

$$\text{Tasa PCM} = 8000\text{ muestras/s} \times 16\text{ bits/muestra} = 128\text{ kbit/s}$$

Incluso con compresión básica G.711 (ley A / ley $\mu$), la tasa es de $64\text{ kbit/s}$. Dado que un canal de radio TETRAPOL de $12.5\text{ kHz}$ solo tiene capacidad física para transportar $6.0\text{ kbit/s}$ netos de voz (120 bits cada 20 ms), se requiere un **vocoder paramétrico** con un factor de compresión superior a **$20:1$**.

TETRAPOL utiliza el algoritmo **RPCELP (*Regular Pulse Code Excited Linear Prediction*)**, diseñado para modelar acústicamente el aparato fonador humano (cuerdas vocales y tracto vocal) en lugar de transmitir la forma de onda directa.

---

## 4.2. Estructura de la Trama de Voz de 120 bits

Cada trama de voz de $20\text{ ms}$ contiene exactamente 120 bits organizados jerárquicamente en:
1. **Filtro de Envolvente Espectral (Tracto Vocal):** 10 Coeficientes LAR (*Log Area Ratios*).
2. **Excitación de Cuerdas Vocales y Tono:** 3 Sub-tramas temporales sucesivas que sintetizan 56, 48 y 56 muestras respectivamente ($56 + 48 + 56 = 160\text{ muestras}$, equivalentes a $20\text{ ms}$ de audio a $8000\text{ Hz}$).

```
                  ESTRUCTURA DE BITS DE UNA TRAMA DE VOZ (120 BITS)
┌───────────────────────┬───────────────────────────────┬───────────────────────────────┬───────────────────────────────┐
│ 10 Coeficientes LAR   │ Sub-trama 1 (56 muestras)     │ Sub-trama 2 (48 muestras)     │ Sub-trama 3 (56 muestras)     │
│ (37 bits de filtro)   │ LTP (Lag, Gain) + Excitación  │ LTP (Lag, Gain) + Excitación  │ LTP (Lag, Gain) + Excitación  │
└───────────────────────┴───────────────────────────────┴───────────────────────────────┴───────────────────────────────┘
```

---

## 4.3. Distribución de Bits por Parámetro

De acuerdo con la ingeniería inversa y especificaciones de `rpcelp.c`:

### A. Coeficientes LAR (*Log Area Ratios*)
Los coeficientes LAR representan los logaritmos de las áreas de las secciones transversales del tracto vocal modelado como un tubo acústico no uniforme:
- **LAR 1 a 5:** Coeficientes de baja frecuencia más críticos; sus bits más significativos se sitúan en la zona de mayor protección contra errores.
- **LAR 6 a 10:** Coeficientes de alta frecuencia que afinan el timbre de la voz.

### B. Parámetros LTP (*Long Term Predictor* - Tono / Pitch)
Modela la periodicidad producida por la vibración de las cuerdas vocales en sonidos sonoros (vocales):
- **Lag (Retardo de Pitch):** Determina la frecuencia fundamental de la voz ($F_0$).
- **Gain (Ganancia de Pitch):** Factor de amplificación de la resonancia armónica.

### C. Parámetros Estocásticos (Excitación Residual)
Generan la componente de fricción o ruido para consonantes sordas (s, f, t):
- **Decimation Index:** Determina la densidad del tren de pulsos regulares.
- **Sign + Phase:** Posición de fase y signo de los pulsos de excitación.
- **Excitation Gain:** Amplitud de la energía residual.

---

## 4.4. Proceso de Síntesis Acústica en `tetrapol_vocoder`

El flujo de decodificación en C (`lib/rpcelp.c` y `apps/tetrapol_vocoder.c`) opera de la siguiente forma:

```
                               FLUJO DE SÍNTESIS RPCELP
 ┌──────────────────────────────────────────────────────────────────────────────────┐
 │                     Trama Hexadecimal (15 bytes / 120 bits)                      │
 └────────────────────────────────────────┬─────────────────────────────────────────┘
                                          │
                                          ▼
 ┌──────────────────────────────────────────────────────────────────────────────────┐
 │ 1. Desempaquetado y Descuantificación:                                           │
 │    • Reconstrucción de vectores de bits (vfr)                                    │
 │    • Descuantificación no lineal de 10 coeficientes LAR                         │
 │    • Interpolación temporal de LARs (factores 0.875, 0.500, 0.125)              │
 └────────────────────────────────────────┬─────────────────────────────────────────┘
                                          │
                                          ▼
 ┌──────────────────────────────────────────────────────────────────────────────────┐
 │ 2. Generador de Excitación y Filtro LTP:                                         │
 │    • Decodificación de tren de pulsos estocásticos                               │
 │    • Filtrado de memoria a largo plazo (Pitch Synthesis)                         │
 └────────────────────────────────────────┬─────────────────────────────────────────┘
                                          │
                                          ▼
 ┌──────────────────────────────────────────────────────────────────────────────────┐
 │ 3. Filtro de Síntesis LPC (Tracto Vocal):                                        │
 │    • Filtro en celosía (Lattice Filter de orden 10)                              │
 │    • Salida: 160 muestras normalizadas [-1.0, +1.0]                             │
 └────────────────────────────────────────┬─────────────────────────────────────────┘
                                          │
                                          ▼
 ┌──────────────────────────────────────────────────────────────────────────────────┐
 │ 4. Escalado PCM 16 bits y Empaquetado WAV:                                       │
 │    • Conversión: val_int16 = (int16_t)(val_float * 32767.0)                      │
 │    • Escritura de cabecera RIFF WAVE (8000 Hz, 16-bit Mono)                      │
 └──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4.5. Formato del Archivo WAV de Salida

El archivo de audio generado por `tetrapol_vocoder` es un archivo **WAV estándar (RIFF WAVE)** con la siguiente cabecera canónica de 44 bytes:

| Desplazamiento (Bytes) | Campo | Valor | Descripción |
| :--- | :--- | :--- | :--- |
| `0x00 - 0x03` | `ChunkID` | `"RIFF"` | Identificador de contenedor multimedia |
| `0x04 - 0x07` | `ChunkSize` | $36 + \text{DataSize}$ | Tamaño total del archivo menos 8 bytes |
| `0x08 - 0x0B` | `Format` | `"WAVE"` | Formato de audio digital |
| `0x0C - 0x0F` | `Subchunk1ID` | `"fmt "` | Bloque de descripción de formato |
| `0x10 - 0x13` | `Subchunk1Size` | `16` | Tamaño del subchunk fmt (PCM lineal) |
| `0x14 - 0x15` | `AudioFormat` | `1` | Formato PCM sin compresión |
| `0x16 - 0x17` | `NumChannels` | `1` | Canal Mono |
| `0x18 - 0x1B` | `SampleRate` | `8000` | Frecuencia de muestreo ($8\text{ kHz}$) |
| `0x1C - 0x1F` | `ByteRate` | `16000` | Tasa de bytes ($8000 \times 1 \times 2\text{ B/s}$) |
| `0x20 - 0x21` | `BlockAlign` | `2` | Alineación de bloque ($1\text{ canal} \times 2\text{ bytes}$) |
| `0x22 - 0x23` | `BitsPerSample` | `16` | Resolución de audio ($16\text{ bits}$) |
| `0x24 - 0x27` | `Subchunk2ID` | `"data"` | Inicio de los datos PCM |
| `0x28 - 0x2B` | `Subchunk2Size` | $\text{DataSize}$ | Longitud total de bytes de audio |
