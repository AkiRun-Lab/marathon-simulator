import html
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
from lib.pacing_strategy import PacingStrategy
from lib.gpx_handler import GPXHandler
from lib.vdot_handler import VDOTHandler
from lib.temperature_adjustment import adjust_marathon_time, get_delay_minutes, get_temperature_warning
from lib.altitude_adjustment import (
    adjust_marathon_time as altitude_adjust_time,
    get_delay_minutes as altitude_get_delay,
    get_altitude_warning,
)
from lib.cta_selector import judge_cta_category

# Version
__version__ = "1.6.3"

# Amazonストアフロント（おすすめギア一覧）への送客先。
# 汎用CTAはストアトップ、シミュレーション結果連動CTAは下のカテゴリ別アイデアリストを使う。
AMAZON_STORE_URL = "https://www.amazon.co.jp/shop/yancearmstron"

# カテゴリ別Amazonアイデアリスト
AMAZON_RACE_SHOES_LIST_URL = "https://amzn.to/44ZTgZQ"   # ①レースシューズ
AMAZON_DAILY_TRAINER_LIST_URL = "https://amzn.to/4wBLAsD" # ②デイリートレーナー
AMAZON_WEAR_LIST_URL = "https://amzn.to/4aRsy9f"          # ③ウェア（2026-07-15発行）
AMAZON_GADGET_LIST_URL = "https://amzn.to/4gzOg5l"        # ④ギア・ガジェット（2026-07-15発行）
AMAZON_FUEL_LIST_URL = "https://amzn.to/4ym5olj"          # ⑤補給・サプリ（2026-07-15発行）
AMAZON_ACCESSORIES_LIST_URL = "https://amzn.to/4wmTerj"   # ⑥ゼッケン・小物（2026-07-15発行）
AMAZON_STRENGTH_LIST_URL = "https://amzn.to/4fxnEAV"      # 臀筋・体幹リスト（起伏コースの脚づくり・2026-07-15差し替え済／トラッキングID akirun-rfd-22）

# シミュレーション結果連動CTA①の文言バリアント（cta_selector.judge_cta_category の戻り値がキー）
# heat_severe/heat_moderate/wind/hilly はcaption付きの専用訴求。
# shoes_race/shoes_daily は目標タイム帯別ラベル（app.py内で動的生成）をそのまま使うため
# caption/labelはNone（呼び出し側で判定してフォールバックする）
CTA_VARIANTS = {
    "heat_severe": {
        "caption": "気温{temp}℃の想定で+{delay}分。暑いレースは補給・電解質の準備で差がつきます",
        "label": "🥤 補給・サプリのおすすめを見る →",
        "url": AMAZON_FUEL_LIST_URL,
    },
    "heat_moderate": {
        "caption": "気温{temp}℃の想定で+{delay}分。通気・冷却ウェアで消耗を抑えられます",
        "label": "👕 ランニングウェアのおすすめを見る →",
        "url": AMAZON_WEAR_LIST_URL,
    },
    "wind": {
        "caption": "風速{wind}m/sの想定。ゼッケンのばたつきや防風の小物で備えられます",
        "label": "🎽 ゼッケン・小物のおすすめを見る →",
        "url": AMAZON_ACCESSORIES_LIST_URL,
    },
    "hilly": {
        "caption": "獲得標高{gain}m。下りの着地衝撃に耐える殿筋・体幹が武器になります",
        "label": "💪 補強・筋トレグッズを見る →",
        "url": AMAZON_STRENGTH_LIST_URL,
    },
    "shoes_race": {
        "caption": None,
        "label": None,
        "url": AMAZON_RACE_SHOES_LIST_URL,
    },
    "shoes_daily": {
        "caption": None,
        "label": None,
        "url": AMAZON_DAILY_TRAINER_LIST_URL,
    },
}


def _fmt_num_or_int(value) -> str:
    """整数値ならint表示、小数値なら小数1桁で表示する（例: 28.0→"28"、3.5→"3.5"）"""
    v = float(value)
    if v == int(v):
        return str(int(v))
    return f"{v:.1f}"


st.set_page_config(page_title="マラソンペース計算ツール（MPC）", layout="wide")

def load_vdot_data():
    if os.path.exists("data/VDOT一覧表.csv"):
        return VDOTHandler("data/VDOT一覧表.csv")
    return None

def main():
    # Responsive Title - PC: 1 line, Mobile: 2 lines with clean design
    st.markdown(f"""
    <style>
    .app-title {{
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 0.3rem;
        line-height: 1.2;
        color: #2196F3;
        text-align: center;
    }}
    .app-version {{
        font-size: 0.9rem;
        color: #888;
        display: block;
        text-align: center;
    }}
    .app-subtitle {{
        font-size: 1rem;
        color: #aaa;
        text-align: center;
        margin-bottom: 1rem;
    }}
    /* Mobile styles */
    @media (max-width: 768px) {{
        .app-title {{
            font-size: 5.5vw;  /* 画面幅に応じて自動調整 */
        }}
        .app-version {{
            display: block;
            font-size: 0.7rem;
            margin-top: 0.1rem;
        }}
        .app-subtitle {{
            font-size: 0.7rem;
        }}
    }}
    </style>
    <div class="app-title">🏃‍♂️ マラソンペース計算ツール</div>
    <div class="app-version">v{__version__}</div>
    <div class="app-subtitle">物理モデルに基づき、世界中のマラソンコースの予想タイムをシミュレート</div>
    """, unsafe_allow_html=True)

    # Custom CSS for Red Button
    st.markdown("""
    <style>
    /* Red Submit Button Styling */
    div[data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(45deg, #FF4B4B, #FF0000);
        color: white !important;
        border: none;
        padding: 0.5rem 1rem;
        font-size: 1.1rem !important;
        font-weight: bold !important;
        border-radius: 10px;
        box-shadow: 0 4px 15px rgba(255, 75, 75, 0.4);
        transition: all 0.3s ease;
        width: 100%;
    }
    div[data-testid="stFormSubmitButton"] > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(255, 75, 75, 0.6);
        background: linear-gradient(45deg, #FF0000, #FF4B4B);
        border: none !important;
        color: white !important;
    }
    div[data-testid="stFormSubmitButton"] > button:active {
        transform: translateY(1px);
        box-shadow: 0 2px 10px rgba(255, 75, 75, 0.3);
    }
    div[data-testid="stFormSubmitButton"] > button:focus {
        color: white !important;
        border-color: #FF4B4B !important;
    }
    /* Hide Form Border */
    [data-testid="stForm"] {
        border: none;
        padding-left: 0;
        padding-right: 0;
    }
    </style>
    """, unsafe_allow_html=True)

    # --- Pre-load VDOT (Static) ---
    vdot_handler = load_vdot_data()

    # --- Initial Instruction (Visible until executed) ---
    # Check if executed
    if 'executed' not in st.session_state:
        st.session_state['executed'] = False
    if 'result_df' not in st.session_state:
        st.session_state['result_df'] = None
    if 'result_meta' not in st.session_state:
        st.session_state['result_meta'] = None

    if not st.session_state['executed']:
        st.info("👇 下の設定パネルで条件を入力し、「シミュレーション実行」ボタンを押してください。")

    # --- Main Area Inputs ---
    # Weight fixed to 60kg as per user request (simplification)
    weight = 60.0
    
    with st.expander("📝 設定パネル", expanded=True):
        st.markdown("##### <span style='color: #2196F3'>1. 基礎走力</span>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        
        # Mode Selection (OUTSIDE FORM for Reactivity)
        with c1:
            target_mode = st.radio(
                "設定モード", 
                ["フルマラソンタイム", "VDOT"],
                horizontal=True,
                help="【VDOT】ダニエルズ式の走力指標を直接指定。\n【タイム】目標タイムから逆算してVDOTを決定します。"
            )
        
        with st.form(key='pacer_settings'):
            
            target_time_sec = None
            with c2:
                if vdot_handler:
                    if target_mode == "VDOT":
                        selected_vdot_float = st.number_input(
                            "VDOT (小数点入力可)", 
                            min_value=30.0, max_value=85.0, value=45.0, step=0.1, format="%.2f",
                            help="ダニエルズ式の走力指標(30.0〜85.0)。数値が高いほど走力が高い判定になります。"
                        )
                        exact_sec = vdot_handler.get_time_for_exact_vdot(selected_vdot_float)
                        target_time_sec = exact_sec
                        h = int(exact_sec // 3600)
                        m = int((exact_sec % 3600) // 60)
                        s = int(exact_sec % 60)
                        st.caption(f"相当タイム: {h}:{m:02d}:{s:02d}")
                    else:
                        target_time_str = st.text_input(
                            "目標タイム (h:mm:ss)", "3:30:00",
                            help="目標とする、または現在の実力のフルマラソンタイムを入力してください。"
                        )
                        try:
                            parts = list(map(int, target_time_str.split(':')))
                            if len(parts) == 3: h, m, s = parts
                            elif len(parts) == 2: h, m = parts; s = 0
                            else: raise ValueError
                            if not (0 <= m <= 59 and 0 <= s <= 59):
                                raise ValueError
                            total_sec = h * 3600 + m * 60 + s
                            # フルマラソンとして現実的な範囲のみ受け付ける
                            if not (1 * 3600 <= total_sec <= 7 * 3600):
                                raise ValueError
                            target_time_sec = total_sec
                            s_vdot = vdot_handler.get_exact_vdot_from_time(target_time_sec)
                            st.caption(f"相当 VDOT: {s_vdot:.2f}")
                        except ValueError:
                            target_time_sec = None
                            st.caption("⚠️ h:mm:ss 形式（1:00:00〜7:00:00）で入力してください")
                else:
                    st.error("VDOTデータ（data/VDOT一覧表.csv）が見つかりません。実行できません。")

            st.markdown("---")


            
            # Row 2: Course & Wind
            st.markdown("##### <span style='color: #2196F3'>2. コース・気象条件</span>", unsafe_allow_html=True)
            
            # Scan for GPX files (domestic first, then international)
            domestic_dir = os.path.join("data", "domestic")
            intl_dir = os.path.join("data", "international")
            domestic_files = sorted([os.path.join("domestic", f) for f in os.listdir(domestic_dir) if f.endswith(".gpx")]) if os.path.exists(domestic_dir) else []
            intl_files = sorted([os.path.join("international", f) for f in os.listdir(intl_dir) if f.endswith(".gpx")]) if os.path.exists(intl_dir) else []
            gpx_files = domestic_files + intl_files
            if not gpx_files:
                st.error("コースファイル（GPX）が見つかりません。data/domestic または data/international に配置してください。")
                st.stop()

            selected_gpx = st.selectbox(
                "コースファイル", gpx_files,
                format_func=lambda x: os.path.basename(x).replace(".gpx", ""),
                help="dataフォルダ内のGPXファイルを選択します。42.195km前後に自動補正されます。"
            )

            w1, w2, w3 = st.columns(3)
            with w1:
                wind_speed = st.slider(
                    "風速 (m/s)", 0.0, 10.0, 0.0,
                    help="当日の予報風速。内部計算で地表摩擦や遮蔽効果を考慮し、50%に減衰させて適用します。"
                )
            with w2:
                wind_options = {
                    "北":0, "北北東":22.5, "北東":45, "東北東":67.5,
                    "東":90, "東南東":112.5, "南東":135, "南南東":157.5,
                    "南":180, "南南西":202.5, "南西":225, "西南西":247.5,
                    "西":270, "西北西":292.5, "北西":315, "北北西":337.5
                }
                wind_label = st.selectbox(
                    "風向き", list(wind_options.keys()),
                    help="風が吹いてくる方向を選択してください。"
                )
                wind_dir = wind_options[wind_label]
            with w3:
                temperature = st.slider(
                    "気温 (°C)", 
                    min_value=0, 
                    max_value=35, 
                    value=10,
                    help="レース当日の予報気温。10°C未満では調整なし。10°C以上では気温に応じてタイムが調整されます。"
                )

            # 標高補正トグル
            apply_altitude_correction = st.checkbox(
                "🏔️ 標高補正を適用（Péronnet 1991）",
                value=True,
                help="GPX の平均標高（海抜 m）に基づき、有酸素パワーの低下分をタイムに反映します。閾値 500m 未満は影響ゼロ。"
            )

            # Advanced Smoothing (Hidden by default, enabled via ?dev=true)
            # Check for query params (Streamlit 1.30+ uses st.query_params)
            is_dev = "dev" in st.query_params
            
            if is_dev:
                smoothing_m = st.slider(
                    "詳細設定: 標高平滑化範囲 (m) [開発者用]",
                    min_value=100, max_value=200, value=130, step=5,
                    help="値を大きくすると、細かい坂を無視して滑らかにします。"
                )
                altitude_threshold_m = st.slider(
                    "詳細設定: 標高補正の閾値 (m) [開発者用]",
                    min_value=0, max_value=1500, value=500, step=50,
                    help="この値以下の平均標高は補正係数 1.0（補正ゼロ）。デフォルト 500m。"
                )
            else:
                smoothing_m = 130  # Default value
                altitude_threshold_m = 500  # Default value
            
            st.markdown("---")
            


            # Row 3: Strategy
            st.markdown("##### <span style='color: #2196F3'>3. レース戦略</span>", unsafe_allow_html=True)
            s1, s2 = st.columns(2)
            with s1:
                split_map = {
                    "イーブン (一定)": "even",
                    "ポジティブ (前半貯金)": "positive",
                    "ネガティブ (後半追い上げ)": "negative"
                }
                split_label = st.selectbox(
                    "スプリット配分", list(split_map.keys()),
                    help="ペース配分の傾向を選びます。\n【イーブン】一定ペース\n【ポジティブ】前半速く後半粘る\n【ネガティブ】後半にペースアップ"
                )
            
            with s2:
                hill_power_param = st.slider(
                    "坂道強度 (平地比 %)", 
                    min_value=70, max_value=130, value=100, step=5,
                    help="100%より高いと坂で頑張り、低いと休みます"
                )
            
            submit_btn = st.form_submit_button("🚀 シミュレーション実行", type="primary")
    

    
    pacing_preference = split_map[split_label]

    # --- Calculation Engine (Runs ONLY on Submit) ---
    if submit_btn:
        if target_time_sec is None:
            st.error("目標タイムまたはVDOTの設定を確認してください。")
            st.stop()

        # Load Course Data（読み込めない場合は黙ってフォールバックせず明示エラー）
        gpx_path = os.path.join("data", selected_gpx)
        if not os.path.exists(gpx_path):
            st.error(f"コースファイルが見つかりません: {selected_gpx}")
            st.stop()
        try:
            handler = GPXHandler(gpx_path)
            course_data = handler.to_course_data(smoothing_window_m=smoothing_m)
        except ValueError as e:
            st.error(f"コースファイルを読み込めませんでした: {e}")
            st.stop()
        if not course_data.segments:
            st.error(f"コースファイルに座標データがありません: {selected_gpx}")
            st.stop()

        st.session_state['executed'] = True

        # Temperature Adjustment
        base_time_sec = target_time_sec  # 補正前のタイムを保存
        base_time_min = target_time_sec / 60

        # 気温補正を適用
        adjusted_time_min = adjust_marathon_time(base_time_min, temperature)
        temp_delay_min = get_delay_minutes(base_time_min, temperature)
        temp_adjusted_time_min = adjusted_time_min  # 標高補正前のタイム（コース比較で使用）

        # 標高補正を適用
        mean_elevation = course_data.calculate_mean_elevation()
        altitude_delay_min = altitude_get_delay(base_time_min, mean_elevation, threshold_m=altitude_threshold_m) if apply_altitude_correction else 0.0
        if apply_altitude_correction:
            adjusted_time_min = altitude_adjust_time(adjusted_time_min, mean_elevation, threshold_m=altitude_threshold_m)

        adjusted_time_sec = adjusted_time_min * 60

        # Strategy Calculation (補正後のタイムを使用)
        strategy = PacingStrategy(
            mass_kg=weight, 
            wind_speed_ms=wind_speed, 
            wind_dir_degrees=wind_dir,
            target_time_sec=adjusted_time_sec,  # 気温補正後のタイム
            hill_preference=hill_power_param, 
            pacing_preference=pacing_preference
        )
        
        # Generate Table
        df_high_res = strategy.generate_pace_table(course_data, interval_meters=5)
        
        # Store Results
        st.session_state['result_df'] = df_high_res
        st.session_state['result_meta'] = {
            'course_name': selected_gpx,
            'base_speed_ms': strategy.base_speed_ms,
            'target_time_sec': adjusted_time_sec,  # 補正後のタイム
            'temp_adjusted_time_sec': temp_adjusted_time_min * 60,  # 気温補正のみ（標高補正前）のタイム
            'base_time_sec': base_time_sec,  # 補正前のタイム（表示用）
            'temperature': temperature,  # 気温
            'temp_delay_min': temp_delay_min,  # 気温による遅延 
            'weight': weight,
            'wind_speed': wind_speed,
            'wind_dir': wind_dir,
            'hill_param': hill_power_param,
            'pacing_pref': pacing_preference,
            'smoothing_m': smoothing_m,
            # Pre-calculate metrics for current course
            'elevation_gain': course_data.calculate_elevation_gain(),
            'mean_elevation': mean_elevation,
            'altitude_delay_min': altitude_delay_min,
            'altitude_correction_applied': apply_altitude_correction,
            'altitude_threshold_m': altitude_threshold_m,
        }

    # --- Rendering Engine (Uses Cached Data) ---
    if st.session_state['executed'] and st.session_state['result_df'] is not None:
        
        # Retrieve Data
        df_high_res = st.session_state['result_df']
        meta = st.session_state['result_meta']
        
        # --- Results Metrics ---
        total_seconds = df_high_res['time_sec'].sum()
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        formatted_time = f"{hours}:{minutes:02d}:{seconds:02d}"
        
        avg_pace_sec = total_seconds / 42.195
        avg_min = int(avg_pace_sec // 60)
        avg_sec = int(avg_pace_sec % 60)
        formatted_pace = f"{avg_min}:{avg_sec:02d}/km"
        
        # Summary Metrics - Featured Time Display + CTA①（カード一体型・カテゴリ別送客）
        # 目標タイム帯別ラベル（従来ロジック。shoes_race/shoes_daily カテゴリ・フォールバック時に使用）
        target_h = int(meta['base_time_sec'] // 3600)
        target_m = int((meta['base_time_sec'] % 3600) // 60)
        if target_h >= 4:
            fallback_cta_label = "👟 完走を支えるギアをAmazonで見る →"
        elif target_h >= 3 and target_m >= 30:
            fallback_cta_label = "👟 サブ3.5向けシューズ＆ギアを見る →"
        elif target_h >= 3:
            fallback_cta_label = "👟 サブ3に効くギアをAmazonで見る →"
        else:
            fallback_cta_label = "👟 2時間台ランナーの装備を見る →"

        # シミュレーション結果（st.session_state由来のmetaのみ使用・rerun耐性）からCTAカテゴリを判定
        cta_category = judge_cta_category(
            meta.get('temp_delay_min'),
            meta.get('wind_speed'),
            meta.get('elevation_gain'),
            meta.get('base_time_sec'),
        )

        cta_url = AMAZON_STORE_URL
        cta_label = fallback_cta_label
        cta_caption_html = ""

        variant = CTA_VARIANTS.get(cta_category)
        try:
            if cta_category in ("shoes_race", "shoes_daily") and variant is not None:
                cta_url = variant["url"]
                cta_label = fallback_cta_label
            elif variant is not None and variant.get("caption"):
                caption_text = variant["caption"].format(
                    temp=_fmt_num_or_int(meta.get('temperature')),
                    delay=f"{float(meta.get('temp_delay_min', 0.0)):.1f}",
                    wind=_fmt_num_or_int(meta.get('wind_speed')),
                    gain=int(round(float(meta.get('elevation_gain', 0.0)))),
                )
                cta_url = variant["url"]
                cta_label = variant["label"]
                cta_caption_html = (
                    '<p style="margin: 0 0 0.6rem 0; color: #aaa; font-size: 0.82rem;">'
                    f'{html.escape(caption_text)}</p>'
                )
        except Exception:
            # 失敗時は現行どおりのタイム帯別ラベル＋ストアトップにフォールバック（アプリを絶対に壊さない）
            cta_url = AMAZON_STORE_URL
            cta_label = fallback_cta_label
            cta_caption_html = ""

        course_name = os.path.basename(meta['course_name']).replace('.gpx', '')

        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-radius: 16px;
            padding: 1.5rem;
            margin: 1rem 0;
            text-align: center;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        ">
            <p style="margin: 0; color: #888; font-size: 0.9rem;">🏁 シミュレーション結果</p>
            <p style="
                margin: 0.5rem 0;
                font-size: 3.5rem;
                font-weight: bold;
                color: #FF6B6B;
                text-shadow: 0 2px 10px rgba(255, 107, 107, 0.5);
                letter-spacing: 2px;
            ">{formatted_time}</p>
            <p style="margin: 0 0 1rem 0; color: #aaa; font-size: 1rem;">{course_name}</p>{cta_caption_html}
            <a href="{cta_url}" target="_blank" rel="noopener noreferrer sponsored" style="
                display: inline-block;
                background: rgba(255, 107, 107, 0.15);
                color: #FF6B6B;
                padding: 0.4rem 1.2rem;
                border-radius: 20px;
                border: 1px solid rgba(255, 107, 107, 0.4);
                font-size: 0.85rem;
                font-weight: bold;
                text-decoration: none;
            ">{cta_label}</a>
        </div>
        """, unsafe_allow_html=True)
        
        # Temperature Adjustment Info
        if meta['temperature'] > 10:
            delay_min = meta['temp_delay_min']
            temp = meta['temperature']
            base_time_sec = meta['base_time_sec']
            
            # 補正情報の表示
            st.info(f"""
🌡️ **気温補正適用済み**: {temp}°C の条件で、約 **{delay_min:.1f}分** の遅延を考慮した予想タイムです。

※ 10°C（最適気温）の場合、約 **{delay_min:.1f}分** 短縮される見込みです。
            """)
            
            # 警告メッセージ
            warning = get_temperature_warning(temp)
            if warning:
                if temp >= 30:
                    st.error(warning)
                elif temp >= 25:
                    st.warning(warning)
            
            # 免責文言
            st.caption("⚠️ この調整値は学術研究に基づく統計的推定です。個人差や当日のコンディションにより実際のタイムは異なる場合があります。")

        # Altitude Adjustment Info
        if meta.get('altitude_correction_applied'):
            mean_elev = meta.get('mean_elevation', 0.0)
            alt_delay = meta.get('altitude_delay_min', 0.0)
            if alt_delay > 0.0:
                st.info(f"🏔️ **標高補正適用済み**：平均標高 {int(mean_elev)}m → 約 **{alt_delay:.1f}分** の遅延を考慮した予想タイムです。")
            else:
                applied_threshold = int(meta.get('altitude_threshold_m', 500))
                st.info(f"🏔️ **標高補正適用済み**：平均標高 {int(mean_elev)}m（{applied_threshold}m 以下のため影響なし）")
            warning = get_altitude_warning(mean_elev)
            if warning:
                st.warning(warning)
            st.caption("⚠️ 標高補正は非高地順化ランナーを想定した理論値です（Péronnet et al. 1991）。高地に慣れたランナーへの影響は小さくなります。")

        # Additional Metrics - Row 1
        col1, col2, col3 = st.columns(3)
        col1.metric("予想タイム", formatted_time)
        
        col2.metric("シミュレーション結果：平均ペース", formatted_pace)
        
        # Flat Equivalent
        base_flat_pace = 1000.0 / meta['base_speed_ms']
        flat_min = int(base_flat_pace // 60)
        flat_sec = int(base_flat_pace % 60)
        col3.metric("基礎走力（平地相当ペース）", f"{flat_min}:{flat_sec:02d}/km")
        col3.caption("このペース感覚を維持してください")
        
        # Additional Metrics - Row 2
        col4, col5, col6 = st.columns(3)
        col4.metric("獲得標高", f"{int(meta.get('elevation_gain', 0))}m")
        
        # コース難易度 = シミュレーション結果 / 目標タイム
        difficulty = total_seconds / meta['base_time_sec']
        col5.metric("コース難易度", f"{difficulty:.4g}")
        col5.caption("シミュレーション結果 ÷ 目標タイム（気象・標高の影響込み）")
        mean_elev = meta.get('mean_elevation', 0.0)
        col6.metric("平均標高", f"{int(mean_elev)}m")
        col6.caption("コース平均海抜")

        # --- Charts (Using High Res Data) ---
        st.subheader("ペース戦略チャート")
        
        # Toggle for Smoothing
        enable_smoothing = st.checkbox("チャートの平滑化 (1km移動平均)", value=True, help="細かい変動を除去して傾向を見やすくします")
        
        fig = go.Figure()
        
        # Elevation Approx reconstruction
        elevations = [0]
        for g in df_high_res['gradient']:
            elevations.append(elevations[-1] + (5 * g)) # 5m segments
        df_high_res['elevation_approx'] = elevations[:-1]
        
        # Elevation (Filled Area) - Normalized to fit chart? No, use secondary y-axis
        fig.add_trace(go.Scatter(
            x=df_high_res['km'], y=df_high_res['elevation_approx'], fill='tozeroy', 
            name='コース起伏 (相対標高)', line=dict(color='gray', width=0), opacity=0.2, yaxis='y2'
        ))
        
        # Pace Data selection
        y_pace = df_high_res['pace_min_km']
        if enable_smoothing:
            # 5m intervals. 1km = 200 points.
            y_pace = df_high_res['pace_min_km'].rolling(window=200, min_periods=1, center=True).mean()
        
        # Pace (Line)
        fig.add_trace(go.Scatter(
            x=df_high_res['km'], y=y_pace, 
            name='平均ペース (分/km)', line=dict(color='#ff4b4b', width=2)
        ))
        
        fig.update_layout(
            xaxis_title="距離 (km)",
            yaxis=dict(title="ペース (分/km)", range=[y_pace.max()+0.2, y_pace.min()-0.2]), 
            yaxis2=dict(title="相対標高 (m)", overlaying='y', side='right', showgrid=False),
            hovermode="x unified",
            legend=dict(orientation="h", y=1.1)
        )
        st.plotly_chart(fig, use_container_width=True)

        # --- Course Map ---
        if 'lat' in df_high_res.columns and df_high_res['lat'].notnull().any():
            st.subheader("コース平面図")
            
            # Filter valid coords
            map_df = df_high_res.dropna(subset=['lat', 'lon'])
            
            map_fig = go.Figure(go.Scattermap(
                mode = "lines",
                lon = map_df['lon'],
                lat = map_df['lat'],
                marker = {'size': 10},
                line = dict(width=4, color='#FF0000'),
                text = map_df['km'].apply(lambda x: f"{x:.1f}km"),
                hoverinfo='text'
            ))
            
            # Auto-Zoom Calculation
            min_lat, max_lat = map_df['lat'].min(), map_df['lat'].max()
            min_lon, max_lon = map_df['lon'].min(), map_df['lon'].max()
            
            mid_lat = (min_lat + max_lat) / 2
            mid_lon = (min_lon + max_lon) / 2
            
            # Heuristic for Zoom Level
            # 0.1 deg diff ~ 11km. Typically requires Zoom ~12.
            lat_diff = max_lat - min_lat
            lon_diff = max_lon - min_lon
            max_diff = max(lat_diff, lon_diff)
            
            # Base zoom 11 for ~0.3 deg. +1 zoom for half size.
            # zoom = 11 - log2(max_diff / 0.3)
            # Safe clamp between 8 and 15
            if max_diff > 0:
                # Log2(max_diff / 0.2) -> if diff=0.2, 0. if diff=0.4, 1.
                # If diff=0.4 (40km), we want Zoom ~10.
                # 11.5 - 1 = 10.5. 
                # User reported too zoomed in, so let's be conservative.
                # Subtract 1.5 extra padding.
                zoom_level = 11.5 - np.log2(max_diff / 0.2) - 1.2
                zoom_level = max(8, min(15, zoom_level))
            else:
                zoom_level = 12
            
            map_fig.update_layout(
                map_style="open-street-map",
                map = dict(
                    center=dict(lat=mid_lat, lon=mid_lon),
                    zoom=zoom_level
                ),
                margin={"r":0,"t":0,"l":0,"b":0},
                height=400
            )
            st.plotly_chart(map_fig, use_container_width=True)

        # --- Detailed Table (Aggregated to 1km) ---
        st.subheader("シミュレーション結果：区間ラップ表（1km毎）")
        
        # Aggregate 100m chunks into 1km bins
        df_high_res['km_bin'] = df_high_res['km'].apply(np.floor).astype(int)
        
        agg_funcs = {
            'time_sec': 'sum',
            'cumulative_time_sec': 'max'
        }
        
        df_1km = df_high_res.groupby('km_bin').agg(agg_funcs).reset_index()
        
        # Calculate Pace
        counts = df_high_res.groupby('km_bin').size()
        df_1km['dist_km'] = counts * 0.005 # 5m = 0.005km
        
        df_1km['pace_sec_km'] = df_1km['time_sec'] / df_1km['dist_km']
        
        # Formatting
        def fmt_section(bin_idx):
            start = bin_idx
            end = bin_idx + 1
            if start == 42:
                return "42 - 42.195 km"
            return f"{start} - {end} km"

        df_1km['区間'] = df_1km['km_bin'].apply(fmt_section)
        
        df_1km['ラップ'] = df_1km['time_sec'].apply(lambda x: f"{int(x//60)}:{int(x%60):02d}")
        df_1km['通過タイム'] = df_1km['cumulative_time_sec'].apply(lambda x: f"{int(x//3600)}:{int((x%3600)//60):02d}:{int(x%60):02d}")
        
        # Pace string
        def fmt_pace(sec_km):
            m = int(sec_km // 60)
            s = int(sec_km % 60)
            return f"{m}:{s:02d}"
        
        df_1km['平均ペース'] = df_1km['pace_sec_km'].apply(fmt_pace)

        final_table = df_1km[['区間', '平均ペース', 'ラップ', '通過タイム']]
        st.dataframe(final_table, width="stretch")

        # CTA② ラップ表の下 - ランニングギア・ガジェットCTA（分岐なしの固定訴求）
        st.markdown(f"""
<div style="
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border: 1px solid rgba(255, 107, 107, 0.3);
    border-radius: 10px;
    padding: 1.2rem;
    margin: 1rem 0 1.5rem 0;
    text-align: center;
">
    <p style="color: #E2E8F0; font-size: 0.95rem; margin: 0 0 0.3rem 0;">
        📋 ラップ表をメモしたら、次は<span style="color: #FF6B6B; font-weight: bold;">ペースを守る道具</span>
    </p>
    <p style="color: #94A3B8; font-size: 0.8rem; margin: 0 0 0.8rem 0;">
        1kmごとのラップを本番で刻むには、GPSウォッチと使い慣れたギアが支えになります
    </p>
    <a href="{AMAZON_GADGET_LIST_URL}" target="_blank" rel="noopener noreferrer sponsored" style="
        display: inline-block;
        background: transparent;
        color: #FF6B6B;
        padding: 0.4rem 1.5rem;
        border-radius: 6px;
        border: 1px solid #FF6B6B;
        text-decoration: none;
        font-weight: bold;
        font-size: 0.85rem;
        transition: all 0.2s;
    ">⌚ ランニングギア・ガジェット一覧（Amazon）</a>
</div>
""", unsafe_allow_html=True)

        # --- Course Comparison Section ---
        st.divider()
        st.subheader("📊 コース比較")
        st.markdown("現在の設定条件（気象・レース戦略）を維持したまま、別コースのシミュレーション結果と比較します。")
        
        current_course = meta['course_name']
        compare_files = [f for f in gpx_files if f != current_course]
        
        if compare_files:
            compare_gpx = st.selectbox(
                "比較対象のコース", compare_files,
                format_func=lambda x: os.path.basename(x).replace(".gpx", "")
            )
            
            if st.button("コース比較を実行", key="compare_btn"):
                # Load comparison course（読み込めない場合は明示エラー）
                comp_gpx_path = os.path.join("data", compare_gpx)
                if not os.path.exists(comp_gpx_path):
                    st.error(f"比較コースファイルが見つかりません: {compare_gpx}")
                    st.stop()
                try:
                    comp_handler = GPXHandler(comp_gpx_path)
                    # Use the same smoothing parameter as the current simulation
                    sm_m = meta.get('smoothing_m', 130)
                    comp_data = comp_handler.to_course_data(smoothing_window_m=sm_m)
                except ValueError as e:
                    st.error(f"比較コースを読み込めませんでした: {e}")
                    st.stop()
                if not comp_data.segments:
                    st.error(f"比較コースに座標データがありません: {compare_gpx}")
                    st.stop()
                
                # 標高補正は比較先コース自身の平均標高で再計算する（気温補正は気象条件なので共通）
                comp_target_sec = meta.get('temp_adjusted_time_sec', meta['target_time_sec'])
                comp_mean_elev = comp_data.calculate_mean_elevation()
                if meta.get('altitude_correction_applied'):
                    comp_target_sec = altitude_adjust_time(
                        comp_target_sec / 60.0,
                        comp_mean_elev,
                        threshold_m=meta.get('altitude_threshold_m', 500),
                    ) * 60.0

                # Run Strategy
                comp_strategy = PacingStrategy(
                    mass_kg=meta['weight'],
                    wind_speed_ms=meta['wind_speed'],
                    wind_dir_degrees=meta['wind_dir'],
                    target_time_sec=comp_target_sec,
                    hill_preference=meta['hill_param'],
                    pacing_preference=meta['pacing_pref']
                )
                
                comp_df = comp_strategy.generate_pace_table(comp_data, interval_meters=5)
                comp_total = comp_df['time_sec'].sum()
                
                # Compare Times
                # Use int() to ensure consistency with displayed formatted times
                diff_sec = int(comp_total) - int(total_seconds)
                sign = "+" if diff_sec >= 0 else "-"
                abs_diff = abs(diff_sec)
                diff_m = int(abs_diff // 60)
                diff_s = int(abs_diff % 60)
                diff_str = f"{sign}{diff_m}分{diff_s}秒"
                
                ch = int(comp_total // 3600)
                cm = int((comp_total % 3600) // 60)
                cs = int(comp_total % 60)
                comp_time_fmt = f"{ch}:{cm:02d}:{cs:02d}"
                
                # Calculate Metrics for Comparison
                comp_gain = comp_data.calculate_elevation_gain()
                
                # コース難易度 = シミュレーション結果 / 目標タイム
                curr_difficulty = total_seconds / meta['base_time_sec']
                comp_difficulty = comp_total / meta['base_time_sec']
                
                curr_gain = meta.get('elevation_gain', 0)
                
                # Display Results with Metrics
                c1, c2 = st.columns(2)
                
                curr_mean_elev = meta.get('mean_elevation', 0.0)

                # Current
                c1.markdown(f"### {os.path.basename(current_course).replace('.gpx', '')}")
                c1.metric("予想タイム", formatted_time)
                c1.metric("獲得標高", f"{int(curr_gain)}m")
                c1.metric("平均標高", f"{int(curr_mean_elev)}m")
                c1.metric("コース難易度", f"{curr_difficulty:.4g}")

                # Comparison
                c2.markdown(f"### {os.path.basename(compare_gpx).replace('.gpx', '')}")
                c2.metric("予想タイム", comp_time_fmt, delta=diff_str, delta_color="inverse")
                c2.metric("獲得標高", f"{int(comp_gain)}m", delta=f"{int(comp_gain - curr_gain)}m", delta_color="off")
                c2.metric("平均標高", f"{int(comp_mean_elev)}m", delta=f"{int(comp_mean_elev - curr_mean_elev)}m", delta_color="off")
                diff_difficulty = comp_difficulty - curr_difficulty
                c2.metric("コース難易度", f"{comp_difficulty:.4g}", delta=f"{diff_difficulty:+.4g}", delta_color="off")
                
                # Recommendation Comment based on time difference
                st.divider()
                compare_name = os.path.basename(compare_gpx).replace('.gpx', '')
                current_name = os.path.basename(current_course).replace('.gpx', '')
                
                if diff_sec < 0:
                    # Comparison course is faster
                    faster_time = f"{diff_m}分{diff_s}秒" if diff_m > 0 else f"{diff_s}秒"
                    st.success(f"🏆 **{compare_name}なら {faster_time} 速い！** PR狙いにおすすめです")
                elif diff_sec > 0:
                    # Current course is faster
                    slower_time = f"{diff_m}分{diff_s}秒" if diff_m > 0 else f"{diff_s}秒"
                    st.warning(f"⚠️ **{compare_name}は {slower_time} 遅い** 記録狙いなら {current_name} がおすすめ")
                else:
                    st.info(f"⏱️ **両コースのタイムは同等です**")

        else:
            st.caption("比較できる他のGPXファイルがありません。")

        # CTA③ コース比較後 - メインCTA（Amazonストア・ゴールドカード）
        st.markdown(f"""
<div style="
    background: linear-gradient(135deg, #F4C66B 0%, #E0A23D 100%);
    border-radius: 16px;
    padding: 2rem 1.5rem 1.6rem;
    margin: 1.8rem 0 0.8rem;
    text-align: center;
    position: relative;
    overflow: hidden;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.28);
">
    <div style="
        position: absolute;
        top: -1px;
        left: 50%;
        transform: translateX(-50%);
        background: linear-gradient(135deg, #FF6B6B, #FF4757);
        color: white;
        padding: 0.25rem 1.2rem;
        border-radius: 0 0 8px 8px;
        font-size: 0.72rem;
        font-weight: bold;
        letter-spacing: 0.5px;
    ">🔥 ランナーに人気</div>
    <p style="font-size: 2.2rem; margin: 1.1rem 0 0.2rem;">👟</p>
    <p style="color: #1F3A6B; font-weight: 800; font-size: clamp(1.15rem, 4.6vw, 1.5rem); margin: 0 0 0.5rem;">
        PB更新に効くシューズ＆ギア
    </p>
    <p style="color: #4a3b14; font-size: clamp(0.85rem, 3.2vw, 0.98rem); line-height: 1.6; margin: 0 auto 1.3rem; max-width: 34em;">
        私が実走で検証して使っているシューズ・ウェア・補給を、用途別にAmazonのおすすめリストにまとめました。自分に合う一足を探す入口にどうぞ。
    </p>
    <a href="{AMAZON_STORE_URL}" target="_blank" rel="noopener noreferrer sponsored" style="
        display: inline-block;
        background: #1F3A6B;
        color: #ffffff;
        padding: 0.95rem 2.4rem;
        border-radius: 10px;
        text-decoration: none;
        font-weight: 800;
        font-size: clamp(1rem, 3.8vw, 1.2rem);
        box-shadow: 0 5px 16px rgba(0, 0, 0, 0.3);
    ">🛒 おすすめギア一覧（Amazon）を見る ›</a>
    <p style="color: #5a4a1f; font-size: 0.72rem; margin: 1rem 0 0;">
        ※ Amazonのアソシエイトとして適格販売により収入を得ています
    </p>
</div>
""", unsafe_allow_html=True)

    # --- App Info (Manual Summary) ---
    st.divider()
    with st.expander("📘 アプリの使い方・仕様要約"):
        st.markdown("""
        **1. 基礎走力の設定**
        VDOTまたは目標タイムを入力し、あなたの走力基準を定めます。
        
        **2. コースと環境**
        GPXデータからコースの起伏を読み取ります。
        風速は予報値を入力してください（内部で地表補正されます）。
        ※「詳細設定」で獲得標高の算出基準（平滑化）を調整できます。
        
        **3. レース戦略**
        *   **スプリット**: 前半・後半のペース配分傾向。
        *   **坂道設定**: 上り坂でどれくらい頑張るか（100%基準）。
        
        **4. 結果の見方**
        *   **平均ペース**: 赤い線に従って走ると、設定した戦略通りにレースを展開できます。
        *   **平滑化**: チャートのチェックボックスで、細かい変動をならしてトレンドを確認できます。
        *   **コース比較**: 別のコースとコース難易度やタイム差を比較できます。
        """)
        
        # ブログ記事への誘導
        st.markdown("""
<div style="
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border-radius: 10px;
    padding: 1rem;
    margin-top: 0.5rem;
    text-align: center;
">
    <p style="color: #E2E8F0; font-size: 0.9rem; margin: 0 0 0.5rem 0;">
        📖 もっと詳しい使い方をブログで解説しています
    </p>
    <a href="https://akirun.net/marathon-simulator-guide/" target="_blank" style="
        display: inline-block;
        background: rgba(0, 229, 255, 0.1);
        color: #00E5FF;
        padding: 0.4rem 1.2rem;
        border-radius: 20px;
        border: 1px solid rgba(0, 229, 255, 0.3);
        font-size: 0.85rem;
        font-weight: bold;
        text-decoration: none;
    ">使い方ガイドを読む →</a>
</div>
""", unsafe_allow_html=True)
    
    # --- Footer with Developer Profile ---
    st.divider()
    st.markdown(f"""
    <div style="text-align: center; padding: 1rem 0;">
        <p style="margin: 0.3rem 0;">👤 <strong>開発者:</strong> あきら</p>
        <p style="margin: 0.3rem 0;">🏃 フルマラソンPB 2:46:27</p>
        <div style="
            display: flex;
            justify-content: center;
            gap: 0.8rem;
            flex-wrap: wrap;
            margin: 1rem 0;
        ">
            <a href="https://akirun.net/" target="_blank" style="
                display: inline-block;
                background: rgba(0, 229, 255, 0.1);
                color: #00E5FF;
                padding: 0.5rem 1rem;
                border-radius: 8px;
                border: 1px solid rgba(0, 229, 255, 0.3);
                text-decoration: none;
                font-size: 0.85rem;
                font-weight: bold;
            ">📱 AkiRun ブログ</a>
            <a href="https://akirun.net/marathon-simulator-guide/" target="_blank" style="
                display: inline-block;
                background: rgba(255, 107, 107, 0.1);
                color: #FF6B6B;
                padding: 0.5rem 1rem;
                border-radius: 8px;
                border: 1px solid rgba(255, 107, 107, 0.3);
                text-decoration: none;
                font-size: 0.85rem;
                font-weight: bold;
            ">📖 使い方ガイド</a>
            <a href="https://akirun.net/marathon-gear-recommend/" target="_blank" style="
                display: inline-block;
                background: rgba(255, 107, 107, 0.1);
                color: #FF6B6B;
                padding: 0.5rem 1rem;
                border-radius: 8px;
                border: 1px solid rgba(255, 107, 107, 0.3);
                text-decoration: none;
                font-size: 0.85rem;
                font-weight: bold;
            ">👟 ギアガイド</a>
        </div>
        <p style="margin: 1rem 0 0 0; font-size: 0.8rem; color: #888;">
            マラソンペース計算ツール v{__version__} | © 2025 AkiRun
        </p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
