# Capítulo 6: Arquitectura del Software, Componentes e Implementación

---

## 6.1. Estructura y Árbol del Repositorio

El proyecto `tetrapol-kit-2023` se organiza de forma modular combinando librerías de bajo nivel en C con scripts de procesamiento y monitorización en tiempo real en Python y Bash:

```
tetrapol-kit-2023/
├── CMakeLists.txt                # Configuración global del sistema de compilación
├── apps/                         # Aplicaciones ejecutables en C
│   ├── CMakeLists.txt
│   ├── tetrapol_dump.c           # Decodificador principal de tramas físicas a JSON
│   ├── tetrapol_vocoder.c        # Sintetizador de audio RPCELP a archivo WAV
│   └── tetrapol_build.c          # Ensamblador de tramas sintéticas para testing
├── lib/                          # Núcleo de la librería libtetrapol.a
│   ├── CMakeLists.txt
│   ├── bch.c                     # Corrector de errores BCH (160, 120) y (120, 72)
│   ├── rpcelp.c                  # Implementación matemática del Vocoder RPCELP
│   ├── frame.c                   # Desempaquetado y parseo de tramas binarias
│   ├── frame_json.c              # Serializador de eventos a formato JSON
│   ├── tch.c / cch.c             # Lógica de canales de tráfico y control
│   ├── tsdu.c / tsdu_print.c     # Decodificador de unidades de datos de señalización
│   └── tetrapol/                 # Cabeceras públicas C (.h)
├── demod/                        # Demodulación SDR en GNU Radio
│   └── demod.py                  # Receptor GMSK multicanal y DDC
├── live_monitor.py               # Monitor en vivo, clasificador y gestor multicanal
├── live.sh                       # Lanzador interactivo unificado
├── analyze_capture.py            # Analizador estadístico de capturas JSON
└── docs/                         # Documentación técnica completa
```

---

## 6.2. Flujo de Datos Integral (*End-to-End Pipeline*)

El siguiente diagrama ilustra el recorrido de los datos desde la antena receptora hasta la generación y reproducción del archivo de audio:

```
                            PIPELINE INTEGRAL DE DATOS
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                Antena RF + RTL-SDR (Blog V4 @ 393.231 MHz)                  │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │ Muestras I/Q (2.048 Msps)
                                        ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │          demod.py (GNU Radio - DDC Multicanal + Demodulador GMSK)           │
 └──────┬───────────────────────────────┬───────────────────────────────┬──────┘
        │ Ch 1 (Bits 8 kbps)            │ Ch 2 (Bits 8 kbps)            │ Ch 3..5
        ▼                               ▼                               ▼
 ┌──────────────┐                ┌──────────────┐                ┌──────────────┐
 │ FIFO Canal 1 │                │ FIFO Canal 2 │                │ FIFO Canal N │
 └──────┬───────┘                └──────┬───────┘                └──────┬───────┘
        │                               │                               │
        ▼                               ▼                               ▼
 ┌──────────────┐                ┌──────────────┐                ┌──────────────┐
 │tetrapol_dump │                │tetrapol_dump │                │tetrapol_dump │
 │ (C / libtp)  │                │ (C / libtp)  │                │ (C / libtp)  │
 └──────┬───────┘                └──────┬───────┘                └──────┬───────┘
        │ Eventos JSON                  │ Eventos JSON                  │ Eventos JSON
        └───────────────────────┬───────┴───────────────────────────────┘
                                │
                                ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │    live_monitor.py (Supervisor Multihilo + Clasificador Estadístico)        │
 │    • Detección de inicio/fin de ráfagas PTT                                 │
 │    • Análisis de Entropía Normalizada, Hamming y Bernoulli                  │
 │    • Si es Cifrada sin clave ──► Descarte en memoria (Disco limpio)         │
 │    • Si es Voz en Claro      ──► Generación de audio y reproducción         │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
                                        ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │          tetrapol_vocoder (C - Sintetizador RPCELP a PCM 16-bit)            │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
                                        ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                  Archivo WAV (8000 Hz Mono) + paplay / aplay                │
 └─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6.3. Comunicación Inter-Procesos (IPC) y Concurrencia

1. **Tuberías Nombradas (FIFOs):**  
   Se crean tuberías FIFO mediante `os.mkfifo()` en `demod/tmp/live/`. Permiten que el demodulador en Python escriba los bits demodulados mientras el proceso en C `tetrapol_dump` los consume de forma síncrona y continua sin latencia de disco.
2. **Arquitectura Multihilo en `live_monitor.py`:**
   - **Hilos Lectores de Canal (`_channel_reader`):** Un hilo por cada frecuencia activa que procesa las líneas JSON generadas por `tetrapol_dump`.
   - **Hilo Supervisor de Ráfagas (`_burst_supervisor`):** Evalúa cada 150 ms si una transmisión de voz ha terminado (silencio $> 0.8\text{ s}$) para cerrar la ráfaga, clasificarla y despachar el vocoder.
   - **Hilos de Audio Asíncrono:** La reproducción con `paplay` o `aplay` se ejecuta en un hilo desacoplado para no bloquear la decodificación de nuevas llamadas entrantes.

---

## 6.4. Manual de Uso y Parámetros del Sistema

### Modo Interactivo (Recomendado)
```bash
./live.sh
```
Inicia el asistente en 5 pasos que permite configurar frecuencias, ganancia SDR (0 dB por defecto), Bias-Tee, guardado de cifradas y nivel de detalle.

### Opciones de Línea de Comandos
```bash
Uso: ./live.sh [-f FRECUENCIAS] [-g GANANCIA] [-b] [-k CLAVE] [--save-encrypted] [-v|-vv]

Banderas disponibles:
  -f, --freq           Frecuencia o lista de frecuencias separadas por coma (ej: 393.525e6,392.800e6).
  -g, --gain           Ganancia del SDR en dB (ej: 0.0, 35.0, 40.2). Por defecto: 0.0 dB.
  -b, --bias-tee       Activa la alimentación Bias-Tee de 4.5V para LNAs / antenas activas.
  -k, --key            Clave o máscara hexadecimal para pruebas de descifrado XOR.
  -s, --save-encrypted Guarda archivos WAV de transmisiones cifradas (por defecto desactivado).
  -v                   Modo Informativo (Muestra grupos de conversación Z:Y:X y señalización).
  -vv                  Modo Depuración Total (Muestra el flujo de datos y tramas en crudo).
  -h, --help           Muestra la ayuda de opciones.
```
