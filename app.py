import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
from lib.course_data import CourseData
from lib.pacing_strategy import PacingStrategy
from lib.gpx_handler import GPXHandler
from lib.vdot_handler import VDOTHandler

st.set_page_config(page_title="マラソン攻略シミュレーター", layout="wide")

def load_vdot_data():
    if os.path.exists("data/VDOT一覧表.csv"):
        return VDOTHandler("data/VDOT一覧表.csv")
    return None

def main():
    st.title("🏃‍♂️ マラソン攻略シミュレーター (β0.1)")
    st.markdown("物理モデルに基づき、世界中のマラソンコースの予想タイムをシミュレートします")

    # Custom CSS for Red Button
    st.markdown("""
    <style>
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
    </style>
    """, unsafe_allow_html=True)

    # --- Pre-load VDOT (Static) ---
    vdot_handler = load_vdot_data()

    # --- Sidebar Inputs ---
    # Weight fixed to 60kg as per user request (simplification)
    weight = 60.0
    
    st.sidebar.header("設定")
    # Target Selection Mode
    target_mode = st.sidebar.radio(
        "基礎走力設定モード", 
        ["フルマラソンタイム", "VDOT"],
        help="【VDOT】ダニエルズ式の走力指標を直接指定。\n【タイム】目標タイムから逆算してVDOTを決定します。"
    )

    # Form Start
    with st.sidebar.form(key='pacer_settings'):
        st.subheader("基礎走力")
        # Target Input
        target_time_sec = None 
        
        if vdot_handler:
            if target_mode == "VDOT":
                selected_vdot_float = st.number_input(
                    "VDOT (小数点入力可)", 
                    min_value=30.0, max_value=85.0, value=45.0, step=0.1, format="%.2f",
                    help="ジャック・ダニエルズ博士のランニングフォーミュラに基づく走力指数です。"
                )
                
                # Interpolate Time & Display immediately inside form
                exact_sec = vdot_handler.get_time_for_exact_vdot(selected_vdot_float)
                target_time_sec = exact_sec
                
                h = int(exact_sec // 3600)
                m = int((exact_sec % 3600) // 60)
                s = int(exact_sec % 60)
                st.caption(f"入力VDOT相当タイム: {h}:{m:02d}:{s:02d}")
                
            else: # Time Target
                target_time_str = st.text_input(
                    "フルマラソンタイム (h:mm:ss)", "3:30:00",
                    help="目標とする、または現在の実力のフルマラソンタイムを入力してください。"
                )
                
                try:
                    parts = list(map(int, target_time_str.split(':')))
                    if len(parts) == 3: h, m, s = parts
                    elif len(parts) == 2: h, m = parts; s = 0
                    else: raise ValueError
                    target_time_sec = h * 3600 + m * 60 + s
                    
                    # Display associated VDOT inside form
                    s_vdot = vdot_handler.get_exact_vdot_from_time(target_time_sec)
                    st.info(f"相当する VDOT: {s_vdot:.2f}")
                    
                except ValueError:
                    target_time_sec = None

        else:
            st.error("データフォルダに 'VDOT一覧表.csv' が見つかりません。")
            selected_vdot_float = st.number_input("VDOT (手動入力)", value=45.0)

        st.subheader("コース選択")
        # Scan for GPX files
        data_dir = "data"
        gpx_files = [f for f in os.listdir(data_dir) if f.endswith(".gpx")]
        if not gpx_files:
            gpx_files = ["Ehime-marathon2025.gpx (Default)"]
        gpx_files.sort()
        
        selected_gpx = st.selectbox(
            "コースファイル", gpx_files,
            format_func=lambda x: x.replace(".gpx", ""),
            help="dataフォルダ内のGPXファイルを選択します。42.195km前後に自動補正されます。"
        )

        st.header("環境条件")
        
        # Elevation Smoothing Slider (Hidden in Expander)
        with st.sidebar.expander("詳細設定 (開発者用)"):
            smoothing_m = st.slider(
                "標高データの平滑化範囲 (m)", 
                min_value=100, max_value=200, value=130, step=5,
                help="獲得標高の算出に使用する平滑化の強さ。値を大きくするとノイズが減り、獲得標高が小さくなります。"
            )

        wind_speed = st.slider(
            "風速 (m/s)", 0.0, 10.0, 0.0,
            help="当日の予報風速。内部計算で地表摩擦や遮蔽効果を考慮し、50%に減衰させて適用します。"
        )
        
        wind_options = {
            "北": 0,
            "北東": 45,
            "東": 90,
            "南東": 135,
            "南": 180,
            "南西": 225,
            "西": 270,
            "北西": 315
        }
        wind_label = st.selectbox(
            "風向き (風が吹いてくる方角)", list(wind_options.keys()),
            help="風が吹いてくる方向を選択してください。"
        )
        wind_dir = wind_options[wind_label]

        # Strategy Settings
        st.subheader("レース戦略の選択")
        
        # Split Strategy
        split_map = {
            "イーブン (一定)": "even",
            "ポジティブ (前半貯金型)": "positive",
            "ネガティブ (後半追い上げ型)": "negative"
        }
        split_label = st.selectbox(
            "スプリット配分", list(split_map.keys()),
            help="ペース配分の傾向を選びます。\n・イーブン: 終始一定\n・ポジティブ: 前半速く、後半粘る\n・ネガティブ: 前半抑えて、後半上げる"
        )
        
        # Hill Strategy
        hill_power_param = st.slider(
            "上り坂のパワー設定 (平地比 %)", 
            min_value=70, max_value=130, value=100, step=5,
            help="坂道での頑張り度合い。\n・100%: 平地と同じ感覚（速度は落ちる）\n・>100%: 坂で頑張る（後半消耗リスクあり）\n・<100%: 坂は楽をする"
        )
        
        submit_btn = st.form_submit_button("🚀 シミュレーション実行", type="primary")
    
    pacing_preference = split_map[split_label]

    # ... (Session State & Calculation Logic remain same) ...
    # (Leaving middle parts unchanged via context match skipping, but actually I need to replace block)
    # Since this is a partial replace, I'll just focus on inputs first if possible.
    # But wait, replace_file_content replaces a contiguous block. 
    # I need to be careful not to delete the logic below form.
    # The 'pacing_preference = ...' line matches existing code.
    
    # Let's verify where line 411 starts (Sidebar Info).
    # I need to handle the bottom part separately or include lines 156-430? That's huge.
    # I will split this into two edits.
    
    # EDIT 1: Sidebar Inputs with Tooltips (replacing lines 61-155)


    # --- Session State Initialization ---
    if 'executed' not in st.session_state:
        st.session_state['executed'] = False
        st.session_state['result_df'] = None
        st.session_state['result_meta'] = {} # Store scalar metrics and context

    # --- Calculation Engine (Runs ONLY on Submit) ---
    if submit_btn:
        st.session_state['executed'] = True
        
        # Load Course Data
        course_data = None
        gpx_path = os.path.join("data", selected_gpx)
        if os.path.exists(gpx_path):
            handler = GPXHandler(gpx_path)
            course_data = handler.to_course_data(smoothing_window_m=smoothing_m)
        else:
            course_data = CourseData.get_ehime_marathon_default()
        
        if target_time_sec is None:
            st.error("目標タイムまたはVDOTの設定を確認してください。")
            st.stop()
            
        # Strategy Calculation
        strategy = PacingStrategy(
            mass_kg=weight, 
            wind_speed_ms=wind_speed, 
            wind_dir_degrees=wind_dir,
            target_time_sec=target_time_sec,
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
            'target_time_sec': target_time_sec, 
            'weight': weight,
            'wind_speed': wind_speed,
            'wind_dir': wind_dir,
            'hill_param': hill_power_param,
            'pacing_pref': pacing_preference,
            'smoothing_m': smoothing_m,
            # Pre-calculate metrics for current course
            'elevation_gain': course_data.calculate_elevation_gain(),
            'difficulty_score': course_data.calculate_difficulty_score()
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
        
        # Summary Metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("シミュレーション結果：予想タイム", formatted_time)
        col1.caption(f"コース: {meta['course_name'].replace('.gpx', '')}")
        
        col2.metric("シミュレーション結果：平均ペース", formatted_pace)
        
        # Flat Equivalent
        base_flat_pace = 1000.0 / meta['base_speed_ms']
        flat_min = int(base_flat_pace // 60)
        flat_sec = int(base_flat_pace % 60)
        col3.metric("基礎走力（平地相当ペース）", f"{flat_min}:{flat_sec:02d}/km")
        col3.caption("このペース感覚を維持してください")

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
            
            map_fig = go.Figure(go.Scattermapbox(
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
                mapbox_style="open-street-map",
                mapbox = dict(
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
        st.dataframe(final_table, use_container_width=True)

        # --- Course Comparison Section ---
        st.divider()
        st.subheader("📊 コース比較")
        st.markdown("現在の設定条件（気象・レース戦略）を維持したまま、別コースのシミュレーション結果と比較します。")
        
        current_course = meta['course_name']
        compare_files = [f for f in gpx_files if f != current_course]
        
        if compare_files:
            compare_gpx = st.selectbox(
                "比較対象のコース", compare_files,
                format_func=lambda x: x.replace(".gpx", "")
            )
            
            if st.button("コース比較を実行", key="compare_btn"):
                # Load comparison course
                comp_gpx_path = os.path.join("data", compare_gpx)
                comp_data = None
                if os.path.exists(comp_gpx_path):
                    comp_handler = GPXHandler(comp_gpx_path)
                    # Use the same smoothing parameter as the current simulation
                    sm_m = meta.get('smoothing_m', 0) # Default to 0 if missing (but should be there)
                    comp_data = comp_handler.to_course_data(smoothing_window_m=sm_m)
                else:
                    comp_data = CourseData.get_ehime_marathon_default()
                
                # Run Strategy
                comp_strategy = PacingStrategy(
                    mass_kg=meta['weight'],
                    wind_speed_ms=meta['wind_speed'],
                    wind_dir_degrees=meta['wind_dir'],
                    target_time_sec=meta['target_time_sec'],
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
                comp_score = comp_data.calculate_difficulty_score()
                
                curr_gain = meta.get('elevation_gain', 0)
                curr_score = meta.get('difficulty_score', 0)
                
                # Display Results with Metrics
                c1, c2 = st.columns(2)
                
                # Current
                c1.markdown(f"### {current_course.replace('.gpx', '')}")
                c1.metric("予想タイム", formatted_time)
                c1.metric("獲得標高", f"{int(curr_gain)}m")
                c1.metric("コース難易度 (Toughness)", f"{curr_score}")
                
                # Comparison
                c2.markdown(f"### {compare_gpx.replace('.gpx', '')}")
                c2.metric("予想タイム", comp_time_fmt, delta=diff_str, delta_color="inverse")
                c2.metric("獲得標高", f"{int(comp_gain)}m", delta=f"{int(comp_gain - curr_gain)}m", delta_color="off")
                c2.metric("コース難易度 (Toughness)", f"{comp_score}", delta=f"{round(comp_score - curr_score, 1)}", delta_color="off")

                
        else:
            st.caption("比較できる他のGPXファイルがありません。")

    else:
        st.info("👈 左側のサイドバーで設定を行い、「シミュレーション実行」ボタンを押してください。")

    # --- Sidebar Info (Manual Summary) ---
    with st.sidebar.expander("📘 アプリの使い方・仕様要約"):
        st.markdown("""
        **1. 基礎走力の設定**
        VDOTまたは目標タイムを入力し、あなたの走力基準を定めます。
        
        **2. コースと環境**
        GPXデータからコースの起伏を読み取ります。
        風速は予報値を入力してください（内部で地表補正されます）。
        ※「詳細設定（開発者用）」で獲得標高の算出基準（平滑化）を調整できます。
        
        **3. レース戦略**
        *   **スプリット**: 前半・後半のペース配分傾向。
        *   **坂道設定**: 上り坂でどれくらい頑張るか（100%基準）。
        
        **4. 結果の見方**
        *   **平均ペース**: 赤い線に従って走ると、設定した戦略通りにレースを展開できます。
        *   **平滑化**: チャートのチェックボックスで、細かい変動をならしてトレンドを確認できます。
        *   **コース比較**: 別のコースと難易度（Toughness）やタイム差を比較できます。
        
        ※ 詳細は同梱の USER_MANUAL.md を参照してください。
        """)

if __name__ == "__main__":
    main()
