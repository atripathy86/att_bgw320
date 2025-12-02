# AT&T BGW320 Device Tracker

This project parses the AT&T BGW320 router status page, extracts the "LAN Host Discovery Table" (connected devices), stores device records in a MariaDB database, and exposes a simple HTTP API to query devices.

**Main features**
- **Parser**: `parser.py` — fetches the router page, parses the device table, and updates the `devices` table in the database periodically.
- **API server**: `webserver.py` — a Flask app exposing `/devices` and `/devices/<identifier>` endpoints to query devices by hostname, IP, or type.
- **Markdown generator**: `generate_table.py` — converts a tab-separated `device_list.txt` into a markdown table `device_table.md` (note: it uses a hard-coded input/output path by default).
- **DB init**: `init.sql` — initial SQL used by the MariaDB container to create the `device_tracker` database and `devices` table.
- **Containerized**: `Dockerfile` and `docker-compose.yml` to run the parser, webserver, and a MariaDB instance.

**Repository layout**
- `parser.py` — router page scraper + DB updater (main background job).
- `webserver.py` — Flask API for querying devices.
- `generate_table.py` — script that converts a device list into markdown.
- `device_list.txt` — sample/raw tab-separated device data.
- `device_table.md` — example generated markdown table.
- `home.ha.html` — sample router HTML used for reference and testing the parser.
- `init.sql` — DB schema and create statements for `device_tracker`.
- `Dockerfile` / `docker-compose.yml` — compose configuration to run `db`, `parser`, and `webserver` services.
- `requirements.txt` — Python dependencies: `requests`, `beautifulsoup4`, `mysql-connector-python`, `flask`.

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
- API will be available at http://localhost:5000/devices

3. Query devices via HTTP:

```bash
# all devices
curl http://localhost:5000/devices

# device by hostname, ip, or type (e.g. "192.168.2.119" or "Ethernet")
curl http://localhost:5000/devices/raspberrypi
curl http://localhost:5000/devices/192.168.2.119
curl http://localhost:5000/devices/Ethernet
```

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
- No authentication is implemented for the Flask API; consider adding auth if exposing to untrusted networks.


