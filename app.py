import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
from lib.course_data import CourseData
from lib.pacing_strategy import PacingStrategy
from lib.gpx_handler import GPXHandler
from lib.vdot_handler import VDOTHandler

st.set_page_config(page_title="愛媛マラソン ペースシミュレーター", layout="wide")

def load_data(gpx_filename):
    # Load VDOT data
    vdot_handler = None
    if os.path.exists("data/VDOT一覧表.csv"):
        vdot_handler = VDOTHandler("data/VDOT一覧表.csv")
    
    # Load Course data (GPX)
    course_data = None
    gpx_path = os.path.join("data", gpx_filename)
    
    if os.path.exists(gpx_path):
        handler = GPXHandler(gpx_path)
        course_data = handler.to_course_data()
    else:
        # Fallback
        course_data = CourseData.get_ehime_marathon_default()
        
    return vdot_handler, course_data

def main():
    st.title("🍊 マラソン ペースシミュレーター")
    st.markdown("物理モデルに基づいたペース配分を計算します。GPXファイルを読み込んでコース特性を反映します。")

    # --- Sidebar Inputs ---
    st.sidebar.header("コース設定")
    
    # Scan for GPX files
    data_dir = "data"
    gpx_files = [f for f in os.listdir(data_dir) if f.endswith(".gpx")]
    if not gpx_files:
        gpx_files = ["Ehime-marathon2025.gpx (Default)"]
        
    # Sort to keep stable (maybe put Ehime first if present?)
    gpx_files.sort()
    
    selected_gpx = st.sidebar.selectbox("コースファイル選択", gpx_files)
    
    vdot_handler, course_data = load_data(selected_gpx)

    st.sidebar.header("ランナー設定")
    # Weight fixed to 60kg as per user request (simplification)
    weight = 60.0
    # st.sidebar.write(f"体重: {weight} kg (固定)") 
    
    # Target Selection
    target_mode = st.sidebar.radio("目標設定モード", ["VDOTから選択", "目標タイムから逆算"])
    
    selected_vdot = 45.0
    
    if vdot_handler:
        if target_mode == "VDOTから選択":
            options = vdot_handler.get_vdot_options()
            # Default index around 45
            default_idx = 0
            if 45 in options: default_idx = options.index(45)
            elif 45.0 in options: default_idx = options.index(45.0)
            
            selected_vdot = st.sidebar.selectbox("VDOT (走力指標)", options, index=default_idx)
            
            # Show predicted time for this VDOT
            pred_time = vdot_handler.get_time_for_vdot(selected_vdot)
            st.sidebar.caption(f"VDOT {selected_vdot} の予想タイム: {pred_time} (平地・無風)")
            
        else: # Time Target
            target_time_str = st.sidebar.text_input("目標タイム (h:mm:ss)", "3:30:00")
            suggested_vdot = vdot_handler.get_closest_vdot(target_time_str)
            st.sidebar.info(f"目標 {target_time_str} に相当する VDOT: {suggested_vdot}")
            selected_vdot = suggested_vdot
    else:
        st.sidebar.error("データフォルダに 'VDOT一覧表.csv' が見つかりません。")
        selected_vdot = st.sidebar.number_input("VDOT (手動入力)", value=45.0)

    st.sidebar.header("気象条件 (予報)")
    temp = st.sidebar.slider("気温 (°C)", 0, 25, 10, help="気温が高いほどパフォーマンスが低下します（実装予定）")
    wind_speed = st.sidebar.slider("風速 (m/s)", 0.0, 10.0, 3.0)
    
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
    wind_label = st.sidebar.selectbox("風向き (風が吹いてくる方角)", list(wind_options.keys()))
    wind_dir = wind_options[wind_label]

    # Strategy Settings
    st.sidebar.subheader("ペース配分戦略")
    
    # Split Strategy
    split_map = {
        "イーブン (一定)": "even",
        "ポジティブ (前半貯金型)": "positive",
        "ネガティブ (後半追い上げ型)": "negative"
    }
    split_label = st.sidebar.selectbox("スプリット配分", list(split_map.keys()))
    pacing_preference = split_map[split_label]
    
    # Hill Strategy
    hill_power_param = st.sidebar.slider(
        "上り坂のパワー設定 (平地比 %)", 
        min_value=70, max_value=130, value=100, step=5,
        help="100%: 一定パワー\n>100%: 上り坂でパワーを上げる（下りで休む）\n<100%: 上り坂で楽をする（下りで稼ぐ）"
    )
    
    # Map input to internal logic? PacingStrategy can take the percent directly.

    # --- Calculation ---
    # Get target time in seconds for the selected VDOT
    target_time_sec = None
    if vdot_handler:
        target_time_sec = vdot_handler.get_seconds_for_vdot(selected_vdot)
    
    # Strategy Calculation
    strategy = PacingStrategy(
        mass_kg=weight, 
        vdot=selected_vdot, 
        wind_speed_ms=wind_speed, 
        wind_dir_degrees=wind_dir,
        target_time_sec=target_time_sec,
        hill_preference=hill_power_param, # New param
        pacing_preference=pacing_preference
    )
    
    # Generate Table (Simulation at 5m intervals for accuracy)
    # データを5m刻みで計算し、短い坂道も反映させます
    df_high_res = strategy.generate_pace_table(course_data, interval_meters=5)
    
    # --- Results ---
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
    col1.metric("予想フィニッシュタイム", formatted_time)
    col1.caption("5m単位で傾斜・風を計算")
    
    col2.metric("平均ペース", formatted_pace)
    
    # Flat Equivalent
    base_flat_pace = 1000.0 / strategy.base_speed_ms
    flat_min = int(base_flat_pace // 60)
    flat_sec = int(base_flat_pace % 60)
    col3.metric("平地換算ペース (VDOT基準)", f"{flat_min}:{flat_sec:02d}/km")
    col3.caption("このペース感覚(強度)を維持してください")

    # --- Charts (Using High Res Data) ---
    st.subheader("ペース戦略チャート")
    
    fig = go.Figure()
    
    # Elevation Approx reconstruction
    elevations = [0]
    for g in df_high_res['gradient']:
        elevations.append(elevations[-1] + (5 * g)) # 5m segments
    df_high_res['elevation_approx'] = elevations[:-1]
    
    # Elevation (Filled Area)
    fig.add_trace(go.Scatter(
        x=df_high_res['km'], y=df_high_res['elevation_approx'], fill='tozeroy', 
        name='コース起伏 (相対標高)', line=dict(color='gray', width=0), opacity=0.2, yaxis='y2'
    ))
    
    # Pace (Line)
    # Smooth the pace line slightly for readability if needed, but 100m is ok
    fig.add_trace(go.Scatter(
        x=df_high_res['km'], y=df_high_res['pace_min_km'], 
        name='推奨ペース (分/km)', line=dict(color='#ff4b4b', width=2)
    ))
    
    fig.update_layout(
        xaxis_title="距離 (km)",
        yaxis=dict(title="ペース (分/km)", range=[df_high_res['pace_min_km'].max()+0.2, df_high_res['pace_min_km'].min()-0.2]), 
        yaxis2=dict(title="相対標高 (m)", overlaying='y', side='right', showgrid=False),
        hovermode="x unified",
        legend=dict(orientation="h", y=1.1)
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- Detailed Table (Aggregated to 1km) ---
    st.subheader("推奨ラップ表 (1km毎)")
    
    # Aggregate 100m chunks into 1km bins
    df_high_res['km_bin'] = df_high_res['km'].apply(np.floor).astype(int)
    
    # Group by km_bin
    # Be careful with the last partial km (42km)
    agg_funcs = {
        'time_sec': 'sum',
        'cumulative_time_sec': 'max',
        'segment_name': lambda x: x.mode()[0] if not x.mode().empty else "" # Most frequent segment name
    }
    
    df_1km = df_high_res.groupby('km_bin').agg(agg_funcs).reset_index()
    
    # Calculate Pace from total time in that bin
    # Most bins are 1km = 1000m. Last bin might be less.
    # We need to know distance in bin.
    # Count rows * 5m? Or just use time.
    # Standard bins are 200 rows (0.000 to 0.995). 
    # Let's verify row count.
    counts = df_high_res.groupby('km_bin').size()
    df_1km['dist_km'] = counts * 0.005 # 5m = 0.005km
    
    # Fix last bin distance if needed (it might be 0.195km -> 2 rows)
    # Actually sample logic goes up to total dist.
    
    df_1km['pace_sec_km'] = df_1km['time_sec'] / df_1km['dist_km']
    
    # Formatting
    df_1km['区間'] = df_1km['km_bin'].astype(str) + " - " + (df_1km['km_bin'] + 1).astype(str) + " km"
    
    # Special handle for last segment display
    # If using standard 42.195, last bin is 42.
    
    df_1km['ラップ'] = df_1km['time_sec'].apply(lambda x: f"{int(x//60)}:{int(x%60):02d}")
    df_1km['通過タイム'] = df_1km['cumulative_time_sec'].apply(lambda x: f"{int(x//3600)}:{int((x%3600)//60):02d}:{int(x%60):02d}")
    
    # Pace string
    def fmt_pace(sec_km):
        m = int(sec_km // 60)
        s = int(sec_km % 60)
        return f"{m}:{s:02d}"
    
    df_1km['推奨ペース'] = df_1km['pace_sec_km'].apply(fmt_pace)

    final_table = df_1km[['区間', 'segment_name', '推奨ペース', 'ラップ', '通過タイム']].rename(columns={
        'segment_name': '特徴'
    })
    
    st.dataframe(final_table, use_container_width=True)

if __name__ == "__main__":
    main()
