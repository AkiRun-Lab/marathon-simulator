"""
マラソンペース計算ツール（MPC） - Shoe Finder URL Builder
VDOTからシューマッチング診断ツール（akirun.net/shoe-finder/）へのURLを組み立てる純粋関数。

Streamlitに依存しない（importしない）。例外は投げない。
"""
from typing import Optional

# シューマッチング診断ツールが受け付けるVDOTの範囲（apps/shoe-finder/index.html のclampVdotと同一）
SHOE_FINDER_VDOT_MIN = 30
SHOE_FINDER_VDOT_MAX = 85


def build_shoe_finder_url(vdot, base_url: str) -> Optional[str]:
    """VDOTからシューマッチング診断ツールのURLを組み立てる

    Args:
        vdot: VDOT値（float/int想定）。None・数値以外の場合はNoneを返す
        base_url: シューマッチング診断ツールのベースURL（末尾スラッシュ想定）

    Returns:
        "{base_url}?vdot={整数}" 形式のURL。vdotがNone・数値変換不可の場合はNone。
        範囲外（30〜85）の値は診断ツール側と同じ規則でクランプする。
    """
    if vdot is None:
        return None
    if isinstance(vdot, bool):
        return None
    try:
        vdot_float = float(vdot)
    except (TypeError, ValueError):
        return None

    vdot_int = int(round(vdot_float))
    vdot_int = max(SHOE_FINDER_VDOT_MIN, min(vdot_int, SHOE_FINDER_VDOT_MAX))
    return f"{base_url}?vdot={vdot_int}"
