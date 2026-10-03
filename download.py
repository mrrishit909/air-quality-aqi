"""Step 1: the US EPA AirData pre-generated "Daily AQI by County" files, 2015 to 2025.

    ./venv/bin/python download.py   -> data/daily_aqi_by_county_<year>.zip (11 files), results/pull.json

US Environmental Protection Agency, AirData (aqs.epa.gov/aqsweb/airdata), files "As of 2026-06-25". US government data, free to use. One row per county per day with a monitor reporting: the day's AQI
(the highest of the pollutants measured), its category, the pollutant that set it, and the number of monitoring sites reporting. EPA states that every AirData AQI summary uses the current AQI
breakpoints (revised for PM2.5 in May 2024) whatever the year, so values are comparable across years. About 1.6 MB per year, so the zips are not committed; this script fetches them.
"""
import hashlib
import json
import ssl
import urllib.request
import zipfile
from datetime import date
from pathlib import Path

import certifi

HERE = Path(__file__).parent
YEARS = range(2015, 2026)
URL = "https://aqs.epa.gov/aqsweb/airdata/daily_aqi_by_county_{}.zip"
CTX = ssl.create_default_context(cafile=certifi.where())


def main():
    (HERE / "data").mkdir(exist_ok=True)
    (HERE / "results").mkdir(exist_ok=True)
    info = {"pulled": date.today().isoformat(), "files": {}}
    for y in YEARS:
        name = f"daily_aqi_by_county_{y}.zip"
        blob = urllib.request.urlopen(urllib.request.Request(URL.format(y), headers={"User-Agent": "research-portfolio (Rishit Raj Mathur)"}), context=CTX, timeout=180).read()
        (HERE / "data" / name).write_bytes(blob)
        z = zipfile.ZipFile(HERE / "data" / name); csv_name = z.namelist()[0]; rows = z.read(csv_name).count(b"\n") - 1
        info["files"][name] = {"url": URL.format(y), "bytes": len(blob), "rows": rows, "sha256": hashlib.sha256(blob).hexdigest()}
    (HERE / "results" / "pull.json").write_text(json.dumps(info, indent=2) + "\n")
    print(json.dumps({k: (v["rows"], v["bytes"]) for k, v in info["files"].items()}, indent=1))


if __name__ == "__main__":
    main()
