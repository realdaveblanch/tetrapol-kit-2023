#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <getopt.h>
#include <math.h>
#include <tetrapol/rpcelp.h>

#define SAMPLE_RATE 8000
#define SAMPLES_PER_FRAME 160
#define VOICE_BYTES 15

#pragma pack(push, 1)
typedef struct {
    char riff[4];
    uint32_t overall_size;
    char wave[4];
    char fmt_chunk_marker[4];
    uint32_t length_of_fmt;
    uint16_t format_type;
    uint16_t channels;
    uint32_t sample_rate;
    uint32_t byterate;
    uint16_t block_align;
    uint16_t bits_per_sample;
    char data_chunk_header[4];
    uint32_t data_size;
} wav_header_t;
#pragma pack(pop)

static void write_wav_header(FILE *f, uint32_t total_samples) {
    wav_header_t header;
    memcpy(header.riff, "RIFF", 4);
    header.overall_size = sizeof(wav_header_t) - 8 + (total_samples * 2);
    memcpy(header.wave, "WAVE", 4);
    memcpy(header.fmt_chunk_marker, "fmt ", 4);
    header.length_of_fmt = 16;
    header.format_type = 1; // PCM
    header.channels = 1;    // Mono
    header.sample_rate = SAMPLE_RATE;
    header.byterate = SAMPLE_RATE * 2;
    header.block_align = 2;
    header.bits_per_sample = 16;
    memcpy(header.data_chunk_header, "data", 4);
    header.data_size = total_samples * 2;

    fseek(f, 0, SEEK_SET);
    fwrite(&header, sizeof(wav_header_t), 1, f);
}

static int hex2byte(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

static int parse_hex(uint8_t *out, const char *hex, int max_len) {
    int len = 0;
    int h_len = strlen(hex);
    for (int i = 0; i < h_len && len < max_len; i += 2) {
        int hi = hex2byte(hex[i]);
        if (hi < 0) break;
        int lo = (i + 1 < h_len) ? hex2byte(hex[i + 1]) : 0;
        if (lo < 0) break;
        out[len++] = (hi << 4) | lo;
    }
    return len;
}

static void print_help(const char *prog) {
    fprintf(stderr, "TETRAPOL RPCELP Vocoder / WAV Audio Decoder\n");
    fprintf(stderr, "Uso: %s [OPCIONES]\n", prog);
    fprintf(stderr, "  -i <input.json>    Archivo JSON con tramas decodificadas de tetrapol_dump\n");
    fprintf(stderr, "  -o <output.wav>    Archivo WAV de salida (PCM 16-bit 8000Hz mono)\n");
    fprintf(stderr, "  -k <hex_key>       Clave/máscara XOR hexadecimal para descifrado de tramas de voz\n");
    fprintf(stderr, "  -h                 Muestra esta ayuda\n");
}

int main(int argc, char *argv[]) {
    const char *input_path = NULL;
    const char *output_path = "output.wav";
    const char *key_hex = NULL;
    uint8_t key_bytes[VOICE_BYTES];
    int key_len = 0;

    int opt;
    while ((opt = getopt(argc, argv, "i:o:k:h")) != -1) {
        switch (opt) {
            case 'i':
                input_path = optarg;
                break;
            case 'o':
                output_path = optarg;
                break;
            case 'k':
                key_hex = optarg;
                key_len = parse_hex(key_bytes, key_hex, VOICE_BYTES);
                break;
            case 'h':
            default:
                print_help(argv[0]);
                return (opt == 'h') ? 0 : 1;
        }
    }

    if (!input_path) {
        fprintf(stderr, "Error: Debe especificar un archivo de entrada con -i <archivo.json>\n");
        print_help(argv[0]);
        return 1;
    }

    FILE *fin = fopen(input_path, "r");
    if (!fin) {
        perror("Error al abrir archivo de entrada");
        return 1;
    }

    FILE *fout = fopen(output_path, "wb");
    if (!fout) {
        perror("Error al abrir archivo de salida WAV");
        fclose(fin);
        return 1;
    }

    // Escribir cabecera WAV temporal (se actualizará al final con el total de muestras)
    write_wav_header(fout, 0);

    rpcelp dec;
    rpcelp_decode_init(&dec);

    char line[4096];
    uint32_t total_frames = 0;
    uint32_t total_samples = 0;

    while (fgets(line, sizeof(line), fin)) {
        if (strstr(line, "\"type\": \"VOICE\"") || strstr(line, "\"type\":\"VOICE\"")) {
            char *p = strstr(line, "\"value\"");
            if (!p) continue;
            char *colon = strchr(p, ':');
            if (!colon) continue;
            char *q1 = strchr(colon, '\"');
            if (!q1) continue;
            char *start = q1 + 1;
            char *q2 = strchr(start, '\"');
            if (!q2 || (q2 - start) < 30) continue;

            char hex_val[32] = {0};
            memcpy(hex_val, start, 30);
            hex_val[30] = '\0';

            uint8_t voice_raw[VOICE_BYTES] = {0};
            int vlen = parse_hex(voice_raw, hex_val, VOICE_BYTES);
            if (vlen < VOICE_BYTES) continue;

            // Si se suministró clave XOR de descifrado, aplicarla
            if (key_len > 0) {
                for (int i = 0; i < VOICE_BYTES; i++) {
                    voice_raw[i] ^= key_bytes[i % key_len];
                }
            }

            // Decodificar los 160 samples (20 ms) con RPCELP
            const double *samples = rpcelp_decode_frame(&dec, voice_raw);

            int16_t pcm16[SAMPLES_PER_FRAME];
            for (int s = 0; s < SAMPLES_PER_FRAME; s++) {
                double val = samples[s] * 32767.0;
                // Escalar y limitar a rango int16 [-32767, 32767]
                if (val > 32767.0) val = 32767.0;
                if (val < -32768.0) val = -32768.0;
                pcm16[s] = (int16_t)val;
            }

            fwrite(pcm16, sizeof(int16_t), SAMPLES_PER_FRAME, fout);
            total_samples += SAMPLES_PER_FRAME;
            total_frames++;
        }
    }

    // Actualizar cabecera con el tamaño total final
    write_wav_header(fout, total_samples);

    fclose(fin);
    fclose(fout);

    fprintf(stderr, "=== Conversión finalizada ===\n");
    fprintf(stderr, "Tramas de voz procesadas: %u (%.2f segundos de audio)\n",
            total_frames, (double)total_samples / SAMPLE_RATE);
    fprintf(stderr, "Archivo WAV generado: %s (8000 Hz, 16-bit PCM Mono)\n", output_path);
    if (key_len > 0) {
        fprintf(stderr, "Clave XOR aplicada: %s\n", key_hex);
    }

    return 0;
}
