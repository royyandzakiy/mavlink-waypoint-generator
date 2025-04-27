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
- Git
- Mission Planner (needed to download the SITL)

### 1. Setup Software in The Loop (SITL)
- Open Mission Planner > `Simulation Tab`
- Choose `Quadplane` & `Plane`. Click ok to download SITL

![sitl_download](docs/sitl_download.png)

- Find folder of SITL, mine is at `%USERPROFILE%\OneDrive\Documents\Mission Planner\sitl\ArduPlane.exe`

![arduplane_exe](docs/arduplane_exe.png)

- Disconnect

- Activate Command Prompt
```bash
# Assign temporary variable
set MY_ARDUPILOT_SITL_FOLDER=%USERPROFILE%\Documents\Mission Planner\sitl

# or, choose this if you have OneDrive installed, your Documents folder probably have moved here
set MY_ARDUPILOT_SITL_FOLDER=%USERPROFILE%\OneDrive\Documents\Mission Planner\sitl

# Activate SITL
"%MY_ARDUPILOT_SITL_FOLDER%\ArduPlane.exe" -Mquadplane -O-35.3633522,149.1652409,587.067920000005,0 -s1 --serial0 tcp:127.0.0.1 --defaults "%MY_ARDUPILOT_SITL_FOLDER%\default_params\quadplane.parm"

# Activate mavproxy to broadcast to different IPs
mavproxy --master tcp:127.0.0.1:5887 --out udp:127.0.0.1:14550 --out udp:127.0.0.1:14552 --out udp:localhost:14601 --out udpin:localhost:14602 --out udpout:localhost:14603 --out udpbcast:192.168.2.255:14700
```

- Connect Mission Planner to the broadcasted MavProxy
    - Choose `UDP`
    - Click on Connect, then fill in this in the port `14552`
    
    ![ardupilot_port](docs/ardupilot_port.png)

- Sidenote: here is to understand the above Ports setup
    - ArduPlane.exe SITL runs on `TCP 127.0.0.1:5887`
    - MavProxy directly connects to SITL at `TCP 127.0.0.1:5887`, MavProxy then broadcasts to all the other Ports
    - MantisGCS connects to `UDP 127.0.0.1:14550`
    - Mission Planner connects to `UDP 127.0.0.1:14552` (optional)
    - QGroundControl connects to `UDP 127.0.0.1:14553` (optional)
    - mavlink-waypoint-generator connect to `UDP 127.0.0.1:14600++`

### 2. Run Project

```bash
# Clone repository
git clone https://github.com/royyandzakiy/mavlink-waypoint-generator.git
cd mavlink-waypoint-generator

# Create virtual environment (do this just once)
python -m venv .venv

# Activate environment
.\.venv\Scripts\activate # .\.venv\Scripts\Activate.ps1 if using powershell

# Upgrade pip
python -m pip install --upgrade pip

# Install required packages
pip install pymavlink numpy

# Run the mission planner:
python run_mission.py
```

### 3. Edit Confugration
Edit `config/mission_params.py` to set your mission parameters:
```
class MissionParams:
    def __init__(self):
        # Shape parameters
        self.shape_type = "circle"  # "circle", "triangle", or "square"
        self.radius_m = 500         # Distance from center to edge in meters
        
        # Pattern parameters
        self.pattern_type = "spiral_out"  # "zigzag", "spiral_out", or "spiral_in"
        self.stripe_separation_m = 100     # Distance between passes in meters
        self.rotation_deg = 45             # Rotation angle in degrees
        
        # Spray parameters
        self.spray_interval_m = 50   # Distance between spray triggers in meters
        self.servo_channel = 6      # PWM output channel (6-9 typically)
        self.servo_pwm = 1900       # PWM value for spray ON (1100-1900)
        
        # MAVLink parameters
        self.altitude = 30          # Mission altitude in meters
        self.connection_string = 'udp:localhost:14603'  # MAVProxy connection
```

### 4. Check Output
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

### Example
##### circle zigzag
![circle_zigzag](docs/circle_zigzag.png)

##### circle_spiralin
![circle_spiralin](docs/circle_spiralin.png)

##### square spiralout
![square_spiralout](docs/square_spiralout.png)