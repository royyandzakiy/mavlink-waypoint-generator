from fastapi import FastAPI
from fastapi.responses import StreamingResponse, HTMLResponse
import threading
import time
from pymavlink import mavutil
from tabulate import tabulate

app = FastAPI()

# Global connection object
# connect_str = 'tcp:127.0.0.1:5887'
# connect_str = 'udpin:127.0.0.1:14550'
connect_str = 'udpout:127.0.0.1:14552'
# connect_str = 'udpbcast:127.0.0.1:14553'
# connect_str = 'udp:127.0.0.1:14600'
# connect_str = 'udp:localhost:14601'

# connect_str = 'udp:127.0.0.1:14552'
connection = mavutil.mavlink_connection(connect_str)