# Schumann ST05 — 雲端虛擬瀏覽器影音錄製（原創合成媒體限定）

本研究原型使用 GitHub Actions 的短暫 Ubuntu Runner，配合系統預裝的 Xvfb / Google Chrome、Playwright、固定版本且經 SHA-256 驗證的 FFmpeg/FFprobe，實作 **X11 虛擬桌面畫面錄製 + HTML5 原創影片之瀏覽器內音訊錄製 + FFmpeg 合成 MP4**。

這是 **ST05 技術候選版**，與主倉庫的 CVOC-ST02/03/04 以及舒曼機 PR #1～#3 完全分離，並非完成的虛擬算子電腦。

## 何者實際被錄製？

1. FFmpeg 在 Runner 當地產生長度 5 秒的原創測試圖樣以及 440 Hz 音訊，存為 WebM。
2. 將 WebM 作為 `data:video/webm;base64,...` 嵌入 `page.set_content`，不向外部網站導覽，也不輸入 URL、登入或 Cookie。
3. Chromium 在 Xvfb 虛擬顯示器中播放該媒體。FFmpeg 的 `x11grab` 取自真實 X11 桌面畫面，**不是將原檔複製成完成作品**。
4. 使用 HTML5 `createMediaElementSource` + `MediaStreamAudioDestinationNode` + `MediaRecorder` 擷取**瀏覽器內正在播放的媒體音訊**為 Opus/WebM。這與系統 PulseAudio / PipeWire / BlackHole 監聽不同。
5. FFmpeg 將 X11 錄製畫面與瀏覽器錄製音軌合成 MP4；原本的 `cvoc_media_evidence.py` 再重新讀取 MP4，驗證時長、影音軌道、音量、非單色畫面和 SHA-256。
6. 報告中固定標記：`school_login_attempted=false`、`university_course_recorded=false`、`os_audio_monitor_verified=false`、`cvoc_native_verified=false`。

## 技術／授權界線

- **不會**登入 Microsoft 365、開啟 Microsoft Stream、下載受限影片、錄製真實課程、蒐集密碼／Cookie、處理 DRM 或跳過學校授權與 MFA。
- 這項音訊錄製僅驗證受控頁面內的 MediaRecorder 能力，不證明雲端可錄製任意串流網站的聲音。
- 不包含 OS 級 PulseAudio、麥克風、系統混音器驗證；若未來真的需要整個桌面的音訊監聽，必須另外驗證與審查。
- 沒有任意 URL／命令輸入，使用工作產生的暫存檔；不是一般用途的瀏覽器錄製工具。
- SHA-256 提供本地一致性，非來源認證。單點影像亮度與峰值音量無法證明全片品質或視聽同步精度。
- GitHub-hosted Runner 是一次性的虛擬電腦，工作結束即釋放；沒有永久登入的遠端桌面、排程、續跑、PR 合併或正式部署。
- 工作流程僅 `pull_request` 和手動 `workflow_dispatch`，`GITHUB_TOKEN` 為 `contents: read`，並保留原創測試 MP4／報告一天。沒有私人內容或付費服務設定。

## GitHub 測試

`.github/workflows/st05-synthetic-browser-av.yml` 執行：

- 取得與 PR #3 已驗證一致的固定版本 FFmpeg/FFprobe wheel，先比對其 SHA-256，再直接解壓原生執行檔，不執行套件的 Python 下載初始化程式碼；固定版本不代表其二進位安全已全面審核。
- 使用 `playwright==1.56.0`；需 Runner 預裝 Google Chrome/Chromium 與 Xvfb，不以無聲或截圖替代。
- 6 項 ST05 安全測試及原有 10 項影音防護測試，然後真的執行合成影片的 X11 + Browser MediaRecorder 錄製。
- 嚴格驗證成功才上傳原創影音與 JSON 報告。

## 本機重現

Linux 上需要 Chromium、Xvfb、Python Playwright 1.56.0、FFmpeg 和 FFprobe，並確認所在機器有權執行 X11 錄影：

```bash
python -m unittest discover -s scripts -p 'test_st05_contract.py' -v
xvfb-run -a -s '-screen 0 960x540x24 -ac' \
  python scripts/st05_browser_av_probe.py --output-dir artifacts/st05_synthetic
python scripts/cvoc_media_evidence.py generate \
  artifacts/st05_synthetic/st05_capture.mp4 artifacts/st05_synthetic/st05_media_evidence.json
python scripts/cvoc_media_evidence.py verify \
  artifacts/st05_synthetic/st05_capture.mp4 artifacts/st05_synthetic/st05_media_evidence.json
```

工作流程與其依賴的影音驗證器仍須獨立審查。ST05 PR 必須以舒曼機 PR #3 的分支為基底，**不得自行合併、正式部署或授權實際課程錄影**。
