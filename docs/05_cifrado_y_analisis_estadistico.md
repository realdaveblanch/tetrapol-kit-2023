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
