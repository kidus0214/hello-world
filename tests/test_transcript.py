import json

from clipforge import transcript
from clipforge.transcript import Word


def test_json3_auto_captions_keep_word_offsets(tmp_path):
    path = tmp_path / "source.en.json3"
    path.write_text(json.dumps({"events": [
        {"tStartMs": 1000, "dDurationMs": 2000, "segs": [
            {"utf8": "hello"}, {"utf8": " world", "tOffsetMs": 600}]},
        {"tStartMs": 3000, "dDurationMs": 100, "segs": [{"utf8": "\n"}]},
        {"tStartMs": 4000, "dDurationMs": 2000, "segs": [{"utf8": "manual caption line"}]},
    ]}))
    words = transcript.parse_json3(path)
    assert [w.text for w in words] == ["hello", "world", "manual", "caption", "line"]
    assert words[0].start == 1.0 and words[1].start == 1.6
    assert words[2].start == 4.0 and abs(words[4].end - 6.0) < 1e-6


def test_vtt_strips_tags_and_rolling_duplicates(tmp_path):
    path = tmp_path / "source.en.vtt"
    path.write_text(
        "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\n<c>first</c> line\n\n"
        "00:00:03.000 --> 00:00:05.000\nfirst line\nsecond line\n"
    )
    words = transcript.parse_vtt(path)
    assert [w.text for w in words] == ["first", "line", "second", "line"]
    assert words[0].start == 1.0 and words[2].start == 3.0


def test_lines_break_on_gaps_and_sentence_ends():
    words = [Word(0, 0.4, "Look."), Word(0.5, 0.9, "there"), Word(3.0, 3.4, "later")]
    assert [text for _, _, text in transcript.to_lines(words)] == ["Look.", "there", "later"]
