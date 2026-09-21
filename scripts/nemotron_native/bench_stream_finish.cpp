// Minimal native streaming finish harness for the Nemotron benchmark.
//
// Drives the stable C ABI streaming path directly, bypassing the HTTP
// server: open stream, push 16 kHz mono float32 slices, drain interims,
// then time nemo_speech_asr_stream_finish() and report the final.
//
// Usage:
//   bench_stream_finish <model.gguf> <audio.wav> [--gpu N] [--right-ctx R]
//                       [--slice-ms N] [--pace] [--lang CODE] [--max-audio-s S]
//
// Output: one JSON line on stdout:
//   {"slices":N,"interims":M,"finish_latency_s":F,"finish_status":S,
//    "final":"...","audio_processed":A}
// Exit 0 on measured finish. A hung finish() is the datum: run each trial
// under timeout(1); exit 124 means the native finish path wedged.
//
// --max-audio-s truncates the input to the first S seconds (length matrix).
// --pace sleeps slice-ms between pushes to emulate realtime arrival.

#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <thread>
#include <vector>

#include "nemo_speech/asr.h"

namespace {

constexpr int kSampleRate = 16000;

bool read_wav_pcm16_mono(const char* path, std::vector<float>& out, std::string& err) {
    FILE* f = std::fopen(path, "rb");
    if (!f) {
        err = "cannot open file";
        return false;
    }
    auto read_u32 = [&]() -> uint32_t {
        uint8_t b[4];
        if (std::fread(b, 1, 4, f) != 4)
            return 0;
        return (uint32_t)b[0] | ((uint32_t)b[1] << 8) | ((uint32_t)b[2] << 16) |
               ((uint32_t)b[3] << 24);
    };
    auto read_u16 = [&]() -> uint16_t {
        uint8_t b[2];
        if (std::fread(b, 1, 2, f) != 2)
            return 0;
        return (uint16_t)b[0] | ((uint16_t)b[1] << 8);
    };
    char riff[4], wave[4];
    if (std::fread(riff, 1, 4, f) != 4 || std::memcmp(riff, "RIFF", 4) != 0) {
        err = "not a RIFF file";
        std::fclose(f);
        return false;
    }
    read_u32();
    if (std::fread(wave, 1, 4, f) != 4 || std::memcmp(wave, "WAVE", 4) != 0) {
        err = "not a WAVE file";
        std::fclose(f);
        return false;
    }
    int fmt = -1, channels = -1, rate = -1, bits = -1;
    long data_pos = -1;
    uint32_t data_len = 0;
    while (!std::feof(f)) {
        char id[4];
        if (std::fread(id, 1, 4, f) != 4)
            break;
        uint32_t len = read_u32();
        long next = std::ftell(f) + (long)len;
        if (std::memcmp(id, "fmt ", 4) == 0) {
            fmt = read_u16();
            channels = read_u16();
            rate = (int)read_u32();
            read_u32();
            read_u16();
            bits = read_u16();
        } else if (std::memcmp(id, "data", 4) == 0) {
            data_pos = std::ftell(f);
            data_len = len;
            break;
        }
        std::fseek(f, next, SEEK_SET);
    }
    if (fmt != 1 || channels != 1 || rate != kSampleRate || bits != 16 || data_pos < 0) {
        err = "need 16kHz mono PCM16 WAV";
        std::fclose(f);
        return false;
    }
    std::fseek(f, data_pos, SEEK_SET);
    size_t nsamples = data_len / 2;
    std::vector<int16_t> raw(nsamples);
    if (std::fread(raw.data(), 2, nsamples, f) != nsamples) {
        err = "short data chunk";
        std::fclose(f);
        return false;
    }
    std::fclose(f);
    out.resize(nsamples);
    for (size_t i = 0; i < nsamples; i++)
        out[i] = raw[i] / 32768.0f;
    return true;
}

void json_escape(const std::string& in, std::string& out) {
    for (char c : in) {
        switch (c) {
            case '"': out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            default:
                if ((unsigned char)c < 0x20) {
                    char buf[8];
                    std::snprintf(buf, sizeof(buf), "\\u%04x", c);
                    out += buf;
                } else {
                    out += c;
                }
        }
    }
}

}  // namespace

int main(int argc, char** argv) {
    if (argc < 3) {
        std::fprintf(
            stderr,
            "Usage: %s <model.gguf> <audio.wav> [--gpu N] [--right-ctx R]\n"
            "                    [--slice-ms N] [--pace] [--lang CODE] [--max-audio-s S]\n",
            argv[0]);
        return 1;
    }
    const char* model_path = argv[1];
    const char* audio_path = argv[2];
    int gpu = 0;
    int right_ctx = 1;
    int slice_ms = 100;
    bool pace = false;
    std::string language;
    double max_audio_s = -1.0;
    for (int i = 3; i < argc; i++) {
        std::string a = argv[i];
        if (a == "--gpu" && i + 1 < argc)
            gpu = std::atoi(argv[++i]);
        else if (a == "--right-ctx" && i + 1 < argc)
            right_ctx = std::atoi(argv[++i]);
        else if (a == "--slice-ms" && i + 1 < argc)
            slice_ms = std::atoi(argv[++i]);
        else if (a == "--pace")
            pace = true;
        else if (a == "--lang" && i + 1 < argc)
            language = argv[++i];
        else if (a == "--max-audio-s" && i + 1 < argc)
            max_audio_s = std::atof(argv[++i]);
    }

    std::vector<float> audio;
    std::string err;
    if (!read_wav_pcm16_mono(audio_path, audio, err)) {
        std::fprintf(stderr, "[bench] %s: %s\n", audio_path, err.c_str());
        return 2;
    }
    if (max_audio_s > 0.0) {
        size_t keep = (size_t)(max_audio_s * kSampleRate);
        if (keep < audio.size())
            audio.resize(keep);
    }

    nemo_speech_asr_backend_config backend = {};
    backend.size = sizeof(backend);
    backend.gpu = gpu;

    nemo_speech_asr_model_config model = {};
    model.size = sizeof(model);
    model.path = model_path;

    nemo_speech_asr_streaming_config streaming = {};
    streaming.size = sizeof(streaming);
    streaming.chunk_size = 0.16f;
    streaming.ctc_left_padding = 1.92f;
    streaming.ctc_right_padding = 1.92f;
    streaming.rnnt_right_context = right_ctx;

    nemo_speech_asr_recognizer_config cfg = {};
    cfg.size = sizeof(cfg);
    cfg.backend = &backend;
    cfg.model = &model;
    cfg.streaming = &streaming;

    nemo_speech_asr_recognizer* recognizer = nullptr;
    if (nemo_speech_asr_create(&cfg, &recognizer) != NEMO_SPEECH_ASR_OK) {
        std::fprintf(
            stderr, "[bench] create failed: %s\n", nemo_speech_asr_last_error());
        return 2;
    }

    nemo_speech_asr_recognition_options opts = nemo_speech_asr_recognition_options_default();
    opts.interim_results = true;
    opts.enable_automatic_punctuation = true;
    opts.language_code = language.empty() ? nullptr : language.c_str();

    nemo_speech_asr_stream* stream = nullptr;
    if (nemo_speech_asr_streaming_recognize(recognizer, &opts, &stream) !=
        NEMO_SPEECH_ASR_OK) {
        std::fprintf(
            stderr, "[bench] streaming_recognize failed: %s\n",
            nemo_speech_asr_last_error());
        nemo_speech_asr_destroy(recognizer);
        return 2;
    }

    size_t slice_samples = (size_t)slice_ms * kSampleRate / 1000;
    size_t slices = 0, interims = 0;
    std::string last_final;
    float last_processed = 0.0f;
    auto drain = [&]() {
        nemo_speech_asr_result* res = nullptr;
        while (nemo_speech_asr_stream_next(stream, &res) == NEMO_SPEECH_ASR_OK && res) {
            const char* text = nemo_speech_asr_result_transcript(res, 0);
            if (nemo_speech_asr_result_is_final(res)) {
                if (text)
                    last_final = text;
            } else {
                interims++;
            }
            last_processed = nemo_speech_asr_result_audio_processed(res);
            nemo_speech_asr_result_destroy(res);
            res = nullptr;
        }
    };

    for (size_t off = 0; off < audio.size(); off += slice_samples) {
        size_t n = slice_samples;
        if (off + n > audio.size())
            n = audio.size() - off;
        if (n == 0)
            break;
        if (nemo_speech_asr_stream_push_f32(stream, audio.data() + off, n, kSampleRate) !=
            NEMO_SPEECH_ASR_OK) {
            std::fprintf(
                stderr, "[bench] push failed: %s\n", nemo_speech_asr_last_error());
            nemo_speech_asr_stream_close(stream);
            nemo_speech_asr_destroy(recognizer);
            return 2;
        }
        slices++;
        drain();
        if (pace)
            std::this_thread::sleep_for(std::chrono::milliseconds(slice_ms));
    }

    auto t0 = std::chrono::steady_clock::now();
    nemo_speech_asr_status fst = nemo_speech_asr_stream_finish(stream);
    auto t1 = std::chrono::steady_clock::now();
    double finish_latency =
        std::chrono::duration_cast<std::chrono::duration<double>>(t1 - t0).count();
    drain();

    std::string esc;
    json_escape(last_final, esc);
    std::printf(
        "{\"slices\":%zu,\"interims\":%zu,\"finish_latency_s\":%.3f,"
        "\"finish_status\":%d,\"final\":\"%s\",\"audio_processed\":%.2f}\n",
        slices, interims, finish_latency, (int)fst, esc.c_str(), last_processed);

    nemo_speech_asr_stream_close(stream);
    nemo_speech_asr_destroy(recognizer);
    return 0;
}
