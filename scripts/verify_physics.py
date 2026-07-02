from lib.physics import RunningPhysics

def verify():
    mass = 65.0
    vdot = 45 # Sub 3.5 runner approx
    
    # Base Condition: Flat, No Wind
    base_speed = RunningPhysics.vdot_to_flat_velocity(vdot)
    base_power = RunningPhysics.calculate_total_power(base_speed, 0.0, 0.0, mass)
    
    print(f"--- Base Baseline (VDOT {vdot}, Mass {mass}kg) ---")
    print(f"Speed: {base_speed:.3f} m/s ({1000/base_speed/60:.2f} min/km)")
    print(f"Metabolic Power: {base_power:.1f} Watts ({(base_power/mass):.2f} W/kg)")
    print("-" * 30)
    
    scenarios = [
        ("Flat, No Wind", 0.0, 0.0),
        ("Uphill +3% (Hirata)", 0.03, 0.0),
        ("Uphill +5% (Steep)", 0.05, 0.0),
        ("Downhill -3%", -0.03, 0.0),
        ("Headwind 3m/s", 0.0, -3.0),
        ("Headwind 5m/s (Strong)", 0.0, -5.0),
        ("Tailwind 3m/s", 0.0, 3.0),
        ("Uphill +3% & Headwind 3m/s", 0.03, -3.0),
    ]
    
    print(f"{'Scenario':<30} | {'Speed (m/s)':<12} | {'Pace (min/km)':<15} | {'Diff'}")
    print("-" * 75)
    
    for name, grad, wind in scenarios:
        v = RunningPhysics.solve_speed_for_power(base_power, grad, wind, mass)
        pace_min_km = 1000 / v / 60
        diff_percent = (v - base_speed) / base_speed * 100
        print(f"{name:<30} | {v:.3f}        | {pace_min_km:.2f}           | {diff_percent:+.1f}%")

if __name__ == "__main__":
    verify()
