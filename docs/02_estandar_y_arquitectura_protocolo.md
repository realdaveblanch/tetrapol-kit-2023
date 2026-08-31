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
