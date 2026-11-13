from clipforge import picker
from clipforge.transcript import Word


def test_signals_pick_the_loud_passage(cfg):
    loudness = [-50.0] * 60
    loudness[30:38] = [-10.0] * 8
    clips = picker.pick_with_signals({"duration": 60, "title": "T"}, [], loudness, [], cfg)
    assert clips and clips[0]["start"] <= 31 and clips[0]["end"] >= 35
    starts = sorted(c["start"] for c in clips)
    assert all(b - a >= 6 for a, b in zip(starts, starts[1:]))


def test_normalize_clamps_snaps_and_drops_overlaps(cfg):
    words = [Word(10.2, 10.6, "go"), Word(15.5, 16.0, "done")]
    ideas = [
        {"start": 10.0, "end": 16.4, "score": 9, "hashtags": ["#GTA 6", ""]},
        {"start": 12.0, "end": 18.0, "score": 5, "hashtags": []},      # overlaps the better clip
        {"start": 55.0, "end": 99.0, "score": 7, "hashtags": []},      # runs past the end
    ]
    clips = picker.normalize(ideas, 60.0, words, cfg)
    assert [c["id"] for c in clips] == ["clip01", "clip02"]
    first, second = clips
    assert abs(first["start"] - 10.05) < 0.01 and abs(first["end"] - 16.25) < 0.01
    assert first["hashtags"] == ["GTA6"]
    assert second["end"] == 60.0 and second["end"] - second["start"] >= cfg["clips"]["min_seconds"]


def test_pick_falls_back_to_signals_without_credentials(cfg, monkeypatch):
    for name in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        monkeypatch.delenv(name, raising=False)

    def boom(*_args, **_kwargs):
        raise TypeError("Could not resolve authentication method")

    monkeypatch.setattr(picker, "pick_with_claude", boom)
    clips, selector = picker.pick({"duration": 30, "title": "T"}, [], [-20.0] * 30, [], cfg)
    assert clips and selector == "signals (no Claude API key set)"


def test_prompt_contains_transcript_and_limits(cfg):
    prompt = picker.build_prompt({"title": "Trailer", "channel": "C", "duration": 90},
                                 [Word(1, 2, "hello")], [-20.0] * 90, [3.0], cfg)
    assert "<transcript>" in prompt and "[1.0-2.0] hello" in prompt
    assert "between 4 and 8 seconds" in prompt and "Scene cuts at: 0:03.0" in prompt
