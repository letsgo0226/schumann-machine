# CVOC × 舒曼機：合成錄影技術證據轉接器（候選版）

**用途與目前狀態**：這是 `letsgo0226/schumann-machine` 草稿 PR #1 的從屬擴充，用於合成影片的**唯讀**本地分析與報告生成。它沒有登入學校、開啟受限影片、遠端控制 Windows/macOS、部署雲端主機或驗證課程授權的能力。

## 與 CVOC-ST02 的關係

CVOC-ST02 的 `verify_manifest` 目前只允許 `st30-tape`、`st38-sk-ledger`、`st43-pocket`、`st44-continuity`、`st47-state`。**它不接受這份影音報告**。因此，本原型採用獨立的 `schumann-cvoc-external-media-v0` 型別，拒絕未知欄位、篡改、權限升級宣稱及錯誤影音內容。

後續只有在 M45 主系統獨立審查、明確定義新的影音算子型別與驗證語義之後，才能將其納入 CVOC 正式介面。不要將 `technical_checks_passed=true` 誤讀為已通過 CVOC-ST02 原生驗證、登入成功或錄製授權。

## 本階段的驗證內容

1. 輸入只接受本機一般 `.mp4` 檔，不接受符號連結、URL 或遠端播放來源。
2. 對象需落在 20,000 至 50,000,000 bytes，時長 2–20 秒，且恰有一個音軌與一個影軌。
3. 使用 `ffprobe` 讀取時長及軌道；以 `volumedetect` 檢測最大音量（不得低於 -55 dBFS）；對第 1 秒的抽樣畫面做亮度變異檢查（拒絕幾乎全黑／均勻畫面）。這是**技術抽樣**，不是逐幀品質保證。
4. 計算 MP4 SHA-256。獨立 `verify` 重新解析媒體並比對整份報告；不是數位簽章，也不能證明上游檔案來歷。
5. 固定 `source_verified=false`、`cvoc_st02_native_verified=false`、`cross_component_verified=false`、`course_authorized=false`，杜絕將合成技術檢查提升為登入／授權宣稱。
6. 不儲存、列印或上傳任何學校登入憑證、Cookie、私人課程影片或 Stream URL。

## 本機測試（需 ffmpeg／ffprobe）

```bash
python3 -m unittest discover -s scripts -p 'test_cvoc_media_evidence.py' -v
```

在合成測試錄影成功後，才可對該 MP4 執行：

```bash
python3 scripts/cvoc_media_evidence.py generate artifacts/vm_synthetic_capture.mp4 artifacts/vm_synthetic_evidence.json
python3 scripts/cvoc_media_evidence.py verify artifacts/vm_synthetic_capture.mp4 artifacts/vm_synthetic_evidence.json
```

在 GitHub Actions 的合成影片工作流程中，只有產生並驗證完整報告後才上傳 Artifact，保留一日。**不執行**真實課程錄製；工作流程為手動觸發，需審查後才可合併與啟動。

## 合成影音報告型別

```text
protocol: schumann-cvoc-external-media-v0
component: video.synthetic.capture
operator_type: LocalSyntheticMP4 -> UnverifiedMediaEvidence
authorization: read-only
media_bytes / duration_seconds / audio_max_dbfs / video_luma_stdev / input_digest_sha256
technical_checks_passed: true
source_verified: false
cvoc_st02_native_verified: false
cross_component_verified: false
course_authorized: false
```

合成證據已能在單一工作中驗證，但**尚未**與 M45 CVOC-ST02 原生驗證器完成跨倉庫整合，也尚未在 GitHub Runner 執行完整影音測試。

本變更應以**獨立草稿 PR**對準舒曼機 PR #1 的分支進行審查；不直接更動 M45/CVOC 主系統、不合併、不安排自動續跑、不啟動付費資源。
