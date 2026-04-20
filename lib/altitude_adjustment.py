"""
標高補正モジュール

Péronnet, Thibault & Cousineau (1991) の理論モデルに基づき、
平均標高（海抜 m）がマラソンパフォーマンスに与える影響を計算します。

参考文献:
  Péronnet, F., Thibault, G., & Cousineau, D.L. (1991).
  A theoretical analysis of the effect of altitude on running performance.
  Journal of Applied Physiology, 70(1), 399-404.
  PubMed: https://pubmed.ncbi.nlm.nih.gov/2010398/
"""

from typing import Optional

# ============================================================
# 開発者オプション（デフォルト値）
#   ALTITUDE_CORRECTION_ENABLED : 補正エンジン全体の緊急キルスイッチ（UI非露出）
#   ALTITUDE_THRESHOLD_M        : 補正発動の最低標高。app.py の ?dev=true UI
#                                 スライダーから実行時に上書き可能（デフォルト 500m）。
# ============================================================
ALTITUDE_CORRECTION_ENABLED = True   # 緊急キルスイッチ: False にすると全補正無効
ALTITUDE_THRESHOLD_M = 500           # デフォルト閾値: これ以下の平均標高は補正係数 1.0
# ============================================================


def _aerobic_power_fraction(altitude_km: float) -> float:
    """Péronnet (1991) ポリノミアル: 海抜ゼロ時の有酸素パワーに対する比率 (0〜1.0)

    論文から導出された三次多項式:
      % Aerobic Power = 0.178*(km)^3 - 1.43*(km)^2 - 4.07*(km) + 100

    出典: Péronnet et al. (1991), 及び検証式の二次引用:
      joshuacassinatmd.com/tools/altitude-conversion-category
    """
    pct = 0.178 * altitude_km ** 3 - 1.43 * altitude_km ** 2 - 4.07 * altitude_km + 100
    # 安全クリップ: 極高度での計算誤差を防ぐ（実際のマラソンでは発生しない範囲）
    pct = max(10.0, min(100.0, pct))
    return pct / 100.0


def adjust_marathon_time(
    base_time_min: float,
    mean_altitude_m: float,
    threshold_m: Optional[float] = None,
) -> float:
    """標高補正後のマラソンタイムを返す（乗算補正）

    有酸素パワーが altitude に応じて低下するため、同じ走力で走ると
    低地より時間がかかる。補正後タイムは base_time_min 以上になる。

    ALTITUDE_CORRECTION_ENABLED = False の場合は常に base_time_min を返す。
    mean_altitude_m が有効閾値以下の場合も補正なし。

    Args:
        base_time_min: 海面水準での目標タイム（分）
        mean_altitude_m: コースの平均標高（海抜 m、GPXから算出）
        threshold_m: 補正発動の最低標高（省略時は ALTITUDE_THRESHOLD_M を使用）

    Returns:
        標高補正後のタイム（分）

    Examples:
        >>> adjust_marathon_time(180, 0)    # 海面
        180.0
        >>> adjust_marathon_time(180, 400)  # 閾値未満 → 補正なし
        180.0
        >>> round(adjust_marathon_time(180, 1000), 1)  # 1000m
        191.0
    """
    effective_threshold = threshold_m if threshold_m is not None else ALTITUDE_THRESHOLD_M
    if not ALTITUDE_CORRECTION_ENABLED or mean_altitude_m <= effective_threshold:
        return float(base_time_min)

    altitude_km = mean_altitude_m / 1000.0
    power_fraction = _aerobic_power_fraction(altitude_km)
    return base_time_min / power_fraction


def get_delay_minutes(
    base_time_min: float,
    mean_altitude_m: float,
    threshold_m: Optional[float] = None,
) -> float:
    """標高による遅延時間（分）を返す

    Args:
        base_time_min: 海面水準での目標タイム（分）
        mean_altitude_m: コースの平均標高（海抜 m）
        threshold_m: 補正発動の最低標高（省略時は ALTITUDE_THRESHOLD_M を使用）

    Returns:
        遅延時間（分）。閾値以下または機能無効の場合は 0.0

    Examples:
        >>> get_delay_minutes(180, 0)
        0.0
        >>> round(get_delay_minutes(180, 1000), 1)
        11.0
    """
    return adjust_marathon_time(base_time_min, mean_altitude_m, threshold_m) - float(base_time_min)


def get_altitude_warning(mean_altitude_m: float) -> Optional[str]:
    """平均標高に応じた注意メッセージを返す

    Args:
        mean_altitude_m: コースの平均標高（海抜 m）

    Returns:
        注意メッセージ（不要な場合は None）
    """
    if not ALTITUDE_CORRECTION_ENABLED:
        return None
    if mean_altitude_m >= 2500:
        return "⚠️ 高高度レース：高山病対策と十分な高地順化（最低 2〜3 週間）が推奨されます。"
    elif mean_altitude_m >= 1500:
        return "⚠️ 高地レース：高地トレーニング未経験の場合、実際の遅延はシミュレーション値より大きくなる可能性があります。"
    return None
