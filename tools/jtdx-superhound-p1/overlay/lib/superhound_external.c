#ifndef _WIN32
#define _POSIX_C_SOURCE 200809L
#endif

/*
 * SQ4KOU JTDX SuperHound P1 bridge
 *
 * This file contains no SuperFox/QPC implementation. It passes a 12 kHz
 * JTDX receive buffer to a separately built WSJT-X command-line SuperFox
 * decoder (sfrx) through a temporary PCM WAV file and forwards decoder
 * output back to the normal JTDX decoder stdout stream.
 */

#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
#  include <process.h>
#  define JTDX_GETPID _getpid
#  define JTDX_POPEN _popen
#  define JTDX_PCLOSE _pclose
#  define JTDX_PATH_SEP '\\'
#else
#  include <unistd.h>
#  define JTDX_GETPID getpid
#  define JTDX_POPEN popen
#  define JTDX_PCLOSE pclose
#  define JTDX_PATH_SEP '/'
#endif

static void put_u16le(FILE *f, uint16_t v)
{
    fputc((int)(v & 0xffu), f);
    fputc((int)((v >> 8) & 0xffu), f);
}

static void put_u32le(FILE *f, uint32_t v)
{
    fputc((int)(v & 0xffu), f);
    fputc((int)((v >> 8) & 0xffu), f);
    fputc((int)((v >> 16) & 0xffu), f);
    fputc((int)((v >> 24) & 0xffu), f);
}

static int write_pcm16_wav(const char *path, const float *samples, int npts)
{
    FILE *f;
    uint32_t data_bytes;
    int i;

    if (!path || !samples || npts <= 0) return -1;
    f = fopen(path, "wb");
    if (!f) return -2;

    data_bytes = (uint32_t)npts * 2u;
    fwrite("RIFF", 1, 4, f);
    put_u32le(f, 36u + data_bytes);
    fwrite("WAVE", 1, 4, f);
    fwrite("fmt ", 1, 4, f);
    put_u32le(f, 16u);
    put_u16le(f, 1u);
    put_u16le(f, 1u);
    put_u32le(f, 12000u);
    put_u32le(f, 24000u);
    put_u16le(f, 2u);
    put_u16le(f, 16u);
    fwrite("data", 1, 4, f);
    put_u32le(f, data_bytes);

    for (i = 0; i < npts; ++i) {
        float x = samples[i];
        int32_t q;
        if (x > 32767.0f) x = 32767.0f;
        if (x < -32768.0f) x = -32768.0f;
        q = (x >= 0.0f) ? (int32_t)(x + 0.5f) : (int32_t)(x - 0.5f);
        put_u16le(f, (uint16_t)(int16_t)q);
    }

    if (fclose(f) != 0) return -3;
    return 0;
}

static const char *temp_dir(void)
{
#ifdef _WIN32
    const char *p = getenv("TEMP");
    if (!p || !*p) p = getenv("TMP");
#else
    const char *p = getenv("TMPDIR");
#endif
    if (!p || !*p) p = ".";
    return p;
}

static void forward_line(char *line)
{
    char *p;
    size_t n;
    if (!line) return;
    p = strstr(line, "~  ");
    if (p) {
        n = strlen(p + 3);
        memmove(p + 2, p + 3, n + 1);
    }
    fputs(line, stdout);
}

int jtdx_superhound_external_c(int nutc, const float *samples, int npts)
{
    const char *helper = getenv("JTDX_SFRX");
    const char *tdir;
    char wav[1024];
    char cmd[4096];
    char line[1024];
    FILE *pipe;
    int rc;
    long pid;

    if (!helper || !*helper) return 0;
    if (!samples || npts < 180000) return -10;

    tdir = temp_dir();
    pid = (long)JTDX_GETPID();
    snprintf(wav, sizeof(wav), "%s%cjtdx_%ld_000000_%06d.wav",
             tdir, JTDX_PATH_SEP, pid, nutc % 1000000);

    rc = write_pcm16_wav(wav, samples, 180000);
    if (rc != 0) return -20 + rc;

    snprintf(cmd, sizeof(cmd), "\"%s\" 750 100 \"%s\"", helper, wav);

    pipe = JTDX_POPEN(cmd, "r");
    if (!pipe) {
        remove(wav);
        return -30;
    }

    while (fgets(line, sizeof(line), pipe)) {
        forward_line(line);
    }
    rc = JTDX_PCLOSE(pipe);
    remove(wav);
    fflush(stdout);
    return rc;
}
