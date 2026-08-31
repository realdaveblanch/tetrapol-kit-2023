# 📡 TETRAPOL Toolkit & Live SDR Monitor (2026 Edition)

[![License: GPL v2](https://img.shields.io/badge/License-GPL%20v2-blue.svg)](COPYING)
[![Language: C99 / Python 3](https://img.shields.io/badge/Language-C99%20%2F%20Python%203-green.svg)](#)
[![SDR: RTL-SDR / HackRF / Airspy](https://img.shields.io/badge/SDR-RTL--SDR%20%2F%20HackRF-orange.svg)](#)
[![Documentation](https://img.shields.io/badge/Docs-Technical%20Manual-purple.svg)](MANUAL_TECNICO_TETRAPOL.md)

Suite completa de análisis, demodulación, monitorización multicanal y decodificación de audio para redes de radiocomunicación **TETRAPOL (PAS 0001)** mediante **Radio Definida por Software (SDR)**.

---

## 🌟 Características Principales

- 📻 **Demodulación GMSK Multicanal en Paralelo (*Trunking SDR*):** Sintoniza y demodula simultáneamente hasta **5 portadoras independientes** dentro del ancho de banda de un único receptor RTL-SDR económico ($2.048\text{ MHz}$).
- 🔊 **Vocoder RPCELP Integrado:** Síntesis y decodificación acústica completa de tramas de voz digital de $6.0\text{ kbit/s}$ directamente a formato de audio estándar **WAV (16-bit PCM Mono @ 8000 Hz)**.
- ⚡ **Monitor en Vivo Inteligente (`./live.sh`):** Detección en tiempo real de llamadas de voz, eventos de señalización, balizas y grupos de conversación (*Talkgroups*).
- 🛡️ **Clasificador Criptográfico Estadístico:** Discriminación matemática en tiempo real mediante **Entropía de Shannon Normalizada**, **Distancia de Hamming inter-trama** y **Balance de Bernoulli** para distinguir transmisiones cifradas por flujo (*Stream Cipher*), voz en claro y ruido radioeléctrico.
- 🏷️ **Seguimiento Dinámico de Trunking y Mapa de Flotas (`talkgroups.json`):** Asociación automática en tiempo real de cada llamada con su **Talkgroup (Z:Y:X)** y nombre de flota personalizado, etiquetando los archivos WAV y la consola.
- 🎧 **Reproducción de Audio en Directo:** Escucha inmediata de llamadas en claro a través de los altavoces mediante PulseAudio / ALSA.
- 🔌 **Control de Hardware Avanzado:** Soporte interactivo para **Bias-Tee (4.5V DC)** para LNAs activos y escalonamiento de ganancia RF.
- 📘 **[Manual Técnico y Científico Completo](MANUAL_TECNICO_TETRAPOL.md):** Más de 7 capítulos que detallan la física de radio, arquitectura PAS 0001, matemáticas del vocoder y un glosario pedagógico completo.

---

## 🚀 Inicio Rápido

### 1. Requisitos e Instalación

En sistemas Linux (Ubuntu / Debian / Raspberry Pi OS / WSL2):

```bash
# Instalar dependencias del sistema y GNU Radio
sudo apt update
sudo apt install -y build-essential cmake pkg-config git \
                    libglib2.0-dev libjson-c-dev libcmocka-dev \
                    gnuradio gr-osmosdr rtl-sdr pulseaudio-utils

# Clonar y compilar el proyecto
git clone https://github.com/realdaveblanch/tetrapol-kit-2023.git
cd tetrapol-kit-2023
cmake -B build -S .
cmake --build build
```

---

### 2. Ejecución Interactiva (Menú Asistido)

Simplemente ejecuta el script unificado:

```bash
./live.sh
```

Aparecerá el asistente en consola:

```text
============================================================
          TETRAPOL KIT - PANEL DE CONTROL EN VIVO           
============================================================
  [1] 392.6625 MHz  (Canal 1)
  [2] 392.8000 MHz  (Canal 2)
  [3] 393.5250 MHz  (Canal 3 - Principal)
  [4] 393.6500 MHz  (Canal 4)
  [5] 393.8000 MHz  (Canal 5)

  [T] TODOS los 5 canales a la vez (Trunking simultáneo - Span: 1.14 MHz)
  [M] Introducir frecuencia manual personalizada
------------------------------------------------------------
1. Canales a sintonizar (ej: 1,3,4 o T) [Por defecto: T]: 
2. Ajuste de Ganancia SDR (1..7 o M) [Por defecto: 1 (0.0 dB)]: 
3. ¿Activar Bias-Tee 4.5V? (s/N) [Por defecto: N]: 
4. ¿Deseas guardar archivos WAV de transmisiones cifradas? (s/N) [Por defecto: N]: 
5. Nivel de visualización en consola (1:Limpio / 2:Informativo / 3:Debug) [Por defecto: 1]: 
```

*(Pulsa **`Enter`** en todos los pasos para iniciar el monitoreo óptimo automático).*

---

### 3. Ejemplos de Línea de Comandos

```bash
# Monitoreo de 1 frecuencia específica:
./live.sh -f 393.525e6

# Monitoreo multicanal simultáneo (3 frecuencias) con ganancia de 35 dB:
./live.sh -f 393.525e6,393.650e6,393.800e6 -g 35.0

# Con Bias-Tee activado (alimentación para antena activa/LNA):
./live.sh -b -g 35.0

# Modo informativo (muestra grupos de conversación Z:Y:X y señalización):
./live.sh -v

# Probar descifrado con una clave/máscara hexadecimal:
./live.sh -f 393.525e6 -k "A1B2C3D4E5F6..."
```

---

## 🏗️ Arquitectura del Sistema

```
 ┌───────────────┐     ┌────────────────────────┐     ┌────────────────────────┐
 │   RTL-SDR     │ ──► │ demod.py (GNU Radio)   │ ──► │ Tuberías FIFO / Canal  │
 │ (Muestras I/Q)│     │ • DDC Multicanal       │     │ (live_stream_*.fifo)   │
 └───────────────┘     │ • Demodulación GMSK    │     └───────────┬────────────┘
                       └────────────────────────┘                 │
                                                                  ▼
 ┌───────────────┐     ┌────────────────────────┐     ┌────────────────────────┐
 │ Audio WAV     │ ◄── │ tetrapol_vocoder (C)   │ ◄── │ tetrapol_dump (C)      │
 │ (PCM 8000 Hz) │     │ • Síntesis RPCELP      │     │ • Desempaquetado       │
 │ + Altavoces   │     │ • Filtro LPC + LTP     │     │ • Corrección BCH(160)  │
 └───────────────┘     └────────────────────────┘     └────────────────────────┘
```

---

## 📚 Documentación Técnica

El proyecto cuenta con un manual de ingeniería completo en el directorio [`docs/`](docs/):

- 📖 **[MANUAL_TECNICO_TETRAPOL.md](MANUAL_TECNICO_TETRAPOL.md)** - Libro técnico unificado.
- **[01. Introducción y Comparativa TETRAPOL vs. TETRA](docs/01_introduccion_y_contexto.md)**
- **[02. El Estándar TETRAPOL y Arquitectura de Protocolo (PAS 0001)](docs/02_estandar_y_arquitectura_protocolo.md)**
- **[03. Procesamiento Digital de Señales (DSP) y SDR](docs/03_procesamiento_senales_y_sdr.md)**
- **[04. Decodificación de Voz y el Vocoder RPCELP](docs/04_decodificacion_y_vocoder_rpcelp.md)**
- **[05. Cifrado de Flujo y Análisis Estadístico de Tráfico](docs/05_cifrado_y_analisis_estadistico.md)**
- **[06. Arquitectura del Software, Concurrencia e Implementación](docs/06_arquitectura_software_e_implementacion.md)**
- **[07. Glosario Exhaustivo de Conceptos y Tecnicismos](docs/07_glosario_terminologico.md)**

---

## ⚖️ Licencia y Aspectos Legales

Este proyecto es software libre publicado bajo los términos de la **[GNU General Public License v2.0](COPYING)** (GPL-2.0).

- Eres libre de usar, estudiar, modificar, realizar forks y redistribuir este software.
- Cualquier trabajo derivado debe mantenerse bajo la misma licencia GPL-2.0 de código abierto.
- Consulta el archivo [`COPYING`](COPYING) para ver el texto completo de la licencia.
