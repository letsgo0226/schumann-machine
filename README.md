# 舒曼機 SAA-012 — Render Free Preview

這是 SAA-012 的**唯讀部署展示入口**，不是完整研究引擎。公開 HTTP `/` 與 `/health` 只回傳狀態資訊；沒有背景研究、資料庫、持久化磁碟或付費 API。

`python -m py_compile server.py` 可檢查語法，`python server.py` 可本地啟動。完整 SAA-012 研究程式尚未上傳至此儲存庫，不能聲稱已在雲端執行。

Render 方案明確設定 `free`、`autoDeploy: false`。在未確認帳單上限與免費額度前，**不應建立服務**。免費方案並非絕對零費用保證。

不修改「終極舒曼機」基準版本。
