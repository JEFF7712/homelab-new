"""Wyoming Voice-ID Proxy.

Intercepts Wyoming STT audio events, identifies the speaker using sherpa-onnx
speaker embeddings, and prepends [Speaker: <Name>] to the transcript.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import urllib.request
from pathlib import Path

import numpy as np
import sherpa_onnx
from wyoming.asr import Transcript
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.event import async_read_event, async_write_event

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [voice-id] %(message)s",
)
logger = logging.getLogger("voice-id")


def pad_or_tile(
    samples: np.ndarray, target_sec: float = 3.5, rate: int = 16000
) -> np.ndarray:
    """Pad or tile audio samples to target duration to ensure sufficient temporal receptive field."""
    target_samples = int(target_sec * rate)
    if len(samples) >= target_samples:
        return samples
    repeats = int(np.ceil(target_samples / len(samples)))
    return np.tile(samples, repeats)[:target_samples]


class VoiceIdClassifier:
    def __init__(
        self,
        model_path: str | Path,
        profiles_path: str | Path,
        model_url: str | None = None,
    ) -> None:
        self.model_path = Path(model_path)
        self.profiles_path = Path(profiles_path)
        self.model_url = model_url

        self._ensure_model()
        self.config = sherpa_onnx.SpeakerEmbeddingExtractorConfig(
            model=str(self.model_path),
            num_threads=2,
            debug=False,
        )
        self.extractor = sherpa_onnx.SpeakerEmbeddingExtractor(self.config)
        self.profiles: dict[str, np.ndarray] = {}
        self.threshold = 0.35
        self.min_margin = 0.10
        self._load_profiles()

    def _ensure_model(self) -> None:
        if self.model_path.exists():
            return
        if not self.model_url:
            raise FileNotFoundError(
                f"Model not found at {self.model_path} and no model_url provided"
            )
        logger.info(
            f"Model not found at {self.model_path}. Downloading from {self.model_url}..."
        )
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.model_path.with_suffix(".tmp")
        urllib.request.urlretrieve(self.model_url, tmp_path)
        tmp_path.rename(self.model_path)
        logger.info(f"Model downloaded successfully to {self.model_path}")

    def _load_profiles(self) -> None:
        if not self.profiles_path.exists():
            logger.warning(
                f"Profiles file not found at {self.profiles_path}; running with empty profiles."
            )
            return
        with self.profiles_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        self.threshold = float(data.get("threshold", 0.35))
        self.min_margin = float(data.get("min_margin", 0.10))
        self.profiles = {
            name: np.array(vec, dtype=np.float32)
            for name, vec in data.get("speakers", {}).items()
        }
        logger.info(
            f"Loaded {len(self.profiles)} speaker profiles: {list(self.profiles.keys())} "
            f"(threshold: {self.threshold}, min_margin: {self.min_margin})"
        )

    def identify_pcm(
        self, pcm_bytes: bytes, rate: int = 16000
    ) -> tuple[str | None, dict[str, float]]:
        """Identify speaker from 16kHz 16-bit mono PCM bytes."""
        min_samples = int(0.6 * rate)  # minimum 0.6s
        if not self.profiles or len(pcm_bytes) < min_samples * 2:
            return None, {}

        samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        # Check energy
        rms = float(np.sqrt(np.mean(samples**2)))
        if rms < 0.003:
            logger.debug(f"Audio energy too low (rms={rms:.5f}); skipping speaker ID")
            return None, {}

        # Pad / tile to 3.5s to ensure full context for the neural network
        processed = pad_or_tile(samples, target_sec=3.5, rate=rate)

        stream = self.extractor.create_stream()
        stream.accept_waveform(rate, processed)
        stream.input_finished()
        vec = np.array(self.extractor.compute(stream), dtype=np.float32)
        norm = float(np.linalg.norm(vec))
        if norm < 1e-6:
            return None, {}
        vec /= norm

        scores = {
            name: float(np.dot(vec, centroid))
            for name, centroid in self.profiles.items()
        }
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_speaker, top_score = sorted_scores[0]
        runner_up_score = sorted_scores[1][1] if len(sorted_scores) > 1 else -1.0
        margin = top_score - runner_up_score

        if top_score >= self.threshold and margin >= self.min_margin:
            logger.info(
                f"Identified speaker: {top_speaker} (score={top_score:.3f}, margin={margin:.3f})"
            )
            return top_speaker, scores

        logger.info(
            f"Ambiguous or unknown speaker: top={top_speaker} ({top_score:.3f}), "
            f"runner_up=({runner_up_score:.3f}, margin={margin:.3f}, thresh={self.threshold})"
        )
        return None, scores


class SessionState:
    def __init__(self) -> None:
        self.audio_buffer = bytearray()
        self.speaker: str | None = None
        self.recognition_done = asyncio.Event()
        self.recognition_done.set()

    def reset_audio(self) -> None:
        self.audio_buffer.clear()
        self.speaker = None
        self.recognition_done.set()


async def handle_client(
    reader_c: asyncio.StreamReader,
    writer_c: asyncio.StreamWriter,
    upstream_host: str,
    upstream_port: int,
    classifier: VoiceIdClassifier,
) -> None:
    client_addr = writer_c.get_extra_info("peername")
    logger.info(f"Connection accepted from {client_addr}")

    try:
        reader_u, writer_u = await asyncio.open_connection(upstream_host, upstream_port)
    except Exception as e:
        logger.error(
            f"Failed to connect to upstream Whisper at {upstream_host}:{upstream_port}: {e}"
        )
        writer_c.close()
        await writer_c.wait_closed()
        return

    session = SessionState()

    async def client_to_upstream() -> None:
        try:
            while True:
                event = await async_read_event(reader_c)
                if event is None:
                    break

                if AudioStart.is_type(event.type):
                    session.reset_audio()

                elif AudioChunk.is_type(event.type):
                    if event.payload:
                        session.audio_buffer.extend(event.payload)

                elif AudioStop.is_type(event.type):
                    session.recognition_done.clear()
                    pcm = bytes(session.audio_buffer)

                    # Compute identification
                    speaker, _ = classifier.identify_pcm(pcm)
                    session.speaker = speaker
                    session.recognition_done.set()

                await async_write_event(event, writer_u)
        except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
            pass
        except Exception as e:
            logger.error(f"Error in client_to_upstream: {e}", exc_info=True)
        finally:
            writer_u.close()
            try:
                await writer_u.wait_closed()
            except Exception:
                pass

    async def upstream_to_client() -> None:
        try:
            while True:
                event = await async_read_event(reader_u)
                if event is None:
                    break

                if Transcript.is_type(event.type):
                    try:
                        await asyncio.wait_for(
                            session.recognition_done.wait(), timeout=1.5
                        )
                    except asyncio.TimeoutError:
                        logger.warning(
                            "Timed out waiting for speaker recognition to finish"
                        )

                    if session.speaker and event.data and "text" in event.data:
                        orig_text = event.data["text"].strip()
                        tagged_text = f"[Speaker: {session.speaker}] {orig_text}"
                        event.data["text"] = tagged_text
                        logger.info(f"Tagged transcript: {tagged_text}")
                    session.reset_audio()

                await async_write_event(event, writer_c)
        except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
            pass
        except Exception as e:
            logger.error(f"Error in upstream_to_client: {e}", exc_info=True)
        finally:
            writer_c.close()
            try:
                await writer_c.wait_closed()
            except Exception:
                pass

    t1 = asyncio.create_task(client_to_upstream())
    t2 = asyncio.create_task(upstream_to_client())

    done, pending = await asyncio.wait([t1, t2], return_when=asyncio.FIRST_COMPLETED)
    for task in pending:
        task.cancel()
    logger.info(f"Connection closed for {client_addr}")


async def run_proxy(args: argparse.Namespace) -> None:
    classifier = VoiceIdClassifier(
        model_path=args.model,
        profiles_path=args.profiles,
        model_url=args.model_url,
    )

    server = await asyncio.start_server(
        lambda r, w: handle_client(
            r, w, args.upstream_host, args.upstream_port, classifier
        ),
        args.host,
        args.port,
    )

    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
    logger.info(
        f"Wyoming Voice-ID Proxy listening on {addrs} -> upstream {args.upstream_host}:{args.upstream_port}"
    )

    async with server:
        await server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Wyoming Voice-ID Proxy")
    parser.add_argument("--host", default="0.0.0.0", help="Listen host")
    parser.add_argument("--port", type=int, default=10300, help="Listen port")
    parser.add_argument(
        "--upstream-host", default="127.0.0.1", help="Upstream Whisper host"
    )
    parser.add_argument(
        "--upstream-port", type=int, default=10301, help="Upstream Whisper port"
    )
    parser.add_argument(
        "--model", default="/data/model.onnx", help="Path to CAMP++ ONNX model"
    )
    parser.add_argument(
        "--profiles", default="/data/profiles.json", help="Path to profiles.json"
    )
    parser.add_argument(
        "--model-url",
        default="https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/3dspeaker_speech_campplus_sv_en_voxceleb_16k.onnx",
        help="URL to download model if missing",
    )
    args = parser.parse_args()

    asyncio.run(run_proxy(args))


if __name__ == "__main__":
    main()
