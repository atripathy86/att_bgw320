from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import os
import re
import ipaddress
import fnmatch
from datetime import datetime

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

    # Convert datetime objects to ISO format strings for JSON serialization
    for result in results:
        for key, value in result.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()

    cursor.close()
    conn.close()
    return results


def wildcard_to_sql_like(pattern: str) -> str:
    """Convert wildcard pattern (* and ?) to SQL LIKE pattern (% and _)"""
    # Escape SQL special characters first
    pattern = pattern.replace('%', '\\%').replace('_', '\\_')
    # Convert wildcards
    pattern = pattern.replace('*', '%').replace('?', '_')
    return pattern


def is_cidr_notation(query: str) -> bool:
    """Check if query is in CIDR notation (e.g., 192.168.1.0/24)"""
    try:
        ipaddress.ip_network(query, strict=False)
        return '/' in query
    except ValueError:
        return False


def ip_in_network(ip: str, network_str: str) -> bool:
    """Check if an IP address is within a network"""
    try:
        network = ipaddress.ip_network(network_str, strict=False)
        ip_obj = ipaddress.ip_address(ip)
        return ip_obj in network
    except ValueError:
        return False


def matches_wildcard(value: str, pattern: str) -> bool:
    """Check if value matches a wildcard pattern using fnmatch"""
    if not value:
        return False
    return fnmatch.fnmatch(value.lower(), pattern.lower())


def search_devices(query: str) -> list:
    """
    Search devices by hostname, IP address, MAC address, or last_seen time.
    Supports wildcards (* and ?) and CIDR notation for IP addresses.
    """
    all_devices = query_devices()
    
    if not query or query.strip() == '':
        return all_devices
    
    query = query.strip()
    matched_devices = []
    
    # Check if it's CIDR notation
    if is_cidr_notation(query):
        for device in all_devices:
            if device.get('ip_address') and ip_in_network(device['ip_address'], query):
                matched_devices.append(device)
        return matched_devices
    
    # Check if query contains wildcards
    has_wildcards = '*' in query or '?' in query
    
    for device in all_devices:
        matched = False
        
        # Check hostname
        hostname = device.get('hostname', '') or ''
        if has_wildcards:
            if matches_wildcard(hostname, query):
                matched = True
        else:
            if query.lower() in hostname.lower():
                matched = True
        
        # Check IP address
        ip_address = device.get('ip_address', '') or ''
        if not matched:
            if has_wildcards:
                if matches_wildcard(ip_address, query):
                    matched = True
            else:
                if query in ip_address:
                    matched = True
        
        # Check MAC address
        mac_address = device.get('mac_address', '') or ''
        if not matched:
            # Normalize MAC address comparison (remove colons/dashes for comparison)
            query_normalized = query.replace(':', '').replace('-', '').lower()
            mac_normalized = mac_address.replace(':', '').replace('-', '').lower()
            if has_wildcards:
                # Also try matching with colons
                if matches_wildcard(mac_address, query) or matches_wildcard(mac_normalized, query_normalized):
                    matched = True
            else:
                if query_normalized in mac_normalized or query.lower() in mac_address.lower():
                    matched = True
        
        # Check last_seen time
        last_seen = device.get('last_seen', '') or ''
        if not matched and last_seen:
            last_seen_str = str(last_seen)
            if has_wildcards:
                if matches_wildcard(last_seen_str, query):
                    matched = True
            else:
                if query in last_seen_str:
                    matched = True
        
        # Check first_seen time
        first_seen = device.get('first_seen', '') or ''
        if not matched and first_seen:
            first_seen_str = str(first_seen)
            if has_wildcards:
                if matches_wildcard(first_seen_str, query):
                    matched = True
            else:
                if query in first_seen_str:
                    matched = True
        
        # Check device type
        device_type = device.get('device_type', '') or ''
        if not matched:
            if has_wildcards:
                if matches_wildcard(device_type, query):
                    matched = True
            else:
                if query.lower() in device_type.lower():
                    matched = True
        
        if matched:
            matched_devices.append(device)
    
    return matched_devices


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the main web UI"""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Device Tracker - Search</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #e0e0e0;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        header {
            text-align: center;
            margin-bottom: 30px;
        }
        
        h1 {
            font-size: 2.5rem;
            color: #00d4ff;
            margin-bottom: 10px;
            text-shadow: 0 0 20px rgba(0, 212, 255, 0.3);
        }
        
        .subtitle {
            color: #888;
            font-size: 0.95rem;
        }
        
        .search-container {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            padding: 25px;
            margin-bottom: 30px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .search-box {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }
        
        #searchInput {
            flex: 1;
            min-width: 250px;
            padding: 15px 20px;
            font-size: 1.1rem;
            border: 2px solid rgba(0, 212, 255, 0.3);
            border-radius: 12px;
            background: rgba(0, 0, 0, 0.3);
            color: #fff;
            outline: none;
            transition: all 0.3s ease;
        }
        
        #searchInput:focus {
            border-color: #00d4ff;
            box-shadow: 0 0 20px rgba(0, 212, 255, 0.2);
        }
        
        #searchInput::placeholder {
            color: #666;
        }
        
        .btn {
            padding: 15px 30px;
            font-size: 1rem;
            font-weight: 600;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #00d4ff 0%, #0099cc 100%);
            color: #000;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(0, 212, 255, 0.3);
        }
        
        .btn-secondary {
            background: rgba(255, 255, 255, 0.1);
            color: #e0e0e0;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.15);
        }
        
        .help-text {
            margin-top: 15px;
            font-size: 0.85rem;
            color: #888;
            line-height: 1.6;
        }
        
        .help-text code {
            background: rgba(0, 212, 255, 0.1);
            padding: 2px 8px;
            border-radius: 4px;
            color: #00d4ff;
            font-family: 'Monaco', 'Consolas', monospace;
        }
        
        .results-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .results-count {
            font-size: 1.1rem;
            color: #888;
        }
        
        .results-count span {
            color: #00d4ff;
            font-weight: 600;
        }
        
        .results-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
        }
        
        .device-card {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: all 0.3s ease;
        }
        
        .device-card:hover {
            transform: translateY(-5px);
            border-color: rgba(0, 212, 255, 0.3);
            box-shadow: 0 15px 40px rgba(0, 0, 0, 0.3);
        }
        
        .device-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 15px;
        }
        
        .device-name {
            font-size: 1.2rem;
            font-weight: 600;
            color: #fff;
            word-break: break-all;
        }
        
        .device-type {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .device-type.wifi {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
        }
        
        .device-type.ethernet {
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            color: #000;
        }
        
        .device-info {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        
        .info-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }
        
        .info-row:last-child {
            border-bottom: none;
        }
        
        .info-label {
            color: #888;
            font-size: 0.85rem;
        }
        
        .info-value {
            color: #e0e0e0;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.9rem;
            text-align: right;
            word-break: break-all;
        }
        
        .info-value.ip {
            color: #00d4ff;
        }
        
        .info-value.mac {
            color: #ffd700;
        }
        
        .no-results {
            text-align: center;
            padding: 60px 20px;
            color: #666;
        }
        
        .no-results-icon {
            font-size: 4rem;
            margin-bottom: 20px;
        }
        
        .loading {
            text-align: center;
            padding: 60px 20px;
        }
        
        .spinner {
            width: 50px;
            height: 50px;
            border: 3px solid rgba(0, 212, 255, 0.1);
            border-top-color: #00d4ff;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .error-message {
            background: rgba(255, 71, 87, 0.1);
            border: 1px solid rgba(255, 71, 87, 0.3);
            border-radius: 12px;
            padding: 20px;
            color: #ff4757;
            text-align: center;
        }
        
        @media (max-width: 600px) {
            h1 {
                font-size: 1.8rem;
            }
            
            .search-box {
                flex-direction: column;
            }
            
            .btn {
                width: 100%;
            }
            
            .results-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔍 Device Tracker</h1>
            <p class="subtitle">Search your network devices by hostname, IP, MAC address, or time</p>
        </header>
        
        <div class="search-container">
            <div class="search-box">
                <input type="text" id="searchInput" placeholder="Enter hostname, IP, MAC, or date/time..." autofocus>
                <button class="btn btn-primary" onclick="performSearch()">Search</button>
                <button class="btn btn-secondary" onclick="showAll()">Show All</button>
            </div>
            <p class="help-text">
                <strong>Search tips:</strong> 
                Use <code>*</code> for wildcards (e.g., <code>192.168.*</code> or <code>*phone*</code>), 
                <code>?</code> for single character, 
                CIDR notation for subnets (e.g., <code>192.168.1.0/24</code>), 
                or partial matches for hostnames, IPs, and MAC addresses.
            </p>
        </div>
        
        <div id="resultsContainer">
            <div class="no-results">
                <div class="no-results-icon">📡</div>
                <p>Enter a search term or click "Show All" to view all devices</p>
            </div>
        </div>
    </div>

    <script>
        const searchInput = document.getElementById('searchInput');
        const resultsContainer = document.getElementById('resultsContainer');
        
        // Search on Enter key
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                performSearch();
            }
        });
        
        async function performSearch() {
            const query = searchInput.value.trim();
            if (!query) {
                showAll();
                return;
            }
            
            showLoading();
            
            try {
                const response = await fetch(`/search?q=${encodeURIComponent(query)}`);
                if (!response.ok) throw new Error('Search failed');
                const devices = await response.json();
                displayResults(devices, query);
            } catch (error) {
                showError(error.message);
            }
        }
        
        async function showAll() {
            showLoading();
            
            try {
                const response = await fetch('/devices');
                if (!response.ok) throw new Error('Failed to fetch devices');
                const devices = await response.json();
                displayResults(devices, null);
            } catch (error) {
                showError(error.message);
            }
        }
        
        function showLoading() {
            resultsContainer.innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Searching devices...</p>
                </div>
            `;
        }
        
        function showError(message) {
            resultsContainer.innerHTML = `
                <div class="error-message">
                    <p>⚠️ ${message}</p>
                    <p>Please try again or check your connection.</p>
                </div>
            `;
        }
        
        function displayResults(devices, searchQuery) {
            if (!devices || devices.length === 0) {
                resultsContainer.innerHTML = `
                    <div class="no-results">
                        <div class="no-results-icon">🔍</div>
                        <p>No devices found${searchQuery ? ' matching "' + escapeHtml(searchQuery) + '"' : ''}</p>
                    </div>
                `;
                return;
            }
            
            const headerText = searchQuery 
                ? `Found <span>${devices.length}</span> device${devices.length !== 1 ? 's' : ''} matching "${escapeHtml(searchQuery)}"`
                : `Showing <span>${devices.length}</span> device${devices.length !== 1 ? 's' : ''}`;
            
            let html = `
                <div class="results-header">
                    <p class="results-count">${headerText}</p>
                </div>
                <div class="results-grid">
            `;
            
            for (const device of devices) {
                const deviceType = (device.device_type || 'unknown').toLowerCase();
                const typeClass = deviceType.includes('wi-fi') || deviceType.includes('wifi') ? 'wifi' : 'ethernet';
                
                html += `
                    <div class="device-card">
                        <div class="device-header">
                            <span class="device-name">${escapeHtml(device.hostname || 'Unknown')}</span>
                            <span class="device-type ${typeClass}">${escapeHtml(device.device_type || 'Unknown')}</span>
                        </div>
                        <div class="device-info">
                            <div class="info-row">
                                <span class="info-label">IP Address</span>
                                <span class="info-value ip">${escapeHtml(device.ip_address || 'N/A')}</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">MAC Address</span>
                                <span class="info-value mac">${escapeHtml(device.mac_address || 'N/A')}</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">First Seen</span>
                                <span class="info-value">${formatDateTime(device.first_seen)}</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">Last Seen</span>
                                <span class="info-value">${formatDateTime(device.last_seen)}</span>
                            </div>
                        </div>
                    </div>
                `;
            }
            
            html += '</div>';
            resultsContainer.innerHTML = html;
        }
        
        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        function formatDateTime(dateStr) {
            if (!dateStr) return 'N/A';
            try {
                const date = new Date(dateStr);
                return date.toLocaleString();
            } catch {
                return dateStr;
            }
        }
    </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)


@app.get("/search")
async def search(q: str = Query(default="", description="Search query")):
    """
    Search devices by hostname, IP address, MAC address, or last_seen time.
    Supports wildcards (* and ?) and CIDR notation (e.g., 192.168.1.0/24).
    """
    devices = search_devices(q)
    return JSONResponse(content=devices)


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
