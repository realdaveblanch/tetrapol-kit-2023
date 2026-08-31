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
