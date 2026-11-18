# Schumann Actions VM — synthetic capture proof of concept

## What is implemented

The **manually triggered** workflow `.github/workflows/schumann-vm-demo.yml` requests an ephemeral GitHub-hosted Ubuntu 24.04 VM. It installs Xvfb, FFmpeg, PulseAudio and Playwright, then:

1. Generates a synthetic, original 7-second WebM test pattern with a 440 Hz sine tone.
2. Opens the test media in a visible Chromium browser window under Xvfb.
3. Captures the virtual screen and PulseAudio monitor with FFmpeg.
4. Validates MP4 video/audio tracks, recorded size, audio amplitude and SHA-256.
5. Uploads **only the synthetic demonstration clip** as a 1-day Actions artifact.

The workflow is `workflow_dispatch` **only**, has no schedule, no automatic actions against school services, and no production deployment. It should **not be merged or manually dispatched before review**. A newly pushed branch with this workflow does not automatically create a VM or begin recording.

## Important limitations

- **This does not record Microsoft Stream lectures.** A cloud runner is not your logged-in Mac. School SSO, MFA, conditional access, network rules and playback policy may prohibit successful cloud sign-in.
- The script accepts **no remote URL, session cookie, Microsoft token, password or other credential**. Never paste university credentials, Playwright storage states, protected stream URLs or private course video into this public repository, Actions inputs, artifacts or logs.
- Permission to view does not necessarily include permission to record in the cloud or redistribute. Verify with the instructor or institution before building a private authenticated recording integration.
- The test clip is an original synthetic source. Do not add private media uploads to this workflow. GitHub-hosted runner recording remains subject to **actual playback time**, so it cannot compress a two-hour lecture into five minutes without access to a properly authorized source download.
- Private GitHub repositories can incur Actions usage/storage charges depending on plan and quota. This existing repository is public, so it is only suitable for this synthetic probe.
- GitHub's hosted VM is **disposable**; output must be explicitly saved before the job ends.
- A self-hosted runner on your own Mac can orchestrate the *already authorized* local browser and BlackHole system, but it is **not a GitHub cloud virtual machine** and must be configured with strict workflow permissions.

## Manual review procedure

After independent code/security review and explicit approval, merge the PR. Go to repository **Actions → Schumann VM screen recording — synthetic demo only → Run workflow**. If it succeeds, download the short synthetic demonstration MP4 from the workflow's **Artifacts** section. No school data should be present.

## Offline check

With Linux Chromium, Playwright, ffmpeg and Xvfb installed, a **video-only** graphics check can be attempted:

```bash
xvfb-run -a -s '-screen 0 960x540x24 -ac' \
  python scripts/recording_vm_probe.py --video-only --output /tmp/vm_synthetic.mp4
```

The hosted workflow additionally probes PulseAudio. Container sandboxes may prevent Chromium navigation even to local `file://` media; this is an environment restriction and does not prove the hosted workflow succeeds.

**Status:** proposal and syntax-checked only; no GitHub-hosted execution or Microsoft Stream recording has been performed.
