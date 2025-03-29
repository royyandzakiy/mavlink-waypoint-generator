# Agricultural Drone Mission Planner

A Python-based system for generating and uploading complex agricultural spraying patterns to drones using MAVLink.

## Features

- Multiple shape patterns (circle, square, triangle)
- Different coverage styles (zigzag, inward/outward spiral)
- Precise spray control with configurable intervals
- MAVLink integration for ArduPilot/PX4 compatible drones
- Easy-to-configure parameters

## Getting Started

### Prerequisites

- Windows 10/11
- Python 3.8 or newer
- Git (optional)

### 1. Setup Virtual Environment

```powershell
# Create project directory
mkdir agri-drone-mission
cd agri-drone-mission

# Create virtual environment
python -m venv venv

# Activate environment
.\venv\Scripts\activate

# Upgrade pip
python -m pip install --upgrade pip

# Install required packages
pip install pymavlink numpy

# Clone repository (if using Git)
git clone https://github.com/royyandzakiy/ardupilot_mavlink_fastapi
cd agri-drone-mission

# Run the mission planner:
python run_mission.py
```

### 2. Edit Confugration
Edit `config/mission_params.py` to set your mission parameters:
```
class MissionParams:
    def __init__(self):
        # Shape parameters
        self.shape_type = "circle"  # "circle", "triangle", or "square"
        self.radius_m = 50         # Distance from center to edge in meters
        
        # Pattern parameters
        self.pattern_type = "spiral_out"  # "zigzag", "spiral_out", or "spiral_in"
        self.stripe_separation_m = 10     # Distance between passes in meters
        self.rotation_deg = 0             # Rotation angle in degrees
        
        # Spray parameters
        self.spray_interval_m = 5   # Distance between spray triggers in meters
        self.servo_channel = 6      # PWM output channel (6-9 typically)
        self.servo_pwm = 1900       # PWM value for spray ON (1100-1900)
        
        # MAVLink parameters
        self.altitude = 30          # Mission altitude in meters
        self.connection_string = 'udp:localhost:14603'  # MAVProxy connection
```

### 3. Check Output
```bash
Waiting for heartbeat...
Heartbeat received!
Cleared existing mission.
Sent waypoint count: 127
Sending navigation waypoint 0...
Sending spray waypoint 1...
...
Mission uploaded successfully!
```

### Misc
