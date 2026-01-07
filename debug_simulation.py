import pandas as pd
from lib.course_data import CourseData
from lib.pacing_strategy import PacingStrategy
from lib.gpx_handler import GPXHandler
# from lib.vdot_handler import VDOTHandler # Not needed for this specific check, we assume 3:30 input

def debug_sim():
    print("--- Debugging Simulation Internals ---")
    
    # 1. Load Course
    handler = GPXHandler("data/Ehime-marathon2025.gpx")
    course = handler.to_course_data()
    
    # Check Elevation Stats
    # We need to peek into the GPX or the segments
    rows = []
    for s in course.segments:
        d = vars(s).copy()
        d['distance'] = s.distance
        rows.append(d)
    segments_df = pd.DataFrame(rows)
    print("\n[Course Stats]")
    print(segments_df[['gradient', 'distance']].describe())
    
    # Calc nets
    net_elevation = (segments_df['gradient'] * segments_df['distance'] * 1000).sum()
    print(f"Net Elevation Change (Calc): {net_elevation:.2f} m")
    
    # 2. Run Sim for 3:30:00 Target (Flat Pace: 4:58/km -> ~3.35 m/s)
    target_time_str = "3:30:00"
    target_seconds = 3*3600 + 30*60
    
    print(f"\n[Simulation Target]")
    print(f"Time: {target_time_str} ({target_seconds} sec)")
    
    strategy = PacingStrategy(
        mass_kg=60, 
        vdot=45, # dummy
        wind_speed_ms=0, 
        target_time_sec=target_seconds
    )
    
    print(f"Base Speed (Flat): {strategy.base_speed_ms:.3f} m/s")
    print(f"Target Power: {strategy.target_power:.1f} W")
    
    df = strategy.generate_pace_table(course, interval_meters=1000)
    
    print(f"\n[Result Prediction]")
    total_time = df['time_sec'].sum()
    print(f"Predicted Time: {total_time:.1f} sec ({total_time/3600:.2f} hours)")
    print(f"Diff: {total_time - target_seconds:.1f} sec")
    
    # 3. Analyze Anomalies
    print("\n[Fastest Splits]")
    print(df.sort_values('pace_min_km').head(5)[['km', 'gradient', 'pace_min_km', 'speed_ms']])
    
    print("\n[Slowest Splits]")
    print(df.sort_values('pace_min_km', ascending=False).head(5)[['km', 'gradient', 'pace_min_km', 'speed_ms']])

if __name__ == "__main__":
    debug_sim()
