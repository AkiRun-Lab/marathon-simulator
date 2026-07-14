"""
マラソンペース計算ツール（MPC） - CTA Selector
シミュレーション結果（気温・風・起伏・目標タイム）から、
Amazonカテゴリ別リストへの送客CTAカテゴリを判定する純粋関数群。

Streamlitに依存しない（importしない）。例外は投げない。
"""

# =============================================
# 判定しきい値（後から調整できるよう定数化）
# =============================================
HEAT_SEVERE_MIN_DELAY = 5.0     # 気温補正による遅延（分）：これ以上で「暑さ深刻」
HEAT_MODERATE_MIN_DELAY = 2.0   # 気温補正による遅延（分）：これ以上で「暑さ中程度」
WIND_MIN_SPEED_MS = 3.0         # 風速（m/s）：これ以上で「風」カテゴリ
HILLY_MIN_GAIN_M = 300.0        # 獲得標高（m）：これ以上で「起伏」カテゴリ
DAILY_TRAINER_MIN_TIME_SEC = 4 * 3600  # 目標タイム（秒）：これ以上でデイリートレーナー訴求


def _to_float_or_none(value):
    """floatへ変換できない場合はNoneを返す（例外を投げない）"""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def judge_cta_category(temp_delay_min, wind_speed_ms, elevation_gain_m, base_time_sec) -> str:
    """シミュレーション結果からAmazon CTAカテゴリを判定する

    優先順位（上から判定し、最初に条件を満たしたカテゴリを返す）：
        1. temp_delay_min >= HEAT_SEVERE_MIN_DELAY   -> "heat_severe"
        2. temp_delay_min >= HEAT_MODERATE_MIN_DELAY -> "heat_moderate"
        3. wind_speed_ms  >= WIND_MIN_SPEED_MS        -> "wind"
        4. elevation_gain_m >= HILLY_MIN_GAIN_M       -> "hilly"
        5. それ以外：base_time_sec >= DAILY_TRAINER_MIN_TIME_SEC なら "shoes_daily"、
           未満なら "shoes_race"

    Args:
        temp_delay_min: 気温補正による遅延（分）
        wind_speed_ms: 風速（m/s）
        elevation_gain_m: 獲得標高（m）
        base_time_sec: 目標タイム（補正前・秒）

    Returns:
        カテゴリ文字列。None・負値・型不正な入力は0扱い（安全側）。
        base_time_secが不正な場合は "shoes_race" にフォールバックする。
    """
    delay = _to_float_or_none(temp_delay_min)
    if delay is None or delay < 0:
        delay = 0.0

    wind = _to_float_or_none(wind_speed_ms)
    if wind is None or wind < 0:
        wind = 0.0

    gain = _to_float_or_none(elevation_gain_m)
    if gain is None or gain < 0:
        gain = 0.0

    base_time = _to_float_or_none(base_time_sec)
    if base_time is None or base_time < 0:
        # 目標タイムが不正な場合はレースシューズ側に安全側フォールバック
        base_time = 0.0

    if delay >= HEAT_SEVERE_MIN_DELAY:
        return "heat_severe"
    if delay >= HEAT_MODERATE_MIN_DELAY:
        return "heat_moderate"
    if wind >= WIND_MIN_SPEED_MS:
        return "wind"
    if gain >= HILLY_MIN_GAIN_M:
        return "hilly"

    if base_time >= DAILY_TRAINER_MIN_TIME_SEC:
        return "shoes_daily"
    return "shoes_race"
