#!/usr/bin/env python3
"""Synthetic-only virtual desktop capture probe.

Creates an original 7-second test video with a tone, opens it in temporary
Chromium under Xvfb, records the display and PulseAudio sink to MP4.
No URLs, course content, passwords, tokens, cookies, or sign-in are accepted.
"""
import argparse
import base64
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

def run(*cmd, timeout=45):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=timeout)

def build_sample(folder):
    run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "testsrc2=size=720x360:rate=20",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000",
        "-t", "7", "-c:v", "libvpx", "-deadline", "realtime", "-cpu-used", "6",
        "-b:v", "400k", "-c:a", "libopus", "-b:a", "64k",
        str(folder / "sample.webm"), timeout=90)
    (folder / "index.html").write_text("""<!DOCTYPE html><html lang="en"><meta charset="utf-8">
<title>Synthetic VM capture — not a course video</title>
<style>body{background:#101d2e;color:#fff;text-align:center;font:22px sans-serif;margin:0}
h2{margin:10px}video{width:760px;height:385px;background:#000}
button{padding:9px 20px;font-size:20px}small{font-size:13px}</style>
<h2>Schumann Actions VM — Synthetic test only</h2>
<video id="clip" preload="auto" src="sample.webm" playsinline></video>
<div><button id="start">Play demo with audio</button> <span id="clock">0.0 s</span></div>
<small>Generated test pattern; no school videos, logins or personal data.</small>
<script>
let v=document.getElementById('clip');
document.getElementById('start').onclick=()=>v.play();
setInterval(()=>document.getElementById('clock').textContent=v.currentTime.toFixed(1)+' s',100);
</script></html>""", encoding="utf-8")

def probe(output, video_only=False, chrome_path=None):
    if not os.getenv("DISPLAY"):
        raise RuntimeError("DISPLAY missing: run via xvfb-run")
    from playwright.sync_api import sync_playwright
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="schumann-vm-") as tmp:
        folder=Path(tmp)
        build_sample(folder)
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(
                executable_path=chrome_path or shutil.which("google-chrome") or shutil.which("chromium"),
                headless=False,
                args=["--no-sandbox","--disable-dev-shm-usage",
                      "--autoplay-policy=no-user-gesture-required",
                      "--window-position=0,0","--window-size=960,540"])
            try:
                page=browser.new_page(viewport={"width":900,"height":490})
                html = (folder / "index.html").read_text(encoding="utf-8")
                media = base64.b64encode((folder / "sample.webm").read_bytes()).decode("ascii")
                html = html.replace('src="sample.webm"', f'src="data:video/webm;base64,{media}"')
                page.set_content(html, wait_until="load")
                page.wait_for_function("document.querySelector('video').readyState >= 2", timeout=15000)
                command=["ffmpeg","-hide_banner","-loglevel","error","-y",
                         "-thread_queue_size","1024","-f","x11grab",
                         "-video_size","960x540","-framerate","15",
                         "-i",os.environ["DISPLAY"]+"+0,0"]
                if not video_only:
                    command+=["-thread_queue_size","1024","-f","pulse","-i","schumann.monitor"]
                command+=["-t","9","-c:v","libx264","-preset","ultrafast",
                          "-crf","27","-pix_fmt","yuv420p"]
                if not video_only:
                    command+=["-c:a","aac","-b:a","96k"]
                command+=[str(output)]
                proc=subprocess.Popen(command, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, text=True)
                time.sleep(.8)
                page.locator("#start").click()
                page.wait_for_function("document.querySelector('video').ended",timeout=22000)
                try:
                    _,error=proc.communicate(timeout=20)
                except subprocess.TimeoutExpired:
                    proc.kill(); proc.communicate()
                    raise RuntimeError("FFmpeg timed out")
                if proc.returncode:
                    raise RuntimeError("FFmpeg failed: "+error[-1200:])
            finally:
                browser.close()
    streams=run("ffprobe","-v","error","-show_entries","stream=codec_type",
                "-of","csv=p=0",str(output)).stdout.splitlines()
    if "video" not in streams or (not video_only and "audio" not in streams):
        raise AssertionError("Missing MP4 stream: "+repr(streams))
    if output.stat().st_size < 20000:
        raise AssertionError("Output is unexpectedly small")
    if not video_only:
        volume=subprocess.run(["ffmpeg","-hide_banner","-i",str(output),
                              "-af","volumedetect","-f","null","-"],
                              capture_output=True,text=True,timeout=35)
        m=re.search(r"max_volume:\s*(-?[\d.]+) dB",volume.stderr)
        if not m or float(m.group(1)) < -55:
            raise AssertionError("Synthetic tone missing or silent")
        print("AUDIO_MAX_DB",m.group(1))
    print("VM_SYNTHETIC_PROBE_PASS",str(output),
          "bytes",output.stat().st_size,
          "sha256",hashlib.sha256(output.read_bytes()).hexdigest())

if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,default=Path("artifacts/vm_synthetic_capture.mp4"))
    p.add_argument("--video-only",action="store_true")
    p.add_argument("--chrome-path")
    args=p.parse_args()
    probe(args.output.resolve(),args.video_only,args.chrome_path)
