#ifndef RPCELP_DECODE_H
#define RPCELP_DECODE_H

#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <math.h>
#include <assert.h>
#include <stdio.h>

#define MAX_VALS 50
#define MAX_LAR 10
#define MAX_LTP 3
#define MAX_BITS 120

typedef struct {
    char name[20];
    int vb[20];
    int len;
} val_t;

typedef struct {
    double t[MAX_LAR];
    int size;
} lar_t;

typedef struct {
    int ilag;
    int igain;
    int dec;
    int iexgain;
    int iph;
    int N;
} ltp_t;

typedef struct {
    bool v[MAX_BITS];
} vfr_t;

typedef struct {
    double tab[160 * 3];
    double tab2[160 * 3];
    double old[MAX_LAR];
    double v[11];
    double ffb;
} rpcelp;

// Constantes globales
extern const double QBL[8];
extern const double sto_gain[32];
extern const double ls[10][2];

// Fonctions
void sat(double *x, double M);
double declar(int u, int i, int nb);
lar_t lar2refl(const lar_t *lar, int ex);
lar_t lar_mul(double x, const lar_t *a);
lar_t lar_add(const lar_t *b, const lar_t *a);
void lar_init(lar_t *lar);
void ltp_init(ltp_t *ltp, int N);
int ltp_vp(const ltp_t *ltp);
int ltp_Q(const ltp_t *ltp);
int ltp_D(const ltp_t *ltp);
int ltp_ph(const ltp_t *ltp);
int ltp_sigs(const ltp_t *ltp);
double ltp_gain(const ltp_t *ltp);
double ltp_exgain(const ltp_t *ltp);

void rpcelp_decode_init(rpcelp *dec);
const double *rpcelp_decode_frame(rpcelp *dec, const unsigned char *bf);
void rpcelp_decode_clear(rpcelp *dec);
lar_t rpcelp_correctlar(const lar_t *lar, double x);

#endif