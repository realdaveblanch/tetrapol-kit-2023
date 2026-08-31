# MANUAL TÉCNICO Y CIENTÍFICO DE TETRAPOL & TETRAPOL-KIT-2023
### Ingeniería de Radiofrecuencia, Arquitectura de Protocolo, DSP, Criptografía y Vocoder RPCELP

---

## Índice General

1. [Capítulo 1: Introducción, Historia y Fundamentos de TETRAPOL](docs/01_introduccion_y_contexto.md)
   - 1.1. Introducción y Contexto
   - 1.2. Comparativa Técnica: TETRAPOL vs. TETRA
   - 1.3. Objetivos del Proyecto tetrapol-kit-2023
2. [Capítulo 2: El Estándar TETRAPOL y su Arquitectura de Protocolo](docs/02_estandar_y_arquitectura_protocolo.md)
   - 2.1. Estructura en Capas del Estándar (PAS 0001)
   - 2.2. Capa Física y Estructura de Trama Temporal
   - 2.3. Codificación de Canal y Corrección de Errores (BCH)
   - 2.4. Canales Lógicos: CCH frente a TCH
   - 2.5. Jerarquía de Direccionamiento y Códigos de Color (SCR)
   - 2.6. Tramas Especiales de Mantenimiento y Retención
3. [Capítulo 3: Procesamiento Digital de Señales (DSP) y Radio Definida por Software (SDR)](docs/03_procesamiento_senales_y_sdr.md)
   - 3.1. Fundamentos de Recepción SDR y Muestreo I/Q
   - 3.2. Diagrama de Bloques DSP del Demodulador (demod.py)
   - 3.3. Detalles Matemáticos de los Bloques
   - 3.4. Arquitectura Multicanal Simultánea (Channelizer / Trunking SDR)
   - 3.5. Bias-Tee y Optimización de la Ganancia RF
4. [Capítulo 4: Decodificación de Voz y el Vocoder RPCELP](docs/04_decodificacion_y_vocoder_rpcelp.md)
   - 4.1. El Reto de la Compresión de Voz en Banda Estrecha
   - 4.2. Estructura de la Trama de Voz de 120 bits
   - 4.3. Distribución de Bits por Parámetro
   - 4.4. Proceso de Síntesis Acústica en tetrapol_vocoder
   - 4.5. Formato del Archivo WAV de Salida
5. [Capítulo 5: Cifrado, Criptografía y Análisis Estadístico de Tráfico](docs/05_cifrado_y_analisis_estadistico.md)
   - 5.1. Arquitectura de Seguridad TETRAPOL (PAS 0001-16)
   - 5.2. Mecánica del Cifrado de Flujo y Keystream Dinámico
   - 5.3. Análisis Estadístico y Clasificador Multicriterio
6. [Capítulo 6: Arquitectura del Software, Componentes e Implementación](docs/06_arquitectura_software_e_implementacion.md)
   - 6.1. Estructura y Árbol del Repositorio
   - 6.2. Flujo de Datos Integral (End-to-End Pipeline)
   - 6.3. Comunicación Inter-Procesos (IPC) y Concurrencia
   - 6.4. Manual de Uso y Parámetros del Sistema
7. [Capítulo 7: Glosario Exhaustivo de Conceptos y Tecnicismos](docs/07_glosario_terminologico.md)

---

# Capítulo 1: Introducción, Historia y Fundamentos de TETRAPOL

---

## 1.1. Introducción y Contexto

En el ámbito de las radiocomunicaciones móviles privadas para misiones críticas (**PMR / PAMR - *Professional Mobile Radio***), la seguridad pública, los servicios de emergencias, los cuerpos policiales y las infraestructuras de defensa requieren sistemas de comunicación inalámbrica con una fiabilidad, disponibilidad, resistencia y privacidad sustancialmente superiores a las redes celulares comerciales (GSM, LTE, 5G).

Durante la década de 1990 surgieron en Europa dos grandes estándares digitales de radio troncalizada (*Trunking*):
1. **TETRA (*Terrestrial Trunked Radio*)**: Desarrollado bajo el auspicio del Instituto Europeo de Normas de Telecomunicaciones (**ETSI**).
2. **TETRAPOL**: Desarrollado originalmente por **Matra Communications** (posteriormente integrada en **EADS Telecom**, luego **Cassidian** y hoy en día **Airbus Defence and Space**) y estandarizado por el **TETRAPOL Forum** mediante las especificaciones públicas **PAS 0001** (*Publicly Available Specification*).

TETRAPOL fue concebido específicamente para despliegues nacionales de seguridad del Estado a gran escala. Entre sus implementaciones más emblemáticas a nivel mundial destacan:
- **Red SIRDEE** (*Sistema de Radiocomunicaciones Digitales de Emergencia del Estado*) en **España**: Da cobertura nacional y servicio conjunto a la Guardia Civil, Policía Nacional, Dirección General de Tráfico y unidades de Protección Civil.
- **Red ACROPOL** y **RUBIS** en **Francia**: Utilizadas por la *Police Nationale* y la *Gendarmerie Nationale*.
- **Red POLYCOM** en **Suiza**: Red nacional unificada de salvamento, aduanas y policía.
- Despliegues estratégicos en México, República Checa, Eslovaquia y fuerzas armadas de diversos países de la OTAN.

---

## 1.2. Comparativa Técnica: TETRAPOL vs. TETRA

Aunque ambos estándares comparten el prefijo "TETRA", responden a filosofías de ingeniería de radiofrecuencia fundamentalmente distintas:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          COMPARATIVA DE ACCESO AL MEDIO                      │
├──────────────────────────────────────┬──────────────────────────────────────┤
│               TETRAPOL               │                TETRA                 │
│      Acceso FDMA (Frecuencia)        │      Acceso TDMA (Tiempo/Slots)      │
│                                      │                                      │
│  Portadora 1 (12.5 kHz) ──► Ch 1     │  Portadora 1 (25 kHz)                │
│  Portadora 2 (12.5 kHz) ──► Ch 2     │  ├─ Slot 1 ──► Ch 1                  │
│  Portadora 3 (12.5 kHz) ──► Ch 3     │  ├─ Slot 2 ──► Ch 2                  │
│                                      │  ├─ Slot 3 ──► Ch 3                  │
│  (1 usuario por canal de 12.5 kHz)   │  └─ Slot 4 ──► Ch 4                  │
│  • Enlace continuo por frecuencia    │  • 4 canales multiplexados en tiempo │
└──────────────────────────────────────┴──────────────────────────────────────┘
```

| Parámetro Técnico | **TETRAPOL** | **TETRA** |
| :--- | :--- | :--- |
| **Organismo / Creador** | TETRAPOL Forum / Matra / Airbus | ETSI |
| **Método de Acceso** | **FDMA** (*Frequency Division Multiple Access*) | **TDMA** (*Time Division Multiple Access* - 4 slots) |
| **Ancho de Canal (Canalización)** | **10 kHz** o **12.5 kHz** (Banda estrecha pura) | **25 kHz** |
| **Esquema de Modulación** | **GMSK** (*Gaussian Minimum Shift Keying*, $BT = 0.25$) | **$\pi/4$-DQPSK** (*Differential Quadrature Phase Shift Keying*) |
| **Tasa de Símbolos / Bits** | $8.0\text{ kbit/s}$ brutos ($8.0\text{ kBd}$) | $36.0\text{ kbit/s}$ ($18.0\text{ kBd}$) |
| **Códec de Voz (Vocoder)** | **RPCELP** ($6.0\text{ kbit/s}$ netos) | **ACELP** ($4.56\text{ kbit/s}$ netos) |
| **Transmisión de RF** | Portadora continua de envolvente constante | Transmisión pulsada por ráfagas (*Burst TDMA*) |
| **Ventaja Operativa** | **Mayor alcance y cobertura geográfica por celda** gracias a la modulación GMSK de envolvente constante y menor ancho de banda de ruido. | Mayor capacidad de usuarios por portadora física en áreas urbanas densas. |

---

## 1.3. Objetivos del Proyecto `tetrapol-kit-2023`

El proyecto `tetrapol-kit` nació originalmente como un esfuerzo de ingeniería inversa e investigación académica para la interceptación, demodulación y análisis de protocolos TETRAPOL mediante **Radio Definida por Software (SDR)**.

La versión modernizada **`tetrapol-kit-2023`** aborda y resuelve las principales limitaciones históricas del ecosistema open-source:
1. **Modernización y compatibilidad:** Adaptación completa a sistemas operativos modernos (Linux x86_64, glibc moderna, GCC 14/15, CMake 3.10+ y Cmocka 2.x).
2. **Implementación del Vocoder RPCELP:** Integración del sintetizador acústico RPCELP para permitir la decodificación de voz a formato de audio estándar PCM 16-bit 8000 Hz (WAV).
3. **Recepción Multicanal Simultánea (*Trunking SDR*):** Capacidad para demodular en paralelo hasta 5 portadoras distintas dentro del ancho de banda de un único receptor RTL-SDR económico.
4. **Análisis Criptográfico y Clasificación Estadística:** Implementación de métricas de entropía de Shannon, balance de bits y distancia de Hamming para discriminar en tiempo real entre voz cifrada, voz en claro y ruido radioeléctrico.
5. **Interfaz Unificada en Tiempo Real:** Monitor interactivo con control de ganancia, alimentación Bias-Tee y despacho de audio en directo.

---

# Capítulo 2: El Estándar TETRAPOL y su Arquitectura de Protocolo

---

## 2.1. Estructura en Capas del Estándar (PAS 0001)

El estándar TETRAPOL sigue el modelo de referencia OSI para comunicaciones digitales inalámbricas:

```
┌────────────────────────────────────────────────────────────┐
│              CAPA DE APLICACIÓN (Voz / Datos)              │
│      Voz Digital RPCELP (6.0 kbps) / Mensajería SDS / AVL   │
├────────────────────────────────────────────────────────────┤
│              CAPA DE RED Y CONTROL (TSDU / TPDU)           │
│     Gestión de Llamadas, Movilidad, Direcciones Z:Y:X      │
├────────────────────────────────────────────────────────────┤
│              CAPA DE ENLACE / MAC (Framing & FEC)          │
│   Estructura de Tramas (20 ms), Scrambler, Códigos BCH     │
├────────────────────────────────────────────────────────────┤
│              CAPA FÍSICA (RF & Modulación)                 │
│      FDMA 12.5 kHz, GMSK (BT=0.25), 8.0 kbit/s en UHF/VHF   │
└────────────────────────────────────────────────────────────┘
```

---

## 2.2. Capa Física y Estructura de Trama Temporal

En TETRAPOL, la transmisión digital se organiza en intervalos temporales fijos de **$20\text{ ms}$** denominados **tramas** (*frames*). A una velocidad de transmisión de $8000\text{ bit/s}$ brutos, cada trama de $20\text{ ms}$ transporta exactamente:

$$\text{Bits por trama} = 8000\text{ bit/s} \times 0.020\text{ s} = 160\text{ bits brutos}$$

Por tanto, el sistema transmite exactamente **50 tramas por segundo**.

```
             ESTRUCTURA DE UNA TRAMA FÍSICA TETRAPOL (160 BITS / 20 MS)
┌───────────────────────────────────────────────┬──────────────────────────────┐
│        CARGA ÚTIL PROTEGIDA (120 BITS)        │  PARIDAD FEC BCH (40 BITS)   │
│   Voz RPCELP o Datos de Control (15 bytes)    │   Corrección hasta 5 errores │
└───────────────────────────────────────────────┴──────────────────────────────┘
```

---

## 2.3. Codificación de Canal y Corrección de Errores (BCH)

Las señales de radio en entornos móviles sufren atenuaciones severas, multitrayecto y ruido Gaussiano. Para garantizar la integridad de la señalización y de la voz, TETRAPOL emplea códigos de bloques lineales **BCH (*Bose-Chaudhuri-Hocquenghem*)**:

1. **Código BCH $(160, 120, t=5)$**:
   - Se aplica en tramas de tráfico de voz y datos generales.
   - Toma $k = 120\text{ bits}$ de información útil y añade $n - k = 40\text{ bits}$ de paridad y redundancia.
   - Tiene una capacidad de corrección de hasta **$t = 5\text{ bits}$ erróneos por trama**.
2. **Código BCH $(120, 72, t=5)$**:
   - Utilizado en ciertos canales de señalización crítica reducida.
3. **Mecanismo de Detección y Síndromes**:
   - En recepción, `tetrapol_dump` calcula el vector de síndromes $S = (S_1, S_2, \dots, S_{2t})$ multiplicando la trama recibida por la matriz de paridad $H$.
   - Si $S = 0$, la trama no contiene errores (`state: "ok", syndromes: 0`).
   - Si $S \neq 0$, el algoritmo de Berlekamp-Massey / Chien localiza la posición de los errores y corrige hasta 5 bits (`bits_fixed: 1..5`). Si el número de errores supera 5, la trama se declara irrecuperable (`state: "error"`).

---

## 2.4. Canales Lógicos: CCH frente a TCH

TETRAPOL clasifica los canales de radio en dos grandes categorías operativas:

### A. Canal de Control (**CCH** - *Control Channel*)
Es la portadora permanente que gestiona la celda. Transmite continuamente y aloja varios canales lógicos multiplexados:
- **BCH (*Broadcast Channel*)**: Emite la identidad de la estación base (BS ID), el código de red (MNC) y la lista de frecuencias vecinas para *handover*.
- **PCH (*Paging Channel*)**: Envía avisos de llamada entrante a terminales específicos.
- **RACH (*Random Access Channel*)**: Canal de subida (*uplink*) donde los terminales solicitan acceso mediante ALOHA ranurado.
- **SDCH (*Slow Dedicated Control Channel*)**: Canal de señalización dedicado para negociación de llamada.
- **DACH (*Data Access Channel*)**: Transmisión de paquetes de datos y mensajería corta.

### B. Canal de Tráfico (**TCH** - *Traffic Channel*)
Es la frecuencia asignada dinámicamente por la red cuando dos o más terminales establecen una comunicación:
- **VOICE**: Transporta las tramas de voz digital RPCELP de 120 bits cada 20 ms.
- **LSDU-VCH (*Low Speed Data Unit - Voice Channel*)**: Señalización en banda insertada en la conversación (robando tramas o mediante bits asociados `asb`).

---

## 2.5. Jerarquía de Direccionamiento y Códigos de Color (SCR)

### 1. Direccionamiento $Z:Y:X$
Toda entidad en la red TETRAPOL se identifica mediante una tupla jerárquica de 3 niveles:
- **Zona ($Z$)**: Identifica la región geográfica o subsistema de conmutación ($0 \dots 63$).
- **Subred / Flota ($Y$)**: Identifica la organización o cuerpo policial específico ($0 \dots 7$).
- **Identificador de Terminal / Grupo ($X$)**:
  - $X = 0 \dots 4094$: Identificador individual de terminal (ISSI) o de grupo de conversación (*Talkgroup* / GSSI).
  - $X = 4095$ (`0xFFF`): **Dirección Broadcast general** (usada en mensajes de reposo e información común).

### 2. Código de Color / Scrambler ($SCR$)
Para evitar interferencias co-canal entre celdas repetidoras geográficamente cercanas que reutilizan la misma frecuencia, TETRAPOL aplica una máscara pseudoaleatoria (*Scrambler Code*, $SCR \in [0, 127]$). Los terminales solo procesan tramas cuyo código de color coincida con la celda a la que están sincronizados.

---

## 2.6. Tramas Especiales de Mantenimiento y Retención

1. **Patrón de Reposo (`5812` / `0x7FFF`)**:
   - Cuando no hay tráfico de voz, la estación base no interrumpe la emisión; transmite tramas `DATA` con el código hexadecimal `5812` hacia la dirección broadcast `Z:0 Y:7 X:4095`.
   - Esto mantiene sincronizados los bucles de enganche de fase (PLL) y el control de frecuencia (AFC) de todos los terminales a la escucha.
2. **Tiempo de Retención (*Hang Time* `5889`)**:
   - Al finalizar una transmisión de voz (cuando el locutor suelta el PTT), la red mantiene el canal de tráfico abierto durante unos segundos emitiendo el código `5889`.
   - Esto permite que otro interlocutor del mismo grupo responda de forma instantánea sin necesidad de realizar una nueva negociación completa de canal en el CCH.

---

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

---

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

---

# Capítulo 5: Cifrado, Criptografía y Análisis Estadístico de Tráfico

---

## 5.1. Arquitectura de Seguridad TETRAPOL (PAS 0001-16)

La seguridad en TETRAPOL está diseñada para proteger la confidencialidad, autenticidad e integridad de las comunicaciones de misión crítica. Se basa en un esquema de **cifrado de flujo síncrono (*Synchronous Stream Cipher*)** a nivel de capa de enlace.

### A. Jerarquía de Claves
El sistema utiliza una estructura de claves estratificada:
1. **TMK (*Terminal Master Key*)**: Clave de 128 bits grabada en el módulo de seguridad del terminal (chip criptográfico) para autenticación mutua terminal-red.
2. **TKK (*Terminal Key of Keys*)**: Clave maestra para descifrar otras claves de sesión distribuidas por el aire (**OTAR - *Over-The-Air Rekeying***).
3. **DMK (*Direct Mode Key*)**: Clave compartida para comunicaciones directas walkie-a-walkie fuera de cobertura de repetidor (*Direct Mode Operation - DMO*).
4. **PK (*Personalisation Key*)**: Clave de grupo o flota para cifrado de canales de tráfico.

---

## 5.2. Mecánica del Cifrado de Flujo y Keystream Dinámico

El cifrado no opera bloque a bloque como AES-ECB, sino que genera una secuencia pseudoaleatoria continua (**Keystream**) mediante un generador criptográfico hardware (PRNG):

$$\text{Cifrado:} \quad C_i = P_i \oplus S_i(K, \text{FN}_i)$$
$$\text{Descifrado:} \quad P_i = C_i \oplus S_i(K, \text{FN}_i)$$

Donde:
- $P_i$: Trama de voz o datos en claro de 120 bits en el instante $i$.
- $C_i$: Trama cifrada transmitida por el aire.
- $K$: Clave de sesión secreta de 128 bits.
- $\text{FN}_i$: Número de Trama (*Frame Number* / Contador de sincronismo), que avanza estrictamente en cada intervalo de $20\text{ ms}$.
- $S_i$: Bloque de 120 bits de **Keystream** pseudoaleatorio generado para esa trama exacta.

```
                              GENERACIÓN DE KEYSTREAM POR TRAMA
┌─────────────────────────────────┐      ┌─────────────────────────────────┐
│ Clave Secreta K (128 bits)      │      │ Número de Trama FN_i (Contador) │
└────────────────┬────────────────┘      └────────────────┬────────────────┘
                 │                                        │
                 └───────────────────┬────────────────────┘
                                     │
                                     ▼
                    ┌─────────────────────────────────┐
                    │  Generador Criptográfico PRNG   │
                    └────────────────┬────────────────┘
                                     │
                                     ▼
                     Keystream S_i (120 bits únicos cada 20 ms)
                                     │
                 ┌───────────────────┴───────────────────┐
                 │                                       │
                 ▼                                       ▼
    Cifrado en Transmisión:                 Descifrado en Recepción:
    C_i = P_i ⊕ S_i                         P_i = C_i ⊕ S_i
```

> **Propiedad fundamental:** Aunque la clave $K$ permanezca constante durante una llamada de varios minutos, **el Keystream $S_i$ cambia completamente cada 20 milisegundos**. Esto impide ataques de repetición o análisis de frecuencias sencillos.
>
> **Canales en Claro (EMOCH):** En canales de emergencia multisede (**EMOCH**), la red conmuta el generador a modo transparente ($S_i = 0$), permitiendo que cualquier receptor decodifique el audio directamente sin clave.

---

## 5.3. Análisis Estadístico y Clasificador Multicriterio

Dado que un receptor SDR capta tanto tráfico cifrado como no cifrado e interferencias, `live_monitor.py` incorpora un **motor de clasificación estadística multicriterio** basado en tres propiedades físico-matemáticas:

```
                            CLASIFICADOR MULTICRITERIO
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │               Ráfaga de Voz Recibida (Array de tramas de 120 bits)          │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
             ┌──────────────────────────┼──────────────────────────┐
             ▼                          ▼                          ▼
  1. Entropía Normalizada     2. Distancia Hamming        3. Balance de Bits
   H_norm = H(X) / log2(N)     d_H(F_i, F_{i+1})          Ratio de 1s (Bernoulli)
             │                          │                          │
             └──────────────────────────┼──────────────────────────┘
                                        │
                                        ▼
    ┌───────────────────────────────────────────────────────────────────────┐
    │                               DECISIÓN                                │
    ├───────────────────────────────────────────────────────────────────────┤
    │ • Si H_norm ≥ 0.83, d_H ≈ 60 bits, Ratio 1s ≈ 50% ──► [🔒 CIFRADA]    │
    │ • Si 0.65 ≤ H_norm ≤ 0.82, 18 ≤ d_H ≤ 48 bits     ──► [🔊 EN CLARO]   │
    │ • Si d_H < 18 bits o H_norm < 0.65                ──► [⚪ RUIDO/REPOSO]│
    └───────────────────────────────────────────────────────────────────────┘
```

### 1. Entropía de Shannon Normalizada ($H_{\text{norm}}$)
La entropía de Shannon mide la incertidumbre o aleatoriedad de la distribución de bytes:

$$H(X) = -\sum_{i=1}^{n} p(x_i) \log_2 p(x_i)$$

- **La trampa del tamaño de muestra:** Para una ráfaga corta de $N$ bytes (ej. 11 tramas = 165 bytes), el número máximo de valores distintos no puede superar $N$, por lo que la entropía máxima alcanzable es $\log_2(165) = 7.366\text{ bits/byte}$ en lugar de 8.0.
- **Normalización implementada:**
  $$H_{\text{norm}} = \frac{H(X)}{\log_2(\min(N, 256))}$$
  - Cifrado de flujo (Keystream): $H_{\text{norm}} \ge 0.83$ ($83\% - 99\%$ de la máxima aleatoriedad teórica).
  - Voz en claro RPCELP: $H_{\text{norm}} \le 0.78$ (Estructura fonética con redundancia natural).

### 2. Distancia de Hamming Inter-Trama ($d_H$)
Calcula el número de bits que difieren entre dos tramas de 120 bits consecutivas:

$$d_H(F_i, F_{i+1}) = \sum_{k=0}^{119} \left( F_i[k] \oplus F_{i+1}[k] \right)$$

- **En tráfico cifrado:** Como cada trama se enmascara con un Keystream no correlacionado, la probabilidad de cambio de cada bit es $p = 0.5$. La distancia esperada sigue una distribución binomial con media:
  $$\mathbb{E}[d_H] = 120 \times 0.5 = 60\text{ bits}$$
- **En voz en claro:** Como la posición de la boca y las cuerdas vocales no cambian instantáneamente en 20 ms, los coeficientes LAR y LTP evolucionan de forma suave y continua:
  $$d_H \in [18, 48]\text{ bits}$$
- **En ruido de sincronismo o tramas de reposo repetidas:**
  $$d_H < 18\text{ bits}$$

### 3. Balance de Bits (Test de Bernoulli)
Comprueba el porcentaje de bits `1` frente a `0` en la ráfaga:
- En un cifrado seguro, la secuencia de salida es indistinguible de una serie de ensayos de Bernoulli equiprobables ($p = 0.5$):
  $$\text{Ratio de 1s} \in [0.46, 0.54]$$
- En voz en claro o tramas corruptas, el ratio se desvía sistemáticamente de 0.5.

---

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

---

# Capítulo 7: Glosario Exhaustivo de Conceptos y Tecnicismos

Este glosario define y explica los términos fundamentales de radiofrecuencia, procesamiento digital de señales, telecomunicaciones y criptografía presentes en TETRAPOL y en este proyecto. Cada término incluye su definición técnica formal y una explicación sencilla y pedagógica (*"en cristiano"*).

---

## 1. Radiofrecuencia y Radio Definida por Software (SDR)

### • SDR (*Software Defined Radio* - Radio Definida por Software)
- **Definición Formal:** Sistema de radiocomunicación donde componentes tradicionalmente implementados en hardware físico (mezcladores, filtros, demoduladores y detectores) se ejecutan mediante software sobre un procesador o DSP.
- **En lenguaje sencillo:** En lugar de comprar una radio antigua con ruedas y circuitos para cada tipo de modulación, usas un pincho USB (como el RTL-SDR) que envía los datos de la antena al ordenador, y un programa de ordenador hace de radio.

### • Muestras I/Q (*In-Phase / Quadrature*)
- **Definición Formal:** Representación matemática en dos dimensiones de una señal compleja de radiofrecuencia en banda base, donde $I(t)$ es la componente en fase y $Q(t)$ es la componente en cuadratura desfasada $90^\circ$.
- **En lenguaje sencillo:** Son dos números $(X, Y)$ que el receptor mide millones de veces por segundo para saber con total exactitud tanto la fuerza (amplitud) como el giro (fase) de la onda de radio en cada instante.

### • Ancho de Banda (*Bandwidth* - BW)
- **Definición Formal:** Rango de frecuencias que ocupa una señal o que un receptor puede digitalizar simultáneamente, medido en Hertzios (Hz).
- **En lenguaje sencillo:** El "ancho de la carretera". Cuanto más ancho de banda capture el SDR, más canales de radio adyacentes caben dentro para escucharlos a la vez.

### • DDC (*Digital Down-Converter* - Conversor Digital Descendente)
- **Definición Formal:** Algoritmo DSP que traslada digitalmente una banda de frecuencia de interés hacia la frecuencia cero (banda base) y reduce la tasa de muestreo mediante diezmado y filtrado paso bajo.
- **En lenguaje sencillo:** Una lupa matemática que recorta de la captura total de 2 MHz solo los 12.5 kHz del canal que queremos escuchar.

### • Bias-Tee
- **Definición Formal:** Circuito pasivo diplexor que permite inyectar corriente continua (DC) a través de un cable coaxial de RF para alimentar dispositivos activos remotos (como amplificadores LNA) sin interferir en la señal de radio.
- **En lenguaje sencillo:** Enviar electricidad (4.5V) por el mismo cable de la antena para darle energía a un amplificador colocado arriba en el tejado.

### • LNA (*Low-Noise Amplifier* - Amplificador de Bajo Ruido)
- **Definición Formal:** Amplificador electrónico situado lo más cerca posible de la antena receptora para elevar la potencia de señales extremadamente débiles antes de que se degraden en el cable.
- **En lenguaje sencillo:** Un "micrófono de alta sensibilidad" para la antena que amplifica la señal lejana sin meterle ruido.

---

## 2. Modulaciones y Protocolo de Radio

### • GMSK (*Gaussian Minimum Shift Keying*)
- **Definición Formal:** Esquema de modulación digital por desplazamiento de frecuencia de fase continua (CPFSK), donde los pulsos de datos rectangulares son conformados por un filtro paso bajo Gaussiano con $BT=0.25$ antes de la modulación en frecuencia.
- **En lenguaje sencillo:** Una forma muy suave de transmitir ceros y unos variando la frecuencia de la onda sin dar saltos bruscos. Tiene la ventaja de que la potencia siempre es constante, gastando menos batería en los walkies y llegando más lejos.

### • FDMA (*Frequency Division Multiple Access*)
- **Definición Formal:** Técnica de multiplexación en la que el espectro disponible se subdivide en canales de frecuencia discretos e independientes asignados a cada usuario.
- **En lenguaje sencillo:** Cada llamada tiene su propia "carretera" (frecuencia de 12.5 kHz) exclusiva mientras dura la conversación.

### • Canal Troncalizado (*Trunking*)
- **Definición Formal:** Sistema dinámico donde un conjunto compartido de frecuencias de radio es asignado automáticamente por un canal de control central a los usuarios según la demanda.
- **En lenguaje sencillo:** Como la fila única del banco: cuando un usuario pulsa el PTT para hablar, la central le asigna al instante la primera frecuencia libre disponible.

### • Canal de Control (CCH) y Canal de Tráfico (TCH)
- **Definición Formal:** El CCH es la portadora permanente que transmite información del sistema y gestiona las llamadas; el TCH es la portadora temporal asignada para la transmisión de la voz.
- **En lenguaje sencillo:** El CCH es la "torre de control" del aeropuerto y el TCH es la "pista de aterrizaje" por donde viaja la voz de los aviones.

### • Código de Color / Scrambler (SCR)
- **Definición Formal:** Identificador numérico ($0 \dots 127$) aplicado a las tramas de una estación base para permitir la reutilización de frecuencias en celdas cercanas sin que interfieran entre sí.
- **En lenguaje sencillo:** El "DNI" de la antena repetidora para que el walkie sepa a qué torre pertenece la señal que está recibiendo.

---

## 3. Corrección de Errores y Criptografía

### • Código BCH (*Bose-Chaudhuri-Hocquenghem*)
- **Definición Formal:** Clase de códigos algebraicos de bloques lineales para corrección de errores hacia adelante (FEC) capaces de corregir múltiples errores aleatorios por bloque.
- **En lenguaje sencillo:** Añadir números de control a la frase enviada de modo que, si el viento o las interferencias corrompen hasta 5 bits por el camino, el receptor pueda reconstruir los bits originales matemáticamente sin tener que pedir que se repita la frase.

### • Cifrado de Flujo (*Stream Cipher*)
- **Definición Formal:** Algoritmo criptográfico simétrico que combina bit a bit (o byte a byte) el texto en claro con una secuencia pseudoaleatoria continua (**Keystream**) mediante la operación lógica XOR ($\oplus$).
- **En lenguaje sencillo:** Como poner una máscara transparente con un patrón de ruido único sobre el texto. Solo quien tenga la misma máscara exacta puede quitar el ruido y leer el texto.

### • Keystream (Flujo de Clave)
- **Definición Formal:** Secuencia pseudoaleatoria de bits generada por un generador determinista (PRNG) a partir de una clave secreta y un vector de inicialización / contador de trama.
- **En lenguaje sencillo:** La "máscara de ruido" que cambia cada 20 milisegundos para que cada trozo de audio esté protegido de forma diferente.

### • Entropía de Shannon
- **Definición Formal:** Medida cuantitativa del grado de incertidumbre, desorden o contenido de información promedio producido por una fuente de datos, medida en bits por símbolo.
- **En lenguaje sencillo:** Un termómetro de aleatoriedad. Si los datos están cifrados, parecen ruido de televisión perfecto (entropía máxima cercana a 8 bits/byte). Si es voz humana normal, hay patrones repetitivos y la entropía es mucho más baja.

### • Distancia de Hamming
- **Definición Formal:** Número de posiciones en las que los bits de dos vectores binarios de igual longitud son diferentes.
- **En lenguaje sencillo:** Contar cuántas letras cambian entre dos palabras de igual longitud.

---

## 4. Procesamiento de Voz y Vocoders

### • Vocoder (*Voice Coder*)
- **Definición Formal:** Codificador/decodificador paramétrico de voz diseñado para sintetizar el habla humana a tasas de bits extremadamente bajas mediante el modelado del tracto vocal y la excitación acústica.
- **En lenguaje sencillo:** En vez de grabar la onda de audio real (que ocuparía mucho espacio), analiza cómo está colocada la boca y las cuerdas vocales, envía solo esos "parámetros de la boca" (120 bits), y al otro lado un sintetizador recrea la voz.

### • LPC (*Linear Predictive Coding* - Codificación Predictiva Lineal)
- **Definición Formal:** Modelo de procesamiento de voz que asume que cada muestra de sonido se puede predecir como una combinación lineal de las muestras anteriores filtradas por un modelo del tracto vocal.
- **En lenguaje sencillo:** La fórmula matemática que imita la forma de la boca y la garganta humana.

### • Coeficientes LAR (*Log Area Ratios*)
- **Definición Formal:** Representación matemática de los coeficientes de reflexión acústica del tracto vocal transformados logarítmicamente para optimizar su cuantificación y estabilidad ante errores de canal.
- **En lenguaje sencillo:** Los números que indican si la garganta y la lengua están abiertas o cerradas en cada instante.

### • LTP (*Long Term Predictor* - Predicción a Largo Plazo / Pitch)
- **Definición Formal:** Parámetro del vocoder que mide el retardo (*lag*) y la ganancia correspondiente a la frecuencia fundamental de vibración de las cuerdas vocales humanas.
- **En lenguaje sencillo:** El tono de la voz: si la persona que habla es un hombre con voz grave o una mujer con voz aguda.

---

