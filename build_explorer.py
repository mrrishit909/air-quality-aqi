"""Step 7: the data for the explorer page (explorer/index.html).

    ./venv/bin/python build_explorer.py   -> explorer/data.json

24 counties from the fixed panel, every day of 2015 to 2025. Each county and year is one string with three characters per day of the year: the AQI in base 36 (two characters,
capped at 501, which the page shows as "over 500"), then one letter for the pollutant that set it: O ozone, P PM2.5, M PM10, N NO2, C CO. A day with no record is "zz-".
"""
import json
import zipfile
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
YEARS = list(range(2015, 2026))
COUNTIES = [("06037", "Los Angeles, California"), ("06071", "San Bernardino, California"), ("06065", "Riverside, California"), ("06029", "Kern, California"), ("06019", "Fresno, California"),
            ("06073", "San Diego, California"), ("06067", "Sacramento, California"), ("06051", "Mono, California"), ("04013", "Maricopa, Arizona"), ("48201", "Harris, Texas"),
            ("17031", "Cook, Illinois"), ("36061", "New York, New York"), ("42101", "Philadelphia, Pennsylvania"), ("42003", "Allegheny, Pennsylvania"), ("26163", "Wayne, Michigan"),
            ("13121", "Fulton, Georgia"), ("12086", "Miami-Dade, Florida"), ("49035", "Salt Lake, Utah"), ("53033", "King, Washington"), ("41051", "Multnomah, Oregon"),
            ("08031", "Denver, Colorado"), ("25025", "Suffolk, Massachusetts"), ("11001", "District of Columbia"), ("02090", "Fairbanks North Star, Alaska")]
LETTER = {"Ozone": "O", "PM2.5": "P", "PM10": "M", "NO2": "N", "CO": "C"}
CAP = 501


def b36(n):
    s = ""
    while n:
        n, r = divmod(n, 36); s = "0123456789abcdefghijklmnopqrstuvwxyz"[r] + s
    return s.rjust(2, "0")


def main():
    out = {"years": YEARS, "cap": CAP, "counties": []}; want = {f for f, _ in COUNTIES}; recs = {f: {} for f in want}
    for y in YEARS:
        z = zipfile.ZipFile(HERE / "data" / f"daily_aqi_by_county_{y}.zip"); d = pd.read_csv(z.open(z.namelist()[0]), dtype={"State Code": str, "County Code": str}); d["fips"] = d["State Code"] + d["County Code"]
        for r in d[d["fips"].isin(want)].itertuples(index=False):
            recs[r.fips][r.Date] = (min(int(r.AQI), CAP), LETTER[r._7])
    for fips, name in COUNTIES:
        years = {}
        for y in YEARS:
            s, d0 = [], date(y, 1, 1)
            for k in range((date(y + 1, 1, 1) - d0).days):
                a = recs[fips].get((d0 + timedelta(days=k)).isoformat()); s.append(b36(a[0]) + a[1] if a else "zz-")
            years[str(y)] = "".join(s)
        out["counties"].append({"id": fips, "name": name, "d": years})
    (HERE / "explorer").mkdir(exist_ok=True); (HERE / "explorer" / "data.json").write_text(json.dumps(out, separators=(",", ":")))
    print(len(json.dumps(out, separators=(",", ":"))), "bytes;", {c["name"]: sum(v.count("zz-") for v in c["d"].values()) for c in out["counties"]})


if __name__ == "__main__":
    main()
