"""Word-level transcripts from YouTube captions (json3 / vtt) or local Whisper."""

from __future__ import annotations

import html
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Word:
    start: float
    end: float
    text: str


def _spread(text: str, start: float, end: float) -> list[Word]:
    """Split a caption line into words with evenly spaced timings."""
    tokens = text.split()
    if not tokens or end <= start:
        return []
    step = (end - start) / len(tokens)
    return [Word(start + i * step, start + (i + 1) * step, tok) for i, tok in enumerate(tokens)]


def parse_json3(path: Path) -> list[Word]:
    """YouTube json3: auto captions carry per-word offsets, manual ones a line per event."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    words: list[Word] = []
    for event in data.get("events", []):
        segs = event.get("segs")
        if not segs or "tStartMs" not in event:
            continue
        ev_start = event["tStartMs"] / 1000
        ev_end = ev_start + event.get("dDurationMs", 0) / 1000
        timed = any("tOffsetMs" in seg for seg in segs)
        if timed or len(segs) > 1:
            pieces = [
                (ev_start + seg.get("tOffsetMs", 0) / 1000, seg.get("utf8", "").strip())
                for seg in segs
            ]
            pieces = [(t, txt) for t, txt in pieces if txt]
            for i, (t, txt) in enumerate(pieces):
                nxt = pieces[i + 1][0] if i + 1 < len(pieces) else max(ev_end, t + 0.3)
                words.extend(_spread(txt, t, max(nxt, t + 0.05)))
        else:
            text = segs[0].get("utf8", "").replace("\n", " ").strip()
            words.extend(_spread(text, ev_start, ev_end))
    return _clean(words)


_TS = r"(?:(\d+):)?(\d{2}):(\d{2})[.,](\d{3})"
_CUE = re.compile(_TS + r"\s+-->\s+" + _TS)


def _seconds(h, m, s, ms) -> float:
    return int(h or 0) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_vtt(path: Path) -> list[Word]:
    """WebVTT / SRT. YouTube auto-caption VTT repeats rolling lines; duplicates are dropped."""
    words: list[Word] = []
    last_line = ""
    cue = None
    for raw in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        match = _CUE.search(line)
        if match:
            g = match.groups()
            cue = (_seconds(*g[:4]), _seconds(*g[4:]))
            continue
        if not line:
            cue = None
            continue
        if cue is None:
            continue
        text = html.unescape(re.sub(r"<[^>]+>", "", line)).strip()
        if not text or text == last_line:
            continue
        last_line = text
        words.extend(_spread(text, *cue))
    return _clean(words)


def _clean(words: list[Word]) -> list[Word]:
    words = [w for w in words if w.text and not re.fullmatch(r"\[.*\]|♪+", w.text)]
    words.sort(key=lambda w: w.start)
    for i in range(len(words) - 1):  # keep words from overlapping
        if words[i].end > words[i + 1].start:
            words[i].end = max(words[i].start + 0.02, words[i + 1].start)
    return words


def whisper_available() -> bool:
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        return False
    return True


def transcribe_whisper(media_path: Path, model_size: str = "small") -> list[Word]:
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, compute_type="int8")
    segments, _info = model.transcribe(str(media_path), word_timestamps=True, vad_filter=True)
    words = [
        Word(float(w.start), float(w.end), w.word.strip())
        for seg in segments
        for w in (seg.words or [])
    ]
    return _clean(words)


def load_captions(job_folder: Path) -> list[Word]:
    """Best caption file next to the source video, if any."""
    for pattern, parser in (("source*.json3", parse_json3), ("source*.vtt", parse_vtt),
                            ("source*.srt", parse_vtt)):
        for path in sorted(job_folder.glob(pattern)):
            words = parser(path)
            if words:
                return words
    return []


def to_lines(words: list[Word], max_gap: float = 0.8, max_words: int = 16) -> list[tuple[float, float, str]]:
    """Group words into readable lines of (start, end, text)."""
    lines: list[tuple[float, float, str]] = []
    current: list[Word] = []
    for word in words:
        if current and (
            word.start - current[-1].end > max_gap
            or len(current) >= max_words
            or current[-1].text.endswith((".", "?", "!"))
        ):
            lines.append((current[0].start, current[-1].end, " ".join(w.text for w in current)))
            current = []
        current.append(word)
    if current:
        lines.append((current[0].start, current[-1].end, " ".join(w.text for w in current)))
    return lines


def save(words: list[Word], path: Path) -> None:
    path.write_text(json.dumps([asdict(w) for w in words]))


def load(path: Path) -> list[Word]:
    if not path.is_file():
        return []
    return [Word(**item) for item in json.loads(path.read_text())]
