"""Speaker enrollment utility for Jarvis Voice-ID using sherpa-onnx CAMP++ model."""

from __future__ import annotations

import argparse
import json
import logging
import wave
from pathlib import Path

import numpy as np
import sherpa_onnx

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def read_wav_16k_mono(wav_path: str | Path) -> np.ndarray:
    """Read a 16kHz mono WAV file and return float32 samples in [-1.0, 1.0]."""
    with wave.open(str(wav_path), "rb") as f:
        channels = f.getnchannels()
        rate = f.getframerate()
        width = f.getsampwidth()
        if channels != 1 or rate != 16000 or width != 2:
            raise ValueError(
                f"Expected 16kHz mono 16-bit PCM, got {channels}ch, {rate}Hz, {width * 8}bit: {wav_path}"
            )
        data = f.readframes(f.getnframes())
        return np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0


def pad_or_tile(
    samples: np.ndarray, target_sec: float = 3.5, rate: int = 16000
) -> np.ndarray:
    """Pad or tile audio samples to target duration to ensure sufficient temporal receptive field."""
    target_samples = int(target_sec * rate)
    if len(samples) >= target_samples:
        return samples
    repeats = int(np.ceil(target_samples / len(samples)))
    return np.tile(samples, repeats)[:target_samples]


def compute_embedding(
    extractor: sherpa_onnx.SpeakerEmbeddingExtractor,
    samples: np.ndarray,
    target_sec: float = 3.5,
    rate: int = 16000,
) -> np.ndarray:
    """Compute and return normalized embedding for a given audio segment."""
    processed = pad_or_tile(samples, target_sec=target_sec, rate=rate)
    stream = extractor.create_stream()
    stream.accept_waveform(rate, processed)
    stream.input_finished()
    vec = np.array(extractor.compute(stream), dtype=np.float32)
    norm = float(np.linalg.norm(vec))
    if norm < 1e-6:
        raise ValueError("Embedding norm near zero; empty or invalid audio segment.")
    return vec / norm


def extract_speaker_centroid(
    extractor: sherpa_onnx.SpeakerEmbeddingExtractor,
    samples: np.ndarray,
    chunk_sec: float = 4.0,
    hop_sec: float = 2.0,
    rms_min: float = 0.008,
) -> tuple[np.ndarray, list[np.ndarray]]:
    """Segment audio, filter silence, and return (normalized centroid, chunk embeddings)."""
    chunk_len = int(chunk_sec * 16000)
    hop_len = int(hop_sec * 16000)
    embs: list[np.ndarray] = []

    for start in range(0, len(samples) - chunk_len + 1, hop_len):
        chunk = samples[start : start + chunk_len]
        rms = float(np.sqrt(np.mean(chunk**2)))
        if rms >= rms_min:
            embs.append(compute_embedding(extractor, chunk))

    if not embs:
        logger.warning(
            "No chunks exceeded rms_min; falling back to full audio segment."
        )
        embs.append(compute_embedding(extractor, samples))

    centroid = np.mean(embs, axis=0)
    centroid /= np.linalg.norm(centroid)
    return centroid, embs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enroll speakers for Jarvis voice identification"
    )
    parser.add_argument(
        "--model", required=True, help="Path to sherpa-onnx speaker model (.onnx)"
    )
    parser.add_argument(
        "--speaker",
        action="append",
        nargs=2,
        metavar=("NAME", "WAV_FILE"),
        required=True,
        help="Speaker name and path to 16kHz mono WAV file",
    )
    parser.add_argument("--output", required=True, help="Path to write profiles.json")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.35,
        help="Cosine similarity threshold for identification",
    )
    parser.add_argument(
        "--min-margin",
        type=float,
        default=0.10,
        help="Minimum margin over second-best speaker",
    )
    args = parser.parse_args()

    config = sherpa_onnx.SpeakerEmbeddingExtractorConfig(
        model=args.model,
        num_threads=2,
        debug=False,
    )
    extractor = sherpa_onnx.SpeakerEmbeddingExtractor(config)
    logger.info(
        f"Loaded speaker model from {args.model} (embedding dim: {extractor.dim})"
    )

    speakers: dict[str, list[float]] = {}
    speaker_data: dict[str, tuple[np.ndarray, list[np.ndarray]]] = {}

    for name, wav_path in args.speaker:
        logger.info(f"Enrolling speaker: {name} from {wav_path}")
        samples = read_wav_16k_mono(wav_path)
        centroid, embs = extract_speaker_centroid(extractor, samples)
        logger.info(
            f"  {name}: {len(embs)} speech chunks extracted. Centroid norm: {np.linalg.norm(centroid):.4f}"
        )
        speakers[name] = centroid.tolist()
        speaker_data[name] = (centroid, embs)

    # Verification report
    names = list(speakers.keys())
    logger.info("=== Speaker Similarity Matrix ===")
    for n1 in names:
        c1 = np.array(speakers[n1])
        row = [f"{n2}: {float(np.dot(c1, np.array(speakers[n2]))):.3f}" for n2 in names]
        logger.info(f"  {n1:<10} -> {', '.join(row)}")

    # Self-validation on chunks
    logger.info("=== Chunk Classification Validation ===")
    for name, (_, embs) in speaker_data.items():
        correct = 0
        total = len(embs)
        for emb in embs:
            scores = {n: float(np.dot(emb, np.array(speakers[n]))) for n in names}
            best_speaker = max(scores, key=scores.get)  # type: ignore[arg-type]
            if best_speaker == name:
                correct += 1
        acc = (correct / total) * 100 if total > 0 else 0
        logger.info(
            f"  {name}: {correct}/{total} chunks correctly classified ({acc:.1f}%)"
        )

    output_payload = {
        "version": 1,
        "embedding_dim": extractor.dim,
        "threshold": args.threshold,
        "min_margin": args.min_margin,
        "speakers": speakers,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2)
    logger.info(f"Saved speaker profiles to {args.output}")


if __name__ == "__main__":
    main()
