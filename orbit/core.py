"""Plain Python: this module knows nothing about GTK, microphones, or Linux."""

from dataclasses import dataclass
import re
import time


def normalize(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))


@dataclass(frozen=True)
class Action:
    identifier: str
    title: str
    kind: str
    phrases: tuple[str, ...]


class Catalog:
    def __init__(self, actions: list[Action]):
        self.actions = actions

    def resolve(self, text: str) -> Action | None:
        """Only an unambiguous, complete phrase is allowed to trigger an action."""
        phrase = normalize(text)
        matches = [a for a in self.actions if phrase and
                   phrase in {normalize(p) for p in a.phrases}]
        return matches[0] if len(matches) == 1 else None

    def search(self, text: str, limit: int = 10) -> list[Action]:
        phrase = normalize(text)
        def rank(action: Action) -> tuple[int, str]:
            names = {normalize(action.title), *(normalize(p) for p in action.phrases)}
            score = (0 if phrase in names else
                     1 if any(n.startswith(phrase) for n in names) else 2)
            return score, action.title.casefold()
        found = [a for a in self.actions if not phrase or
                 any(phrase in normalize(p) for p in (a.title, *a.phrases))]
        return sorted(found, key=rank)[:limit]

    def voice_phrases(self) -> list[str]:
        return sorted({normalize(p) for a in self.actions for p in a.phrases
                       if self.resolve(p) is not None})


class VoiceGate:
    """Recognized speech must contain the wake phrase, or follow it within 8s."""
    def __init__(self, wake_phrase: str = "hey orbit", timeout: float = 8.0):
        self.wake_phrase = normalize(wake_phrase)
        self.timeout = timeout
        self.deadline = 0.0

    def feed(self, transcript: str, now: float | None = None) -> list[tuple[str, str]]:
        now = time.monotonic() if now is None else now
        text = normalize(transcript)
        if not text or text == "unk":
            return []
        if text == self.wake_phrase or text.startswith(self.wake_phrase + " "):
            self.deadline = now + self.timeout
            remainder = text[len(self.wake_phrase):].strip()
            if remainder:
                self.deadline = 0.0
                return [("wake", ""), ("command", remainder)]
            return [("wake", "")]
        if self.deadline and now <= self.deadline:
            self.deadline = 0.0
            return [("cancel", "")] if text == "cancel" else [("command", text)]
        self.deadline = 0.0
        return []

    def expire(self, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        if self.deadline and now > self.deadline:
            self.deadline = 0.0
            return True
        return False
