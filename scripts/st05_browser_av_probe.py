#!/usr/bin/env python3
"""ST05 synthetic-only Chromium X11 screen and browser-originated audio proof.

No URL, cookies, school content, system login, persistent profile, or network.
Audio is captured from an in-page HTML5 media element using Web Audio and
MediaRecorder, NOT from the host operating system's audio output.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

from cvoc_media_evidence import summarize, validate

MAX_BYTES = 50_000_000


def shell(*args, timeout=90):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                          check=True)


def source_clip(path):
    shell('ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin', '-y',
          '-f', 'lavfi', '-i', 'testsrc2=size=480x270:rate=15',
          '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000',
          '-t', '5', '-c:v', 'libvpx', '-b:v', '550k',
          '-deadline', 'realtime', '-cpu-used', '6', '-c:a', 'libopus',
          '-b:a', '80k', str(path))
    if not (20_000 < path.stat().st_size < 1_500_000):
        raise AssertionError('Synthetic source size out of bounds')


def html(data_uri):
    if not data_uri.startswith('data:video/webm;base64,'):
        raise ValueError('Synthetic in-memory WebM required')
    return '''<!doctype html><html><head><meta charset="utf-8">
    <title>ST05 Synthetic Screen+Audio Probe</title><style>
    body{background:#132238;color:#fff;font:18px sans-serif;text-align:center;margin:0}
    h3{margin:8px}video{width:780px;height:405px;background:#000}
    button{font-size:18px;padding:7px 18px}
    </style></head><body><h3>ST05 - Synthetic Browser Media Only</h3>
    <video id="synthetic" preload="auto" playsinline src="''' + data_uri + '''"></video>
    <div><button id="start">Start original test</button>
    <span id="clock">0.0</span></div><script>
    window.__recError=null;window.__audioB64=null;window.__recStarted=false;
    const video=document.querySelector('#synthetic');
    document.querySelector('#start').onclick=async()=>{
      try {
        const context=new AudioContext();
        const media=context.createMediaElementSource(video);
        const audioDestination=context.createMediaStreamDestination();
        media.connect(audioDestination);
        if (!MediaRecorder.isTypeSupported('audio/webm;codecs=opus'))
          throw Error('No browser Opus encoder');
        const recorder=new MediaRecorder(audioDestination.stream,
            {mimeType:'audio/webm;codecs=opus'});
        const chunks=[];
        recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data)};
        recorder.onerror=e=>{window.__recError=String(e.error||e)};
        recorder.onstop=async()=>{
          try {
            const blob=new Blob(chunks,{type:'audio/webm'});
            if(blob.size<2000 || blob.size>500000)
              throw Error('Audio WebM size unexpected: '+blob.size);
            const reader=new FileReader();
            reader.onload=()=>{window.__audioB64=reader.result.split(',')[1]};
            reader.onerror=()=>{window.__recError='FileReader failure'};
            reader.readAsDataURL(blob);
          }catch(e){window.__recError=String(e)}
        };
        video.onended=()=>{if(recorder.state==='recording')recorder.stop()};
        await context.resume();recorder.start(250);
        window.__recStarted=true;
        await video.play();
      }catch(e){window.__recError=String(e)}
    };
    setInterval(()=>document.querySelector('#clock').textContent=video.currentTime.toFixed(1),100);
    </script></body></html>'''


def x11(display):
    if not display.startswith(':') or '\n' in display or '\r' in display:
        raise ValueError('Expected Xvfb DISPLAY environment variable')
    return display + '+0,0'


def capture(output, *, chrome_path=None):
    from playwright.sync_api import sync_playwright
    display=os.environ.get('DISPLAY')
    if not display:
        raise RuntimeError('ST05 requires an existing Xvfb display; no headless fallback')
    output=Path(output).resolve()
    if output.exists():
        raise FileExistsError('Refusing to overwrite ST05 output')
    output.parent.mkdir(parents=True, exist_ok=True)
    browser_exe=chrome_path or shutil.which('google-chrome') or shutil.which('chromium')
    if not browser_exe or not Path(browser_exe).exists():
        raise RuntimeError('No local Chromium or Chrome binary; external downloads disabled')
    with tempfile.TemporaryDirectory(prefix='st05-original-') as td:
        tmp=Path(td)
        sample=tmp/'original.webm';source_clip(sample)
        uri='data:video/webm;base64,'+base64.b64encode(sample.read_bytes()).decode('ascii')
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=browser_exe,headless=False,
                args=['--no-sandbox','--disable-dev-shm-usage',
                      '--disable-background-networking','--no-first-run',
                      '--autoplay-policy=no-user-gesture-required',
                      '--window-position=0,0','--window-size=960,540'])
            try:
                page=browser.new_page(viewport={'width':900,'height':490})
                page.set_content(html(uri),wait_until='load')
                page.wait_for_function('document.querySelector("video").readyState >= 2',timeout=15000)
                # X11: actual visual desktop capture; no screenshot stand-in.
                screen=tmp/'screen.mp4'
                ffmpeg=subprocess.Popen([
                    'ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y',
                    '-f','x11grab','-framerate','15','-video_size','960x540',
                    '-i',x11(display),'-t','7','-c:v','libx264','-preset','ultrafast',
                    '-crf','27','-pix_fmt','yuv420p',str(screen)],
                    stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
                started=time.monotonic()
                time.sleep(0.7)
                click_offset=time.monotonic()-started
                page.locator('#start').click()
                page.wait_for_function('window.__audioB64 || window.__recError',timeout=18000)
                error=page.evaluate('window.__recError')
                if error:
                    raise RuntimeError('Browser audio capture failed: '+error)
                raw_audio=base64.b64decode(page.evaluate('window.__audioB64'),validate=True)
                if not 2000<len(raw_audio)<500_000:
                    raise AssertionError('Invalid browser-recorded audio payload')
                (tmp/'browser_audio.webm').write_bytes(raw_audio)
                _, screen_err=ffmpeg.communicate(timeout=18)
                if ffmpeg.returncode:
                    raise RuntimeError('X11 screen capture failed: '+screen_err.decode(errors='replace')[-1600:])
            finally:
                browser.close()
        if screen.stat().st_size<30000:
            raise AssertionError('Empty X11 capture')
        # Browser-recorded Opus is the sole audio input, NOT an FFmpeg synthetic tone.
        shell('ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y',
              '-i',str(screen),'-itsoffset',str(round(click_offset,3)),
              '-i',str(tmp/'browser_audio.webm'),
              '-map','0:v:0','-map','1:a:0','-c:v','copy',
              '-c:a','aac','-b:a','96k','-movflags','+faststart',str(output))
        evidence=summarize(output)
        validate(evidence,output)
        if not evidence['technical_checks_passed'] or evidence['streams']!=['audio','video']:
            raise AssertionError('Media validation failed')
        report={
            'protocol':'schumann-st05-synthetic-browser-av-v0',
            'test_type':'xvfb_screen_plus_browser_mediarecorder_audio',
            'school_login_attempted':False,
            'university_course_recorded':False,
            'os_audio_monitor_verified':False,
            'cvoc_native_verified':False,
            'technical_evidence':evidence,
        }
        result=output.parent/'st05_report.json'
        if result.exists():raise FileExistsError('Refusing to overwrite report')
        result.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        print('ST05_BROWSER_AUDIO_VIDEO_PASS',evidence['input_digest_sha256'])
        return result


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--output-dir',type=Path,default=Path('artifacts/st05_synthetic'))
    args=a.parse_args()
    capture(args.output_dir/'st05_capture.mp4')
