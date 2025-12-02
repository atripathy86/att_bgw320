from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os
import re

app = FastAPI()

DB_CONFIG = {
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'password'),
    'host': os.getenv('DB_HOST', 'db'),
    'database': os.getenv('DB_NAME', 'device_tracker'),
    'raise_on_warnings': True
}


def get_db_connection():
    try:
        import mysql.connector
        return mysql.connector.connect(**DB_CONFIG)
    except Exception as err:
        print(f"Database connection error: {err}")
        return None


def query_devices(where_clause=None, params=None):
    conn = get_db_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM devices"
    if where_clause:
        query += f" WHERE {where_clause}"

    cursor.execute(query, params or ())
    results = cursor.fetchall()

    cursor.close()
    conn.close()
    return results


@app.get("/devices")
async def get_all_devices():
    devices = query_devices()
    return JSONResponse(content=devices)


@app.get("/devices/{identifier}")
async def get_device_by_identifier(identifier: str):
    if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', identifier):
        devices = query_devices("ip_address = %s", (identifier,))
        return JSONResponse(content=devices)

    if identifier in ['Ethernet', 'Wi-Fi']:
        devices = query_devices("device_type = %s", (identifier,))
        return JSONResponse(content=devices)

    devices = query_devices("hostname = %s", (identifier,))
    return JSONResponse(content=devices)


if __name__ == '__main__':
    import uvicorn
    port = int(os.getenv('WEB_PORT', '5000'))
    uvicorn.run("webserver:app", host='0.0.0.0', port=port, log_level='info')
