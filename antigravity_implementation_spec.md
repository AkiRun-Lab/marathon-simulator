# マラソン攻略シミュレーター 気温パラメータ実装指示書

**for Google Antigravity**

作成日: 2026年1月28日

---

## 1. 実装概要

### 1.1 目的

マラソン攻略シミュレーターに気温パラメータを追加し、レース当日の気温条件に基づいて目標タイムを自動調整する機能を実装する。

### 1.2 背景・根拠

本実装は以下の学術研究に基づく：

- Ely et al. (2007) Medicine & Science in Sports & Exercise
- El Helou et al. (2012) PLOS ONE（約180万人のデータ分析）
- Racinais et al. (2022) Medicine & Science in Sports & Exercise

### 1.3 技術スタック

- フレームワーク: Streamlit
- 言語: Python 3.10+
- 既存アプリ: AI Marathon Coach（VDOTベースのトレーニングプラン生成）

---

## 2. 数式仕様

### 2.1 コア計算式

```
adjusted_time = base_time × [1 + 0.0001 × h^3.6 × max(0, T - 10)]
```

> 決定係数 R² = 0.84（研究データとの適合度）

### 2.2 変数定義

| 変数 | 説明 | 単位・範囲 |
|------|------|-----------|
| `base_time` | 最適条件（10°C）での目標タイム | 分（120〜360） |
| `h` | base_time / 60（時間単位） | 時間（2.0〜6.0） |
| `T` | レース当日の気温 | °C（0〜35） |
| `adjusted_time` | 気温調整後の予測タイム | 分 |

### 2.3 定数パラメータ

| パラメータ | 値 | 説明 |
|-----------|-----|------|
| 最適気温 | 10°C | この気温以下では調整なし |
| 係数 a | 0.0001 | 回帰分析で導出 |
| べき指数 b | 3.6 | 走力による感受性差を表現 |

---

## 3. 実装コード

### 3.1 コア関数

```python
def adjust_marathon_time(base_time_min: float, temperature: float) -> float:
    """
    気温によるマラソンタイム調整
    
    Args:
        base_time_min: 最適条件での目標タイム（分）
        temperature: レース当日の気温（°C）
    
    Returns:
        調整後のタイム（分）
    """
    OPTIMAL_TEMP = 10.0  # 最適気温（°C）
    COEFFICIENT = 0.0001  # 係数
    EXPONENT = 3.6  # べき指数
    
    h = base_time_min / 60  # 時間単位に変換
    delta_t = max(0, temperature - OPTIMAL_TEMP)
    adjustment_factor = 1 + COEFFICIENT * (h ** EXPONENT) * delta_t
    
    return base_time_min * adjustment_factor
```

### 3.2 ユーティリティ関数

```python
def format_time(minutes: float) -> str:
    """分を H:MM:SS 形式に変換"""
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    secs = int((minutes % 1) * 60)
    return f"{hours}:{mins:02d}:{secs:02d}"


def get_delay_minutes(base_time_min: float, temperature: float) -> float:
    """気温による遅延時間（分）を計算"""
    adjusted = adjust_marathon_time(base_time_min, temperature)
    return adjusted - base_time_min


def get_adjusted_pace_per_km(base_time_min: float, temperature: float) -> str:
    """調整後の1kmあたりペースを計算"""
    adjusted = adjust_marathon_time(base_time_min, temperature)
    pace_min = adjusted / 42.195
    mins = int(pace_min)
    secs = int((pace_min % 1) * 60)
    return f"{mins}:{secs:02d}/km"
```

### 3.3 Streamlit UI実装例

```python
import streamlit as st

st.header("🌡️ 気温によるタイム調整")

# 入力
col1, col2 = st.columns(2)

with col1:
    target_hours = st.number_input("目標タイム（時間）", 2, 6, 3)
    target_minutes = st.number_input("目標タイム（分）", 0, 59, 30)

with col2:
    temperature = st.slider("レース当日の気温（°C）", 0, 35, 15)

# 計算
base_time_min = target_hours * 60 + target_minutes
adjusted_time = adjust_marathon_time(base_time_min, temperature)
delay = get_delay_minutes(base_time_min, temperature)

# 出力
st.metric(
    label="調整後タイム",
    value=format_time(adjusted_time),
    delta=f"+{delay:.1f}分" if delay > 0 else "調整なし"
)

st.write(f"**調整後ペース:** {get_adjusted_pace_per_km(base_time_min, temperature)}")

# 警告表示
if temperature >= 30:
    st.error("🚨 危険：レース中止を検討してください")
elif temperature >= 28:
    st.error("⚠️ 危険：熱中症リスクが非常に高いです")
elif temperature >= 25:
    st.warning("⚠️ 高温注意：こまめな給水と無理のないペース配分を")
```

---

## 4. UI仕様

### 4.1 入力コンポーネント

| 項目 | コンポーネント | 範囲 | デフォルト |
|------|---------------|------|-----------|
| レース気温 | `st.slider` | 0〜35°C | 15°C |
| 目標タイム（時間） | `st.number_input` | 2〜6 | 3 |
| 目標タイム（分） | `st.number_input` | 0〜59 | 30 |

### 4.2 出力表示

| 項目 | 表示形式 | コンポーネント |
|------|---------|---------------|
| 調整後タイム | H:MM:SS | `st.metric`（大きく表示） |
| 遅延時間 | +MM:SS | `st.metric`のdelta |
| 調整後ペース | MM:SS/km | テキスト表示 |
| 警告メッセージ | 条件付き | `st.warning` / `st.error` |

### 4.3 視覚化（オプション）

```python
import matplotlib.pyplot as plt
import numpy as np

def plot_temperature_impact(base_time_min: float):
    """気温とタイムの関係グラフを描画"""
    temps = np.linspace(5, 35, 100)
    times = [adjust_marathon_time(base_time_min, t) for t in temps]
    
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(temps, times, 'b-', linewidth=2)
    ax.axvline(x=10, color='green', linestyle='--', label='最適気温')
    ax.axvspan(25, 35, alpha=0.2, color='red', label='高温ゾーン')
    ax.set_xlabel('気温 (°C)')
    ax.set_ylabel('予測タイム (分)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    return fig

# Streamlitで表示
st.pyplot(plot_temperature_impact(base_time_min))
```

---

## 5. テストケース

### 5.1 単体テスト

| # | 目標タイム | 気温 | 期待結果 | 遅延 |
|---|-----------|------|---------|------|
| 1 | 3:00:00 (180分) | 10°C | 3:00:00 | +0:00（調整なし） |
| 2 | 3:00:00 (180分) | 20°C | ≈3:09:13 | +9〜10分 |
| 3 | 3:00:00 (180分) | 25°C | ≈3:13:50 | +13〜14分 |
| 4 | 4:00:00 (240分) | 20°C | ≈4:34:26 | +34〜35分 |
| 5 | 2:30:00 (150分) | 20°C | ≈2:34:00 | +4分 |

### 5.2 境界値テスト

| # | テスト条件 | 期待動作 |
|---|-----------|---------|
| 1 | 気温 0°C | 調整なし（最適気温以下） |
| 2 | 気温 10°C | 調整なし（最適気温ちょうど） |
| 3 | 気温 10.1°C | わずかな調整が発生 |
| 4 | 目標タイム 2:00:00 | 低下率最小 |
| 5 | 目標タイム 6:00:00 | 低下率最大 |

### 5.3 テストコード

```python
import pytest

def test_no_adjustment_at_optimal_temp():
    """最適気温では調整なし"""
    result = adjust_marathon_time(180, 10)
    assert result == 180

def test_no_adjustment_below_optimal():
    """最適気温以下では調整なし"""
    result = adjust_marathon_time(180, 5)
    assert result == 180

def test_adjustment_at_20c():
    """20°Cでの調整値"""
    result = adjust_marathon_time(180, 20)
    assert 189 <= result <= 190  # 約9-10分増

def test_slower_runners_more_affected():
    """遅いランナーほど影響が大きい"""
    fast = adjust_marathon_time(150, 20) - 150
    slow = adjust_marathon_time(240, 20) - 240
    assert slow > fast * 2  # 遅いランナーは2倍以上の影響
```

---

## 6. 注意事項・制限

### 6.1 モデルの限界

| 制限事項 | 説明 |
|---------|------|
| 個人差 | 暑さへの耐性、暑熱順化状態は考慮されない |
| 湿度 | 本モデルでは直接考慮されない（18°C以上では湿度の影響が増大） |
| データ範囲 | 研究データは主にサブ3:00以上。それより遅いランナーは外挿値 |
| 低温 | 10°C未満でのパフォーマンス低下は考慮されない |

### 6.2 ユーザーへの表示推奨

以下の免責文言をUIに表示すること：

> ⚠️ この調整値は学術研究に基づく統計的推定です。個人差や当日のコンディションにより実際のタイムは異なる場合があります。

### 6.3 熱中症警告閾値

| 気温 | 警告レベル | 表示メッセージ |
|------|-----------|---------------|
| 25°C以上 | 注意 | 「高温注意：こまめな給水を」 |
| 28°C以上 | 危険 | 「危険：熱中症リスクが高いです」 |
| 30°C以上 | 極めて危険 | 「レース中止を検討してください」 |

---

## 7. 気温別調整タイム早見表

実装後の検証用参照データ：

| 目標タイム | 10°C | 15°C | 20°C | 25°C | 30°C |
|-----------|------|------|------|------|------|
| 2:30 | 2:30 | 2:32 | 2:34 | 2:36 | 2:38 |
| 3:00 | 3:00 | 3:04 | 3:09 | 3:13 | 3:18 |
| 3:30 | 3:30 | 3:39 | 3:48 | 3:58 | 4:07 |
| 4:00 | 4:00 | 4:17 | 4:34 | 4:51 | 5:08 |
| 4:30 | 4:30 | 4:59 | 5:29 | 5:58 | 6:28 |
| 5:00 | 5:00 | 5:47 | 6:35 | 7:23 | 8:11 |

---

## 8. 参考資料

1. Ely MR et al. (2007) Impact of weather on marathon-running performance. *Med Sci Sports Exerc.* 39(3):487-493
2. El Helou N et al. (2012) Impact of Environmental Parameters on Marathon Running Performance. *PLoS ONE* 7(5):e37407
3. Racinais S et al. (2022) Effects of Weather Parameters on Endurance Running Performance. *Med Sci Sports Exerc.* 54(1):153-162

### 添付ファイル

- `marathon_temperature_research_report.docx` - 詳細調査報告書
- `temperature_formula_analysis.png` - 数式導出グラフ

---

## 9. 実装チェックリスト

- [ ] コア関数 `adjust_marathon_time()` の実装
- [ ] ユーティリティ関数の実装
- [ ] Streamlit UIの実装
- [ ] 気温スライダーの追加
- [ ] 調整タイム表示の実装
- [ ] 警告メッセージの実装
- [ ] 視覚化グラフの実装（オプション）
- [ ] 単体テストの実行
- [ ] 境界値テストの実行
- [ ] 免責文言の表示
- [ ] ドキュメント更新

---

*End of Document*
