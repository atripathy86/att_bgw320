import requests
from bs4 import BeautifulSoup
import time
import datetime
import re
import sys
import os

# Configuration (overridable via environment variables)
ROUTER_URL = os.getenv('ROUTER_URL', "http://192.168.1.254/cgi-bin/home.ha")
DB_CONFIG = {
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'password'),
    'host': os.getenv('DB_HOST', 'db'),
    'database': os.getenv('DB_NAME', 'device_tracker'),
    'raise_on_warnings': True
}
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', '100'))  # seconds
TIMEOUT = (30, 120) # connect, read

def get_db_connection():
    try:
        # Import here so a lightweight import of this module (for testing parse logic)
        # doesn't require mysql connector to be installed.
        import mysql.connector
        return mysql.connector.connect(**DB_CONFIG)
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        return None

def parse_router_page(html_content):
    devices = []
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find the table with summary="LAN Host Discovery Table"
    table = soup.find('table', summary="LAN Host Discovery Table")
    if not table:
        print("Could not find device table")
        return devices

    # Skip header row
    rows = table.find_all('tr')[1:]
    
    for row in rows:
        cols = row.find_all('td')
        if not cols:
            continue
            
        # Column 0: Device IP Address / Name
        # Format can be: "IP / Hostname" or just "Hostname" (if IP is missing? or just Hostname)
        # Based on file view:
        # "192.168.1.124 / SWNHD..."
        # "unknown00037f12a6a6"
        # "fe80::... / unknown..."
        
        raw_name = cols[0].get_text(strip=True)
        status = cols[1].get_text(strip=True) # on/off
        conn_type = cols[2].get_text(strip=True) # Ethernet/Wi-Fi
        
        ip_address = None
        hostname = None
        mac_address = None
        
        if ' / ' in raw_name:
            parts = raw_name.split(' / ', 1)
            ip_address = parts[0].strip()
            hostname = parts[1].strip()
        else:
            # It might be just a hostname or just an IP?
            # "unknown00037f12a6a6" -> Hostname
            # "NVIDIA" -> Hostname
            # If it looks like an IP, treat as IP?
            # Regex for IP?
            if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', raw_name):
                ip_address = raw_name
                hostname = "Unknown"
            else:
                hostname = raw_name
                ip_address = None # Or maybe we can't find it
        
        # Try to extract MAC from hostname if it follows "unknown<MAC>" pattern
        # Pattern: unknown followed by 12 hex chars
        mac_match = re.search(r'unknown([0-9a-fA-F]{12})', hostname)
        if mac_match:
            mac_address = mac_match.group(1)
            # Format as XX:XX:XX:XX:XX:XX
            mac_address = ':'.join(mac_address[i:i+2] for i in range(0, 12, 2))
        
        # Normalize Type
        if 'Wi-Fi' in conn_type:
            device_type = 'Wi-Fi'
        elif 'Ethernet' in conn_type:
            device_type = 'Ethernet'
        else:
            device_type = conn_type

        devices.append({
            'mac_address': mac_address,
            'hostname': hostname,
            'ip_address': ip_address,
            'device_type': device_type
        })
        
    return devices

def update_database(devices):
    conn = get_db_connection()
    if not conn:
        return

    cursor = conn.cursor()
    now = datetime.datetime.now()

    for device in devices:
        # We use (hostname, ip_address) as unique key based on init.sql
        # But we should handle NULLs. DB might not allow NULL in unique key if not careful, 
        # but in MySQL NULL != NULL.
        # However, our table schema has hostname and ip_address as VARCHAR.
        # If ip_address is None, we should probably store 'Unknown' or similar to ensure uniqueness works if we want it to.
        # Or better, use a query to check existence.
        
        hostname = device['hostname'] or 'Unknown'
        ip = device['ip_address'] or 'Unknown'
        mac = device['mac_address']
        dtype = device['device_type']
        
        # Check if device exists
        query = "SELECT id FROM devices WHERE hostname = %s AND ip_address = %s"
        cursor.execute(query, (hostname, ip))
        result = cursor.fetchone()
        
        if result:
            # Update
            update_query = """
                UPDATE devices 
                SET last_seen = %s, mac_address = COALESCE(%s, mac_address), device_type = %s
                WHERE id = %s
            """
            cursor.execute(update_query, (now, mac, dtype, result[0]))
        else:
            # Insert
            insert_query = """
                INSERT INTO devices (hostname, ip_address, mac_address, device_type, first_seen, last_seen)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (hostname, ip, mac, dtype, now, now))
            
    conn.commit()
    cursor.close()
    conn.close()
    print(f"Updated {len(devices)} devices at {now}")

def main():
    # Wait for DB to be ready
    time.sleep(10) 
    
    while True:
        try:
            print("Fetching router page...")
            response = requests.get(ROUTER_URL, timeout=TIMEOUT)
            response.raise_for_status()
            
            devices = parse_router_page(response.text)
            update_database(devices)
            
        except Exception as e:
            print(f"Error: {e}")
            
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
