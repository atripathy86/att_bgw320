# AT&T BGW320 Device Tracker

This project parses the AT&T BGW320 router status page, extracts the "LAN Host Discovery Table" (connected devices), stores device records in a MariaDB database, and exposes a simple HTTP API and Web UI to query devices.

**Main features**
- **Parser**: `parser.py` — fetches the router page, parses the device table, and updates the `devices` table in the database periodically.
- **API server**: `webserver.py` — a FastAPI app exposing `/devices`, `/devices/<identifier>`, and `/search` endpoints to query devices by hostname, IP, MAC, or type.
- **Web UI (React)**: Modern, separate React-based frontend at port `3000` for searching and viewing devices with a professional, themed interface.
- **Legacy Web UI**: Built-in web interface at `/` (on port `5000`) for searching devices.
- **Markdown generator**: `generate_table.py` — converts a tab-separated `device_list.txt` into a markdown table `device_table.md` (note: it uses a hard-coded input/output path by default).
- **DB init**: `init.sql` — initial SQL used by the MariaDB container to create the `device_tracker` database and `devices` table.
- **Containerized**: `Dockerfile` and `docker-compose.yml` to run the parser, webserver, and a MariaDB instance.

**Repository layout**
- `parser.py` — router page scraper + DB updater (main background job).
- `webserver.py` — FastAPI server with REST API and legacy Web UI.
- `ui/` — React application source code and Docker configuration for the new Web UI.
- `generate_table.py` — script that converts a device list into markdown.
- `device_list.txt` — sample/raw tab-separated device data.
- `device_table.md` — example generated markdown table.
- `home.ha.html` — sample router HTML used for reference and testing the parser.
- `init.sql` — DB schema and create statements for `device_tracker`.
- `Dockerfile` / `docker-compose.yml` — compose configuration to run `db`, `parser`, and `webserver` services.
- `requirements.txt` — Python dependencies: `requests`, `beautifulsoup4`, `mysql-connector-python`, `fastapi`, `uvicorn`.

**Quick start (Docker Compose)**
1. Copy .env-example to .env and update values as needed.
2. Build and start the stack (from project root):

```bash
docker-compose up --build
```

3. Services started by `docker-compose.yml`:
- `db` (MariaDB) on port `3306` with `MYSQL_ROOT_PASSWORD=password` (see `docker-compose.yml`).
- `parser` runs `parser.py` and depends on `db`.
- `webserver` runs `webserver.py` and exposes port `5000`.
- `ui` runs the React Web UI and exposes port `3000`.
- React Web UI available at http://localhost:3000/
- Legacy Web UI available at http://localhost:5000/
- API available at http://localhost:5000/devices (and proxied via http://localhost:3000/api/devices)

3. Query devices via HTTP:

```bash
# all devices
curl http://localhost:5000/devices

# device by hostname, ip, or type (e.g. "192.168.2.119" or "Ethernet")
curl http://localhost:5000/devices/raspberrypi
curl http://localhost:5000/devices/192.168.2.119
curl http://localhost:5000/devices/Ethernet

# search with wildcards, partial matches, or CIDR notation
curl "http://localhost:5000/search?q=192.168.*"
curl "http://localhost:5000/search?q=*phone*"
curl "http://localhost:5000/search?q=192.168.1.0/24"
curl "http://localhost:5000/search?q=aa:bb:cc"
```

**React Web UI Features**
The new React-based UI at `http://localhost:3000` offers a modern experience:
- **Professional Design**: Dark theme with neon accents and responsive layout.
- **Advanced Search**: Supports wildcards (`*`, `?`), CIDR notation, and partial matches.
- **Visual Feedback**: Loading states, error handling, and "no results" indicators.
- **Device Details**: Pretty formatting for IP, MAC, and timestamps, with visual indicators for connection type (Wi-Fi vs Ethernet).

**Legacy Web UI Search Features**
The built-in web interface at `http://localhost:5000/` supports:
- **Wildcards**: Use `*` for multiple characters, `?` for single character (e.g., `*phone*`, `192.168.1.?`)
- **CIDR notation**: Search by subnet (e.g., `192.168.1.0/24`, `10.0.0.0/8`)
- **Partial matches**: Match any part of hostname, IP, MAC address, or timestamps
- **MAC address**: Search by full or partial MAC (with or without colons)
- **Date/time**: Search by first_seen or last_seen timestamps

**Local (non-container) setup**

1. Create or ensure a MariaDB/MySQL database exists and run `init.sql` to create the `devices` table.
2. Install Python deps:

```bash
python3 -m pip install -r requirements.txt
```

3. Edit database configuration in `parser.py` and `webserver.py` (the `DB_CONFIG` dictionaries) if necessary.

4. Run `parser.py` in background and `webserver.py` for the API:

```bash
python3 parser.py &
python3 webserver.py
```

**Important configuration notes**
- The router URL used by the parser is configured in `parser.py` via the `ROUTER_URL` constant (default `http://192.168.1.254/cgi-bin/home.ha`). Update it to match your router's status page address.
- Database credentials are set to `root`/`password` in the provided configs for convenience; change them for production use.
- `generate_table.py` uses an absolute path (`/home/aalap/ip_Addresses/device_list.txt`) by default — update the script if you want it to read `device_list.txt` from the repo root.
- `init.sql` creates a `UNIQUE KEY unique_device (hostname, ip_address)` which treats the pair as unique. The parser uses hostname + ip to decide insert vs update.

Environment variables (recommended)
- `DB_HOST` (default `db`)
- `DB_USER` (default `root`)
- `DB_PASSWORD` (default `password`)
- `DB_NAME` (default `device_tracker`)
- `ROUTER_URL` (default `http://192.168.1.254/cgi-bin/home.ha`)
- `POLL_INTERVAL` (seconds, default `100`)

`parser.py` and `webserver.py` now read the DB and router configuration from these environment variables with the defaults above.

**Notes / caveats**
- The parser relies on HTML structure (a table with `summary="LAN Host Discovery Table"`). Router firmware updates may change that structure and break parsing.
- IP matching in the API is a simple regex; some IPv6 addresses may not be recognized by the simplistic check.
- No authentication is implemented for the API; consider adding auth if exposing to untrusted networks.

## React UI Technical Details

### Tech Stack & Dependencies
The new Web UI is built with a modern React stack:
- **Build Tool**: [Vite](https://vitejs.dev/)
- **Styling**: [Tailwind CSS](https://tailwindcss.com/)
- **HTTP Client**: [Axios](https://axios-http.com/)
- **Icons**: [React Icons](https://react-icons.github.io/react-icons/)
- **Animations**: [Framer Motion](https://www.framer.com/motion/)

### Architecture & Configuration
- **Docker**: The UI is built as a static site (Node.js build stage) and served via **Nginx** (Alpine image).
- **Nginx Proxy**: The Nginx configuration (`ui/nginx.conf`) serves the React app and proxies `/api` requests to the `webserver` container on port 5000.
- **CORS**: The backend (`webserver.py`) uses `CORSMiddleware` to allow cross-origin requests (`allow_origins=["*"]`), enabling the UI to communicate with the API even when running on different ports during development.

### Source Structure
- `ui/src/App.jsx`: Main application component containing:
    - Search state management
    - API integration logic
    - **SearchBar**: Input field with wildcard/CIDR support
    - **ResultList/ResultItem**: Grid display of device cards with animations
- `ui/src/index.css`: Tailwind directives and global theme styles
- `ui/tailwind.config.js`: Custom theme configuration (Primary Cyan `#00d4ff`, Dark Background)


