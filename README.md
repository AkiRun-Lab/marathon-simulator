# Ehime Marathon Pace Simulator

愛媛マラソンのコース特性（勾配、風）を考慮した、等パワー（Constant Effort）戦略によるペースシミュレーターです。

## 特徴
- **コースデータ**: 平田の坂や海岸線などの主要な地形変動を考慮。
- **物理モデル**: 勾配（Minettiの式）と空気抵抗を考慮した物理ベースのペース計算。
- **カスタマイズ**: VDOTや目標タイム、当日の気象条件（風速・風向・気温）に合わせてシミュレーション可能。

## インストールと実行
```bash
pip install -r requirements.txt
python3 -m streamlit run app.py
```
