# 開発用スクリプト

物理モデル・データの手動確認用スクリプト。本番アプリからは使用しない。

アプリルート（`apps/mss/`）から `-m` 付きで実行する（`lib/` をimportするため）：

```bash
python3 -m scripts.debug_data
python3 -m scripts.debug_simulation
python3 -m scripts.verify_physics
python3 -m scripts.verify_wind_impact
```
