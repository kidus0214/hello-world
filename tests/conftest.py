import subprocess

import pytest

from clipforge import config


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CLIPFORGE_CONFIG", raising=False)
    monkeypatch.setattr(config.Path, "home", lambda: tmp_path / "home")
    cfg = config.load()
    cfg["clips"].update(count=2, min_seconds=4, max_seconds=8)
    return cfg


@pytest.fixture(scope="session")
def sample_video(tmp_path_factory):
    """30s landscape clip: quiet tone, with a loud noise burst from 12s to 20s."""
    path = tmp_path_factory.mktemp("media") / "sample.mp4"
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "testsrc2=s=640x360:r=30:d=30",
        "-f", "lavfi", "-i", "sine=f=220:d=30",
        "-f", "lavfi", "-i", "anoisesrc=d=30:c=pink:a=0.6",
        "-filter_complex",
        "[1:a]volume=0.05[s];[2:a]volume='if(between(t,12,20),1,0)':eval=frame[n];"
        "[s][n]amix=inputs=2:normalize=0[a]",
        "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac",
        str(path),
    ], check=True)
    (path.with_suffix(".vtt")).write_text(
        "WEBVTT\n\n00:00:12.000 --> 00:00:16.000\nwatch this jump right here\n\n"
        "00:00:16.000 --> 00:00:20.000\nno way he cleared the bridge\n"
    )
    return path
