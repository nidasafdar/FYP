from rush_detection import RushDetection
import time

rd = RushDetection()

# Run continuously like real system
while True:

    rd.detect_rush("gate1", minutes=5)

    time.sleep(10)  # check every 10 seconds