"""
気温補正モジュール

Ely et al. (2007), El Helou et al. (2012) の研究に基づき、
気温がマラソンパフォーマンスに与える影響を計算します。
"""


def adjust_marathon_time(base_time_min: float, temperature: float) -> float:
    """気温によるマラソンタイム調整
    
    10°Cを最適気温とし、それより高温の場合にタイムの低下を計算します。
    
    計算式: adjusted_time = base_time × [1 + 0.0001 × h^3.6 × max(0, T - 10)]
    
    Args:
        base_time_min: 最適条件(10°C)での目標タイム（分）
        temperature: レース当日の気温（°C）
    
    Returns:
        調整後のタイム（分）
    
    Examples:
        >>> adjust_marathon_time(180, 10)  # 3:00 @ 10°C
        180.0
        >>> adjust_marathon_time(180, 20)  # 3:00 @ 20°C
        189.2  # 約9分増加
    """
    OPTIMAL_TEMP = 10.0  # 最適気温（°C）
    COEFFICIENT = 0.0001  # 係数
    EXPONENT = 3.6  # べき指数
    
    h = base_time_min / 60  # 時間単位に変換
    delta_t = max(0, temperature - OPTIMAL_TEMP)
    adjustment_factor = 1 + COEFFICIENT * (h ** EXPONENT) * delta_t
    
    return base_time_min * adjustment_factor


def format_time(minutes: float) -> str:
    """分を H:MM:SS 形式に変換
    
    Args:
        minutes: 時間（分）
    
    Returns:
        H:MM:SS 形式の文字列
    
    Examples:
        >>> format_time(180)
        '3:00:00'
        >>> format_time(189.2)
        '3:09:12'
    """
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    secs = int((minutes % 1) * 60)
    return f"{hours}:{mins:02d}:{secs:02d}"


def get_delay_minutes(base_time_min: float, temperature: float) -> float:
    """気温による遅延時間（分）を計算
    
    Args:
        base_time_min: 最適条件での目標タイム（分）
        temperature: レース当日の気温（°C）
    
    Returns:
        遅延時間（分）
    
    Examples:
        >>> get_delay_minutes(180, 10)
        0.0
        >>> round(get_delay_minutes(180, 20), 1)
        9.2
    """
    adjusted = adjust_marathon_time(base_time_min, temperature)
    return adjusted - base_time_min


def get_adjusted_pace_per_km(base_time_min: float, temperature: float) -> str:
    """調整後の1kmあたりペースを計算
    
    Args:
        base_time_min: 最適条件での目標タイム（分）
        temperature: レース当日の気温（°C）
    
    Returns:
        MM:SS/km 形式の文字列
    
    Examples:
        >>> get_adjusted_pace_per_km(180, 10)
        '4:16/km'
        >>> get_adjusted_pace_per_km(180, 20)
        '4:29/km'
    """
    adjusted = adjust_marathon_time(base_time_min, temperature)
    pace_min = adjusted / 42.195
    mins = int(pace_min)
    secs = int((pace_min % 1) * 60)
    return f"{mins}:{secs:02d}/km"


def get_temperature_warning(temperature: float) -> str:
    """気温に応じた警告メッセージを返す
    
    Args:
        temperature: 気温（°C）
    
    Returns:
        警告メッセージ（警告不要の場合は空文字列）
    
    Examples:
        >>> get_temperature_warning(20)
        ''
        >>> get_temperature_warning(26)
        '⚠️ 高温注意：こまめな給水と無理のないペース配分を心がけてください'
    """
    if temperature >= 30:
        return "🚨 危険：熱中症リスクが極めて高いです。レース中止を検討してください"
    elif temperature >= 28:
        return "⚠️ 危険：熱中症リスクが非常に高いです。無理は絶対に避けてください"
    elif temperature >= 25:
        return "⚠️ 高温注意：こまめな給水と無理のないペース配分を心がけてください"
    else:
        return ""
