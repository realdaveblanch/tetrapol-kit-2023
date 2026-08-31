#include <tetrapol/rpcelp.h>
#include <stdlib.h>

// Constantes
const double QBL[8] = {0.3, 0.45, 0.60, 0.74, 0.86, 0.98, 1.14, 1.23};
const double sto_gain[32] = {0, 5, 11, 19, 27, 35, 43, 51, 59, 71, 87, 103, 119, 143, 175, 207, 239, 287, 351, 415, 479, 575, 703, 831, 959, 1151, 1407, 1663, 1919, 2303, 2815, 3583};
const double ls[10][2] = {
    {-1.625, 0.38465041},
    {-0.7255134, 1.625},
    {-1.3538182, 0.62888535},
    {-0.4090979, 1.36354402},
    {-0.7099015, 0.57737373},
    {-0.4737691, 0.82117651},
    {-0.8141674, 0.47146487},
    {-0.5001262, 0.71935197},
    {-0.7204825, 0.47273149},
    {-0.3206912, 0.55081164}
};

double ffdec = 1.0;

// --- Fonctions utilitaires ---
void sat(double *x, double M) {
    if (*x > M) *x = M;
    if (*x < -M) *x = -M;
}

double declar(int u, int i, int nb) {
    assert(i >= 0 && i < 10);
    assert(u >= 0);
    if (u >= (1 << nb))
        printf("error %d >= 2^%d\n", i, nb);
    return ffdec * ls[i][0] + (ffdec * ls[i][1] - ffdec * ls[i][0]) * u / ((1 << nb) - 1);
}

double refl2lar_approx(double x) {
    double a = fabs(x);
    double r;
    if (a < 0.675) r = a;
    else if (a < 0.95) r = 2 * a - 0.675;
    else r = 8 * a - 6.375;
    return (x < 0) ? -r : r;
}

double lar2refl_approx(double lar) {
    double a = fabs(lar);
    double r;
    if (a < 0.675) r = a;
    else if (a < 1.225) r = 0.5 * a + 0.3375;
    else r = 0.125 * a + 0.796875;
    return (lar < 0) ? -r : r;
}

double lar2refl_eval(double lars) {
    lars = pow(10., lars);
    return (lars - 1) / (lars + 1);
}

void lar_init(lar_t *lar) {
    for (int i = 0; i < MAX_LAR; i++)
        lar->t[i] = 0;
    lar->size = 0;
}

lar_t lar2refl(const lar_t *lar, int ex) {
    lar_t r;
    for (int i = 0; i < lar->size; i++) {
        if (ex) r.t[i] = lar2refl_eval(lar->t[i]);
        else r.t[i] = lar2refl_approx(lar->t[i]);
    }
    r.size = lar->size;
    return r;
}

lar_t lar_mul(double x, const lar_t *a) {
    lar_t r;
    for (int i = 0; i < a->size; i++)
        r.t[i] = a->t[i] * x;
    r.size = a->size;
    return r;
}

lar_t lar_add(const lar_t *b, const lar_t *a) {
    lar_t r;
    for (int i = 0; i < a->size; i++)
        r.t[i] = a->t[i] + b->t[i];
    r.size = a->size;
    return r;
}

void ltp_init(ltp_t *ltp, int N) {
    ltp->N = N;
    ltp->ilag = 0;
    ltp->igain = 0;
    ltp->dec = 0;
    ltp->iexgain = 0;
    ltp->iph = 0;
}

int ltp_vp(const ltp_t *ltp) {
    int t[4] = {3, 4, 4, 6};
    return t[ltp->dec];
}

int ltp_Q(const ltp_t *ltp) {
    if (ltp->dec == 0) return ltp->N == 48 ? 6 : 7;
    int t[4] = {7, 4, 3, 1};
    return t[ltp->dec];
}

int ltp_D(const ltp_t *ltp) {
    int t[4] = {8, 12, 15, 56};
    return t[ltp->dec];
}

int ltp_ph(const ltp_t *ltp) {
    int n = (ltp->N == 48) ? 9 : 10;
    return (ltp->iph >> (n - ltp_vp(ltp))) & ((1 << ltp_vp(ltp)) - 1);
}

int ltp_sigs(const ltp_t *ltp) {
    int n = (ltp->N == 48) ? 9 : 10;
    return ltp->iph & ((1 << (n - ltp_vp(ltp))) - 1);
}

double ltp_gain(const ltp_t *ltp) {
    return (ltp->ilag == 255) ? 0 : QBL[ltp->igain];
}

double ltp_exgain(const ltp_t *ltp) {
    return sto_gain[ltp->iexgain] / 100000.;
}

// --- Initialisation des valeurs statiques ---
static val_t vals[MAX_VALS];
static val_t *valslars[MAX_LAR];
static val_t *valsltp[MAX_LTP][2];
static val_t *valsex[MAX_LTP][3];

static const char *bits_raw[] = {
    "LAR01", "1", "0", "23", "22", "21",
    "LAR02", "2", "27", "26", "25", "24",
    "LAR03", "3", "30", "29", "28",
    "LAR04", "4", "31", "33", "32",
    "LAR05", "5", "36", "35", "34",
    "LAR06", "39", "38", "37",
    "LAR07", "42", "41", "40",
    "LAR08", "45", "44", "43",
    "LAR09", "47", "46", "48",
    "LAR10", "51", "50", "49",
    "LTP_lag1", "6", "58", "57", "56", "55", "54", "53", "52",
    "LTP_gain1", "7", "60", "59",
    "E_gain1", "8", "63", "62", "61", "64",
    "E_dec1", "10", "9",
    "E_sph1", "74", "73", "72", "71", "70", "69", "68", "67", "66", "65",
    "LTP_lag2", "11", "79", "78", "77", "76", "75", "81", "80",
    "LTP_gain2", "12", "83", "82",
    "E_gain2", "13", "87", "86", "85", "84",
    "E_dec2", "15", "14",
    "E_sph2", "95", "94", "93", "92", "91", "90", "89", "88", "96",
    "LTP_lag3", "16", "103", "102", "101", "100", "99", "98", "97",
    "LTP_gain3", "17", "105", "104",
    "E_gain3", "18", "109", "108", "107", "106",
    "E_dec3", "20", "19",
    "E_sph3", "111", "110", "119", "118", "117", "116", "115", "114", "113", "112",
    NULL
};

static val_t *val_search(const char *a) {
    for (int i = 0; i < MAX_VALS; i++)
        if (vals[i].name[0] && strcmp(vals[i].name, a) == 0)
            return &vals[i];
    assert(0);
    return NULL;
}

static void init() {
    memset(vals, 0, sizeof(vals));
    int val_idx = 0;
    const char *rr = "";
    for (int i = 0; bits_raw[i]; i++) {
        if (bits_raw[i][0] >= '0' && bits_raw[i][0] <= '9') {
            int u = atoi(bits_raw[i]);
            for (int j = 0; j < MAX_VALS; j++)
                if (vals[j].name[0] && strcmp(vals[j].name, rr) == 0) {
                    vals[j].vb[vals[j].len++] = u;
                    break;
                }
        } else {
            rr = bits_raw[i];
            strncpy(vals[val_idx].name, rr, 19);
            vals[val_idx].len = 0;
            val_idx++;
        }
    }

    for (int i = 0; i < MAX_LAR; i++) {
        char bf[20];
        snprintf(bf, 19, "LAR%02d", i + 1);
        valslars[i] = val_search(bf);
    }

    valsltp[0][0] = val_search("LTP_lag1");
    valsltp[0][1] = val_search("LTP_gain1");
    valsltp[1][0] = val_search("LTP_lag2");
    valsltp[1][1] = val_search("LTP_gain2");
    valsltp[2][0] = val_search("LTP_lag3");
    valsltp[2][1] = val_search("LTP_gain3");

    valsex[0][0] = val_search("E_dec1");
    valsex[0][1] = val_search("E_gain1");
    valsex[0][2] = val_search("E_sph1");
    valsex[1][0] = val_search("E_dec2");
    valsex[1][1] = val_search("E_gain2");
    valsex[1][2] = val_search("E_sph2");
    valsex[2][0] = val_search("E_dec3");
    valsex[2][1] = val_search("E_gain3");
    valsex[2][2] = val_search("E_sph3");
}

// --- Décodage ---
void rpcelp_decode_init(rpcelp *dec) {
    memset(dec->tab, 0, sizeof(dec->tab));
    memset(dec->tab2, 0, sizeof(dec->tab2));
    memset(dec->old, 0, sizeof(dec->old));
    memset(dec->v, 0, sizeof(dec->v));
    dec->ffb = 1.05;
}

lar_t rpcelp_correctlar(const lar_t *lar, double x) {
    lar_t r = *lar;
    for (int i = 1; i <= 10; i++)
        r.t[i - 1] /= 1.001 * pow(x, i);
    return r;
}

static double interm13(double *t) {
    static const double c[32] = {
        -49, 66, -96, 142, -207, 294, -407, 553, -739,
        981, -1304, 1758, -2452, 3688, -6669, 27072, 13496, -5287, 3179,
        -2182, 1587, -1185, 893, -672, 500, -366, 263, -183, 125,
        -84, 59, -47};
    double s = 0;
    for (int i = 0; i < 32; i++)
        s += t[i - 15] * c[i] / 32768;
    return s;
}

static double inter13(double *t) {
    static const double c[32] = {
        -47, 59, -84, 125, -183, 263, -366, 500, -672, 893,
        -1185, 1587, -2182, 3179, -5287, 13496, 27072, -6669, 3688, -2452,
        1758, -1304, 981, -739, 553, -407, 294, -207, 142, -96,
        66, -49};
    double s = 0;
    for (int i = 0; i < 32; i++)
        s += t[i - 16] * c[i] / 32768;
    return s;
}

static void ex(rpcelp *dec, int st, int len, const ltp_t *ltp) {
    int D = ltp_D(ltp);
    int ph = ltp_ph(ltp);
    ph = ph % D;
    int s = ltp_sigs(ltp);
    int Q = ltp_Q(ltp);
    double g1 = ltp_gain(ltp);
    double g2 = ltp_exgain(ltp);
    for (int i = 0; i < len; i++)
        dec->tab[st + i] *= g1;
    for (int i = 0; i < Q && ph < len; i++) {
        if ((s >> (Q - 1 - i)) & 1)
            dec->tab[st + ph] += +g2;
        else
            dec->tab[st + ph] += -g2;
        ph += D;
    }
}

static void lt(rpcelp *dec, int st, int len, const ltp_t *ltp) {
    int ilag = ltp->ilag;
    double g = ltp_gain(ltp);
    int fr = (ilag + 60) % 3;
    int T0 = (ilag + 61) / 3;
    for (int i = st; i < st + len; i++) {
        int j = i - T0;
        if (fr == 0)
            dec->tab[i] += dec->tab[j];
        else if (fr == 1)
            dec->tab[i] += inter13(&dec->tab[i - T0]);
        else
            dec->tab[i] += interm13(&dec->tab[i - T0]);
    }
}

static void st(rpcelp *dec, int st, int len, const lar_t *ll_) {
    lar_t lar = lar2refl(ll_, 0);
    lar = rpcelp_correctlar(&lar, dec->ffb);
    for (int i = st; i < st + len; i++) {
        double sri = dec->tab[i];
        for (int t = 1; t <= 10; t++) {
            sri -= lar.t[10 - t] * dec->v[10 - t];
            dec->v[11 - t] = dec->v[10 - t] + lar.t[10 - t] * sri;
            sat(&dec->v[11 - t], 1000);
        }
        dec->tab2[i] = sri;
        dec->v[0] = sri;
        sat(&dec->v[0], 1000);
    }
}

const double *rpcelp_decode_frame(rpcelp *dec, const unsigned char *bf) {
    static vfr_t vfr;
    static lar_t lar, lars[3];
    static ltp_t ltp[3];
    static bool first = true;
    if (first) {
        init();
        first = false;
    }

    // Convertir bf en vector<bool> (simplifié)
    for (int i = 0; i < MAX_BITS; i++)
        vfr.v[i] = (bf[i / 8] >> (i % 8)) & 1;

    // Décoder LAR
    for (int i = 0; i < MAX_LAR; i++) {
        val_t *it = valslars[i];
        int u = 0;
        for (int j = 0; j < it->len; j++)
            u = (u << 1) | vfr.v[it->vb[j]];
        lar.t[i] = declar(u, i, it->len);
    }
    lar.size = MAX_LAR;

    // Décoder LTP
    for (int i = 0; i < MAX_LTP; i++) {
        ltp_init(&ltp[i], (i == 1) ? 48 : 56);
        ltp[i].ilag = 0;
        for (int j = 0; j < valsltp[i][0]->len; j++)
            ltp[i].ilag = (ltp[i].ilag << 1) | vfr.v[valsltp[i][0]->vb[j]];
        ltp[i].igain = 0;
        for (int j = 0; j < valsltp[i][1]->len; j++)
            ltp[i].igain = (ltp[i].igain << 1) | vfr.v[valsltp[i][1]->vb[j]];
        ltp[i].dec = 0;
        for (int j = 0; j < valsex[i][0]->len; j++)
            ltp[i].dec = (ltp[i].dec << 1) | vfr.v[valsex[i][0]->vb[j]];
        ltp[i].iexgain = 0;
        for (int j = 0; j < valsex[i][1]->len; j++)
            ltp[i].iexgain = (ltp[i].iexgain << 1) | vfr.v[valsex[i][1]->vb[j]];
        ltp[i].iph = 0;
        for (int j = 0; j < valsex[i][2]->len; j++)
            ltp[i].iph = (ltp[i].iph << 1) | vfr.v[valsex[i][2]->vb[j]];
    }

    // Interpolation LAR
    lars[0] = lar_mul(0.875, &lar);
    lars[1] = lar_mul(0.500, &lar);
    lars[2] = lar_mul(0.125, &lar);

    // Mise à jour des buffers
    memmove(dec->tab, dec->tab + 160, sizeof(double) * 160 * 2);
    memmove(dec->tab2, dec->tab2 + 160, sizeof(double) * 160 * 2);
    memset(dec->tab + 320, 0, sizeof(double) * 160);
    memset(dec->tab2 + 320, 0, sizeof(double) * 160);

    // Décodage LTP/ST
    lt(dec, 320, 56, &ltp[0]);
    ex(dec, 320, 56, &ltp[0]);
    lt(dec, 320 + 56, 48, &ltp[1]);
    ex(dec, 320 + 56, 48, &ltp[1]);
    lt(dec, 320 + 56 + 48, 56, &ltp[2]);
    ex(dec, 320 + 56 + 48, 56, &ltp[2]);
    st(dec, 320, 56, &lars[0]);
    st(dec, 320 + 56, 48, &lars[1]);
    st(dec, 320 + 56 + 48, 56, &lars[2]);

    return dec->tab2 + 160 * 2;
}
