from lib.physics import RunningPhysics
import numpy as np

def test_wind():
    mass = 60.0
    vdot = 45.0
    # Base Speed (approx 4hr marathon -> 10.5 km/h -> 2.9 m/s)
    base_speed = 2.9
    
    # Calculate target power with 0 wind
    target_power = RunningPhysics.calculate_total_power(base_speed, 0.0, 0.0, mass)
    print(f"Target Power (0 wind): {target_power:.2f} W")
    
    winds = [-5.0, -2.0, 0.0, 2.0, 5.0] # m/s (Negative=Headwind, Positive=Tailwind)
    
    print(f"{'Wind (m/s)':<12} | {'Speed (m/s)':<12} | {'Pace (min/km)':<15} | {'Diff vs 0'}")
    print("-" * 60)
    
    for w in winds:
        speed = RunningPhysics.solve_speed_for_power(target_power, 0.0, w, mass)
        pace = (1000.0 / speed) / 60.0 # min/km
        diff = speed - base_speed
        
        note = ""
        if w == 0.0: note = " (Baseline)"
        elif diff > 0: note = " (Faster)"
        elif diff < 0: note = " (Slower)"
        
        print(f"{w:<12.1f} | {speed:<12.3f} | {pace:<15.2f} | {note}")

if __name__ == "__main__":
    test_wind()
