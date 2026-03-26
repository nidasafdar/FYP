import psycopg2
from config import DB_CONFIG

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    print("Dropping existing 'detections' table to fix schema mismatch...")
    cur.execute("DROP TABLE IF EXISTS detections;")
    
    print("Creating 'detections' table with correct schema...")
    cur.execute("""
        CREATE TABLE detections (
            id SERIAL PRIMARY KEY,
            track_id INT,
            object_class VARCHAR(20),
            confidence FLOAT,
            bbox_x1 INT,
            bbox_y1 INT,
            bbox_x2 INT,
            bbox_y2 INT,
            frame_number INT,
            timestamp TIMESTAMP,
            camera_id VARCHAR(50),
            direction VARCHAR(10)
        );
    """)
    
    conn.commit()
    print("✅ Table recreated successfully with 'direction' column!")
    
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'detections'")
    cols = cur.fetchall()
    print(f"Verified Columns: {[c[0] for c in cols]}")
    
    conn.close()
except Exception as e:
    print(f"❌ Error: {e}")
