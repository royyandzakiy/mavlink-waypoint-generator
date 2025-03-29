# Master control parameters
class MissionParams:
    def __init__(self):
        # Shape parameters
        self.shape_type = "circle"  # "circle", "triangle", or "square"
        self.radius_m = 500  # Distance from center to edge in meters
        
        # Pattern parameters
        self.pattern_type = "spiral_out"  # "zigzag", "spiral_out", or "spiral_in"
        self.stripe_separation_m = 100  # Distance between passes in meters
        self.rotation_deg = 45  # Rotation angle in degrees
        
        # Spray parameters
        self.spray_interval_m = 50  # Distance between spray triggers in meters
        self.servo_channel = 6  # PWM output channel
        self.servo_pwm = 1900  # PWM value for spray ON (1100-1900)
        
        # MAVLink parameters
        self.altitude = 30  # Mission altitude in meters
        self.connection_string = 'udp:localhost:14603'