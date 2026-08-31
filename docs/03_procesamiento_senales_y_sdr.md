# Capítulo 3: Procesamiento Digital de Señales (DSP) y Radio Definida por Software (SDR)

---

## 3.1. Fundamentos de Recepción SDR y Muestreo I/Q

En un receptor digital moderno, la señal de radiofrecuencia (RF) capturada por la antena se digitaliza en banda base mediante **muestras complejas en fase y cuadratura ($I/Q$)**:

$$s(t) = I(t) + j \cdot Q(t) = A(t) \cdot e^{j \phi(t)}$$

Donde:
- $I(t)$ (*In-Phase*): Componente real de la señal.
- $Q(t)$ (*Quadrature*): Componente imaginaria desfasada $90^\circ$.
- $A(t) = \sqrt{I^2(t) + Q^2(t)}$: Envolvente de amplitud instantánea.
- $\phi(t) = \arctan\left(\frac{Q(t)}{I(t)}\right)$: Fase instantánea de la modulación.

El receptor RTL-SDR muestrea el espectro radioeléctrico a una tasa de **$f_s = 2.048\text{ Msps}$** (2.048.000 muestras complejas por segundo). De acuerdo con el teorema de muestreo de Nyquist-Shannon, esto permite capturar simultáneamente una ventana espectral de **$2.048\text{ MHz}$ de ancho de banda instantáneo**, dentro de la cual pueden convivir múltiples portadoras TETRAPOL adyacentes.

---

## 3.2. Diagrama de Bloques DSP del Demodulador (`demod.py`)

La cadena de procesamiento implementada en GNU Radio consta de los siguientes bloques:

```
                          CADENA DE DEMODULACIÓN GMSK POR CANAL
 ┌──────────────────────────────────────────────────────────────────────────────────┐
 │                          RTL-SDR (Muestras I/Q @ 2.048 Msps)                     │
 └────────────────────────────────────────┬─────────────────────────────────────────┘
                                          │
                                          ▼
                ┌───────────────────────────────────────────────────┐
                │   Frequency Translating FIR Filter (DDC)          │
                │   • Traslación de frecuencia: Δf = f_ch - f_center│
                │   • Filtro Paso Bajo: Ventana HANN (BW: 4.6 kHz)  │
                │   • Diezmado (Decimation): Muestras @ 32.0 kSps   │
                └─────────────────────────┬─────────────────────────┘
                                          │
                                          ▼
                ┌───────────────────────────────────────────────────┐
                │   Demodulador FM / Cuadratura (GMSK)              │
                │   • Detección de desviación de fase instantánea   │
                └─────────────────────────┬─────────────────────────┘
                                          │
                                          ▼
                ┌───────────────────────────────────────────────────┐
                │   Recuperador de Reloj Mueller & Müller (Clock MM)│
                │   • Sincronización de símbolo @ 8000 Baudios      │
                └─────────────────────────┬─────────────────────────┘
                                          │
                                          ▼
                ┌───────────────────────────────────────────────────┐
                │   Decisor de Bits (Slicer) y Salida a FIFO        │
                │   • Mapeo a bytes brutos (0/1) hacia tetrapol_dump│
                └───────────────────────────────────────────────────┘
```

---

## 3.3. Detalles Matemáticos de los Bloques

### 1. Conversor Digital Descendente (*Digital Down-Converter - DDC*)
Para sintonizar un canal situado a la frecuencia $f_{\text{ch}}$ dentro del ancho de banda capturado centrado en $f_{\text{center}}$, se aplica una traslación de frecuencia compleja:

$$x_{\text{DDC}}(t) = s(t) \cdot e^{-j 2\pi (f_{\text{ch}} - f_{\text{center}}) t}$$

A continuación, un filtro FIR paso bajo (*Low-Pass Filter*) con coeficientes calculados mediante ventana de Hann aisla el ancho de banda del canal ($12.5\text{ kHz}$) y diezma la señal a una frecuencia de muestreo manejable ($32.0\text{ kSps}$, correspondiente a 4 muestras por símbolo).

### 2. Modulación GMSK ($BT = 0.25$)
TETRAPOL utiliza **GMSK (*Gaussian Minimum Shift Keying*)**:
- Es una modulación de fase continua (CPM) derivada de MSK donde los pulsos digitales rectangulares pasan previamente por un filtro Gaussiano con producto ancho de banda-tiempo $BT = 0.25$.
- **Ventaja:** Envolvente de amplitud constante ($A(t) = \text{cte}$), lo que permite utilizar amplificadores de potencia RF en clase C altamente eficientes en los repetidores y terminales portátiles, evitando la distorsión no lineal y maximizando la duración de la batería.

### 3. Recuperación de Reloj Mueller & Müller
El bloque `digital.clock_recovery_mm_ff` ajusta dinámicamente el instante óptimo de muestreo de cada símbolo mediante un lazo de seguimiento de error de fase de reloj, compensando las pequeñas derivas de cuarzo entre el transmisor y el dongle SDR.

---

## 3.4. Arquitectura Multicanal Simultánea (*Channelizer / Trunking SDR*)

Tradicionalmente, para escuchar $N$ canales de radio se requerían $N$ receptores físicos independientes. Gracias al diseño del *Channelizer* en `live_monitor.py` y `demod.py`:

1. **Sintonía Central Inteligente:**
   El software calcula la frecuencia central media:
   $$f_{\text{center}} = \frac{\min(f_1, \dots, f_N) + \max(f_1, \dots, f_N)}{2}$$
2. **Banco de Filtros Polifase en Paralelo:**
   A partir del flujo I/Q único del SDR, se bifurcan en paralelo $N$ filtros DDC independientes en memoria.
3. **Tuberías Inter-Proceso (FIFOs):**
   Cada canal demodulado escribe sus bits en un FIFO individual (`live_stream_<freq>.fifo`), alimentando a $N$ instancias paralelas del decodificador `tetrapol_dump` sin contención ni pérdidas de paquetes.

---

## 3.5. Bias-Tee y Optimización de la Ganancia RF

### A. Bias-Tee (Alimentación por Coaxial)
El circuito **Bias-Tee** inyecta un voltaje continuo de **$4.5\text{ V}$ DC** a través del cable coaxial de la antena para alimentar preamplificadores de bajo ruido (**LNA**) situados junto a la antena.
- Activar el Bias-Tee compensa las pérdidas de señal introducidas por tiradas largas de cable coaxial y mejora la figura de ruido global del sistema.

### B. Ajuste de Ganancia y Rango Dinámico
El sintonizador del RTL-SDR (Rafael Micro R820T2 / R828D) dispone de etapas de ganancia LNA, Mezclador y VGA ajustables:
- **$0\text{ dB}$ (Directa / Mínima):** Ideal en presencia de señales muy fuertes o repetidores cercanos, evitando saturación del conversor analógico-digital (ADC) y productos de intermodulación.
- **$28 - 40\text{ dB}$ (Media-Alta):** Nivel óptimo para captar repetidores distantes con buena relación señal a ruido (SNR).
