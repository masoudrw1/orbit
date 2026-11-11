"""Optional offline speech adapter; importing this file does not open the mic."""

import json
from pathlib import Path
import shutil
import subprocess
import threading
from collections.abc import Callable

from .core import VoiceGate


class VoiceListener:
    """Vosk is used for both the prototype wake phrase and English commands.

    This is a constrained speech recognizer, not a dedicated wake-word model.
    It needs real microphone, accent, noise, and idle-resource testing before v1.
    """
    def __init__(self, model_path: Path, phrases: list[str],
                 emit: Callable[[str, str], None]):
        self.model_path, self.phrases, self.emit = model_path, phrases, emit
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.recorder: subprocess.Popen | None = None
        self.recorder_lock = threading.Lock()

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self._run, name="orbit-voice", daemon=True)
        self.thread.start()

    def _run(self) -> None:
        try:
            if not (self.model_path / "am" / "final.mdl").is_file():
                raise RuntimeError("The English speech model is missing. Reinstall Orbit or check the development setup.")
            if not shutil.which("parec"):
                raise RuntimeError("Microphone recording is unavailable. Check that Orbit's required system packages are installed.")
            try:
                from vosk import Model, KaldiRecognizer, SetLogLevel
            except ImportError as exc:
                raise RuntimeError("The speech engine is unavailable. Reinstall Orbit or check the development setup.") from exc
            self.emit("loading", "Loading the offline English speech model…")
            SetLogLevel(-1)
            model = Model(str(self.model_path))
            gate = VoiceGate()
            grammar = sorted({"[unk]", "cancel", gate.wake_phrase, *self.phrases,
                              *(f"{gate.wake_phrase} {p}" for p in self.phrases)})
            decoder = KaldiRecognizer(model, 16000, json.dumps(grammar))
            with self.recorder_lock:
                if self.stop_event.is_set():
                    return
                self.recorder = subprocess.Popen(
                    ["parec", "--format=s16le", "--rate=16000", "--channels=1", "--raw", "--latency-msec=100"],
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                )
            self.emit("ready", 'Microphone on · Say “Hey Orbit”, pause, then your command.')
            while not self.stop_event.is_set():
                pcm = self.recorder.stdout.read(4000)
                if not pcm:
                    if not self.stop_event.is_set():
                        raise RuntimeError("Microphone stream ended. Check your default input device and audio session.")
                    break
                if gate.expire():
                    self.emit("timeout", "No command heard. Say “Hey Orbit” to try again.")
                if decoder.AcceptWaveform(pcm):
                    transcript = json.loads(decoder.Result()).get("text", "")
                    for event, text in gate.feed(transcript):
                        self.emit(event, text)
        except Exception as exc:
            if not self.stop_event.is_set():
                self.emit("error", str(exc))
        finally:
            if self.recorder and self.recorder.poll() is None:
                self.recorder.terminate()
                try:
                    self.recorder.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.recorder.kill()
                    self.recorder.wait()
            self.emit("stopped", "Microphone off")

    def stop(self) -> None:
        self.stop_event.set()
        with self.recorder_lock:
            if self.recorder and self.recorder.poll() is None:
                self.recorder.terminate()
