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
