"""Render a clip: cut, reframe to 9:16, burn in captions, normalise audio."""

from __future__ import annotations

import textwrap
from pathlib import Path

from . import media
from .transcript import Word

WIDTH, HEIGHT = 1080, 1920


def _ass_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{int(hours)}:{int(minutes):02d}:{secs:05.2f}"


def _ass_text(text: str) -> str:
    return text.replace("\\", "/").replace("{", "(").replace("}", ")").replace("\n", " ").strip()


def build_ass(clip: dict, words: list[Word], cfg: dict, credit: str = "") -> str:
    """ASS subtitle document with timings relative to the clip start."""
    font = cfg["clips"]["font"]
    start, end = clip["start"], clip["end"]
    length = end - start
    out = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {WIDTH}",
        f"PlayResY: {HEIGHT}",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Caption,{font},84,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,6,2,2,80,80,460,1",
        f"Style: Hook,{font},70,&H00FFFFFF,&H00FFFFFF,&H00000000,&HC8000000,-1,0,0,0,100,100,0,0,3,18,0,8,90,90,250,1",
        f"Style: Credit,{font},34,&H50FFFFFF,&H50FFFFFF,&H78000000,&H78000000,0,0,0,0,100,100,0,0,1,2,0,2,60,60,150,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    hook = _ass_text(clip.get("hook", ""))
    hook_len = min(float(cfg["clips"]["hook_seconds"]), length)
    if hook and hook_len > 0:
        wrapped = "\\N".join(textwrap.wrap(hook, 24)[:3])
        out.append(f"Dialogue: 2,{_ass_time(0)},{_ass_time(hook_len)},Hook,,0,0,0,,{wrapped}")

    if credit:
        out.append(f"Dialogue: 0,{_ass_time(0)},{_ass_time(length)},Credit,,0,0,0,,{_ass_text(credit)}")

    if cfg["clips"]["captions"]:
        inside = [w for w in words if w.end > start and w.start < end]
        for i in range(0, len(inside), 3):  # three words on screen, the spoken one highlighted
            chunk = inside[i:i + 3]
            for j, word in enumerate(chunk):
                w_start = max(word.start - start, 0.0)
                # hold the word until the next one starts, so lines never stack on screen
                w_end = word.end - start + 0.15
                if i + j + 1 < len(inside):
                    w_end = min(w_end, inside[i + j + 1].start - start) if j + 1 == len(chunk) \
                        else inside[i + j + 1].start - start
                w_end = min(w_end, length)
                if w_end <= w_start:
                    continue
                text = " ".join(
                    ("{\\c&H00F0FF&}" + _ass_text(w.text).upper() + "{\\c&HFFFFFF&}") if k == j
                    else _ass_text(w.text).upper()
                    for k, w in enumerate(chunk)
                )
                out.append(f"Dialogue: 1,{_ass_time(w_start)},{_ass_time(w_end)},Caption,,0,0,0,,{text}")
    return "\n".join(out) + "\n"


def video_filter(src_w: int, src_h: int, layout: str, ass_name: str | None) -> str:
    """Filter graph from [0:v] to [v]."""
    vertical = src_h / src_w >= 1.5
    if vertical or layout == "crop":
        chain = (f"[0:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
                 f"crop={WIDTH}:{HEIGHT},setsar=1[base]")
    else:
        chain = (
            f"[0:v]split=2[bgsrc][fgsrc];"
            f"[bgsrc]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT},boxblur=24:4,eq=brightness=-0.12[bg];"
            f"[fgsrc]scale={WIDTH}:-2[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[base]"
        )
    if ass_name:
        return chain + f";[base]ass={ass_name}[v]"
    return chain + ";[base]null[v]"


def render_clip(source: Path, clip: dict, words: list[Word], meta: dict, cfg: dict, out_dir: Path) -> dict:
    """Write <id>.mp4 and <id>.jpg into out_dir; return the file names."""
    out_dir.mkdir(parents=True, exist_ok=True)
    clip_id = clip["id"]
    length = clip["end"] - clip["start"]
    layout = clip.get("layout") or cfg["clips"]["layout"]

    ass_name = None
    notes = []
    if "ass" in media.ffmpeg_filters():
        credit = ""
        if cfg["clips"]["credit_source"] and meta.get("channel"):
            credit = f"via {meta['channel']}"
        ass_name = f"{clip_id}.ass"
        (out_dir / ass_name).write_text(build_ass(clip, words, cfg, credit), encoding="utf-8")
    else:
        notes.append("this ffmpeg build has no libass, so captions and hook text were skipped")

    video = f"{clip_id}.mp4"
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-ss", f"{clip['start']:.3f}", "-t", f"{length:.3f}", "-i", str(source),
        "-filter_complex", video_filter(meta["width"], meta["height"], layout, ass_name),
        "-map", "[v]",
    ]
    if meta.get("has_audio", True):
        cmd += ["-map", "0:a:0", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
                "-c:a", "aac", "-b:a", "160k", "-ar", "48000"]
    cmd += [
        "-r", str(min(round(meta.get("fps", 30)), 60) or 30),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", video,
    ]
    # run inside out_dir so the ass filter gets a bare file name (no path escaping needed)
    media.run(cmd, cwd=out_dir)

    thumb = f"{clip_id}.jpg"
    media.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-ss", f"{min(1.0, length / 2):.2f}", "-i", video, "-frames:v", "1", "-q:v", "3", thumb,
    ], cwd=out_dir)
    return {"file": video, "thumb": thumb, "notes": notes}
