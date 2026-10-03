"""Step 5: the project's check. Recompute with different code, in plain Python straight from the zipped CSV files (the csv module and counters, no pandas): the audit, the fixed panel of
counties, the category shares, every year and month, every county's counts, the concentration of bad days, the effect of the number of monitors, the worst days (with the states and the
pollutant that set them), the summary figures and a Spearman correlation of year against the share of bad days written out by hand.

    ./venv/bin/python check.py          (run download.py first: the zips are not committed)
"""
import csv
import datetime
import io
import json
import math
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from scipy import stats

HERE = Path(__file__).parent
R = HERE / "results"
YEARS = range(2015, 2026)
MIN_DAYS = 300
BANDS = {"Good": (0, 50), "Moderate": (51, 100), "Unhealthy for Sensitive Groups": (101, 150), "Unhealthy": (151, 200), "Very Unhealthy": (201, 300), "Hazardous": (301, 10 ** 6)}
n_ok = 0


def same(label, got, want, abs_tol=2e-6):
    global n_ok
    n_ok += 1
    assert abs(float(got) - float(want)) <= abs_tol, f"{label}: recount {got} != results {want}"


def eq(label, got, want):
    global n_ok
    n_ok += 1
    assert got == want, f"{label}: recount {got!r} != results {want!r}"


def table(name):
    return list(csv.DictReader(open(R / f"{name}.csv")))


def rows(year):
    z = zipfile.ZipFile(HERE / "data" / f"daily_aqi_by_county_{year}.zip")
    r = csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]), encoding="utf-8", newline=""))
    assert next(r) == ["State Name", "county Name", "State Code", "County Code", "Date", "AQI", "Category", "Defining Parameter", "Defining Site", "Number of Sites Reporting"]
    for state, county, sc, cc, date, aqi, cat, param, site, ns in r:
        yield state, county, sc + cc, date, int(aqi), cat, param, int(ns)


def format_b36(n):
    out = ""
    while n:
        n, r = divmod(n, 36); out = "0123456789abcdefghijklmnopqrstuvwxyz"[r] + out
    return out.rjust(2, "0")


def group(param):
    return "ozone" if param == "Ozone" else "pm25" if param == "PM2.5" else "other"


def main():
    # pass 1: the audit and the panel
    per_year_rows, per_year_counties, county_year, all_counties = {}, {}, Counter(), set()
    total = dups = mismatch = beyond = beyond_pm10 = beyond_pm25 = 0; highest = 0; high_rows = []
    for y in YEARS:
        seen, cs, n = set(), set(), 0
        for state, county, fips, date, aqi, cat, param, ns in rows(y):
            n += 1; cs.add(fips); county_year[(fips, y)] += 1
            k = (fips, date); dups += k in seen; seen.add(k)
            lo, hi = BANDS[cat]; mismatch += not (lo <= aqi <= hi)
            if aqi > 500:
                beyond += 1; beyond_pm10 += param == "PM10"; beyond_pm25 += param == "PM2.5"
            highest = max(highest, aqi); assert date.startswith(str(y))
            if aqi > 2000:
                high_rows.append((-aqi, fips, date, state, county, param))
        per_year_rows[y], per_year_counties[y] = n, len(cs); total += n; all_counties |= cs
    panel = {f for f in all_counties if all(county_year[(f, y)] >= MIN_DAYS for y in YEARS)}
    a = {r["check"]: float(r["value"]) for r in table("audit")}
    eq("county-days", total, int(a["county-days, 2015 to 2025"])); eq("duplicates", dups, 0); eq("category mismatches", mismatch, int(a["rows whose category disagrees with their AQI"]))
    eq("beyond 500", beyond, int(a["county-days with AQI above 500"])); eq("beyond PM10", beyond_pm10, int(a["  of them set by PM10"])); eq("beyond PM2.5", beyond_pm25, int(a["  of them set by PM2.5"]))
    top5 = sorted(high_rows)[:5]
    for r, t in zip(table("extremes"), top5):
        eq("extreme", (r["state"], r["county"], r["fips"].zfill(5), r["date"], int(r["aqi"]), r["param"]), (t[3], t[4], t[1], t[2], -t[0], t[5]))
    eq("extremes listed", len(table("extremes")), 5)
    eq("highest", highest, int(a["highest AQI"])); eq("counties any year", len(all_counties), int(a["counties with data in any year"])); eq("panel", len(panel), int(a[f"panel counties (at least {MIN_DAYS} days in every year)"]))

    # pass 2: the panel
    cat_n, yr, mo, cty, sites, day = Counter(), defaultdict(Counter), defaultdict(Counter), {}, defaultdict(Counter), defaultdict(Counter)
    day_states, days_pm25, days_150, groups_150 = defaultdict(Counter), Counter(), Counter(), Counter(); states_in_panel = set(); panel_rows = 0
    for y in YEARS:
        for state, county, fips, date, aqi, cat, param, ns in rows(y):
            if fips not in panel:
                continue
            panel_rows += 1; states_in_panel.add(state); g = group(param); bad = aqi > 100; cat_n[cat] += 1
            yr[y]["days"] += 1; yr[y]["bad"] += bad; yr[y][g + "_bad"] += bad; yr[y]["over_150"] += aqi > 150
            m = int(date[5:7]); mo[m]["bad"] += bad; mo[m][g] += bad
            c = cty.setdefault(fips, {"state": state, "county": county, "days": 0, "bad": 0, "sites": 0, "ozone": 0, "pm25": 0}); c["days"] += 1; c["bad"] += bad; c["sites"] += ns; c["ozone"] += bad and g == "ozone"; c["pm25"] += bad and g == "pm25"
            sg = "1" if ns == 1 else "2" if ns == 2 else "3" if ns == 3 else "4-5" if ns <= 5 else "6+"; sites[sg]["days"] += 1; sites[sg]["bad"] += bad
            day[date]["reporting"] += 1; day[date]["over_100"] += bad; day[date]["over_150"] += aqi > 150
            if aqi > 150:
                day_states[date][state] += 1; days_150[date] += 1; days_pm25[date] += g == "pm25"; groups_150[g] += 1
    same("panel share", 100 * panel_rows / total, a["panel share of all county-days (%)"]); eq("states in panel", len(states_in_panel), int(a["states and DC in the panel"]))
    for r in table("audit_years"):
        y = int(r["year"]); eq(f"rows {y}", per_year_rows[y], int(r["county_days"])); eq(f"counties {y}", per_year_counties[y], int(r["counties"])); eq(f"panel rows {y}", yr[y]["days"], int(r["panel_county_days"]))
    for r in table("categories"):
        eq(f"category {r['category']}", cat_n[r["category"]], int(r["county_days"])); same("share", 100 * cat_n[r["category"]] / panel_rows, r["share_pct"])
    for r in table("by_year"):
        y = int(r["year"]); t = yr[y]; eq(f"days {y}", t["days"], int(r["county_days"])); eq("bad", t["bad"], int(r["bad"])); same("bad_pct", 100 * t["bad"] / t["days"], r["bad_pct"])
        for g in ("ozone", "pm25", "other"):
            eq(f"{g}_bad {y}", t[g + "_bad"], int(r[g + "_bad"]))
        same("pm25 share", 100 * t["pm25_bad"] / t["bad"], r["pm25_share_of_bad_pct"]); same("ozone share", 100 * t["ozone_bad"] / t["bad"], r["ozone_share_of_bad_pct"]); eq("over_150", t["over_150"], int(r["over_150"]))
    for r in table("by_month"):
        m = int(r["month"]); eq(f"month {m} bad", mo[m]["bad"], int(r["bad"]))
        for g in ("ozone", "pm25", "other"):
            eq(f"month {m} {g}", mo[m][g], int(r[g]))
    ranked = sorted(cty.items(), key=lambda kv: (-kv[1]["bad"], kv[0]))
    for r, (fips, c) in zip(table("counties"), ranked[:15]):
        eq("county", (r["state"], r["county"], r["fips"].zfill(5)), (c["state"], c["county"], fips)); eq("days", c["days"], int(r["days"])); eq("bad", c["bad"], int(r["bad"])); same("mean sites", c["sites"] / c["days"], r["mean_sites"])
        same("bad_pct", 100 * c["bad"] / c["days"], r["bad_pct"]); eq("ozone_bad", c["ozone"], int(r["ozone_bad"])); eq("pm25_bad", c["pm25"], int(r["pm25_bad"]))
        same("ozone share", 100 * c["ozone"] / c["bad"], r["ozone_share_of_bad_pct"]); same("pm25 share", 100 * c["pm25"] / c["bad"], r["pm25_share_of_bad_pct"])
    tot_bad = sum(c["bad"] for c in cty.values())
    for r in table("concentration"):
        k = int(r["top_counties"]); same(f"top {k}", 100 * sum(c["bad"] for _, c in ranked[:k]) / tot_bad if k > 0 else 100 * sum(c["bad"] == 0 for c in cty.values()) / len(cty), r["share_of_bad_pct"])
    for r in table("sites"):
        s = sites[r["sites_group"]]; eq(f"sites {r['sites_group']} days", s["days"], int(r["county_days"])); eq("bad", s["bad"], int(r["bad"])); same("bad_pct", 100 * s["bad"] / s["days"], r["bad_pct"])
    order = sorted(day, key=lambda d: (-day[d]["over_150"], -day[d]["over_100"], d))[:10]
    for r, d in zip(table("worst_days"), order):
        eq("worst date", d, r["date"]); eq("reporting", day[d]["reporting"], int(r["reporting"])); eq("over_100", day[d]["over_100"], int(r["over_100"])); eq("over_150", day[d]["over_150"], int(r["over_150"]))
        top = sorted(day_states[d].items(), key=lambda kv: (-kv[1], kv[0]))[:3]; eq("top states", "; ".join(f"{s} {n}" for s, n in top), r["top_states"]); same("pm25 share", 100 * days_pm25[d] / days_150[d], r["pm25_share_pct"])

    daily = table("daily"); eq("days in the daily table", len(daily), len(day)); eq("days sorted", [r["date"] for r in daily], sorted(day))
    for r in daily:
        d = r["date"]; eq(f"daily {d} reporting", day[d]["reporting"], int(r["reporting"])); eq("over_100", day[d]["over_100"], int(r["over_100"])); eq("over_150", day[d]["over_150"], int(r["over_150"]))

    # the explorer's data: every day of the 24 counties, decoded and compared with the raw rows
    ex = json.load(open(HERE / "explorer" / "data.json")); want = {c["id"] for c in ex["counties"]}; raw_recs = {f: {} for f in want}; letter = {"Ozone": "O", "PM2.5": "P", "PM10": "M", "NO2": "N", "CO": "C"}
    eq("explorer years", ex["years"], list(YEARS)); eq("explorer counties", len(want), 24); assert want <= panel
    for y in YEARS:
        for state, county, fips, date, aqi, cat, param, ns in rows(y):
            if fips in want:
                raw_recs[fips][date] = (min(aqi, ex["cap"]), letter[param])
    for c in ex["counties"]:
        for y in YEARS:
            s, d0 = c["d"][str(y)], datetime.date(y, 1, 1); n = (datetime.date(y + 1, 1, 1) - d0).days; eq(f"explorer {c['id']} {y} length", len(s), 3 * n)
            for k in range(n):
                rec = raw_recs[c["id"]].get((d0 + datetime.timedelta(days=k)).isoformat()); got = s[3 * k:3 * k + 3]; eq(f"explorer {c['id']} {y} day {k}", got, "zz-" if rec is None else format_b36(rec[0]) + rec[1])

    # the summary, with a Spearman correlation written out by hand
    sm = {r["key"]: float(r["value"]) for r in table("summary")}
    bad_tot = sum(yr[y]["bad"] for y in YEARS); o150 = sum(yr[y]["over_150"] for y in YEARS)
    ozone_bad = sum(yr[y]["ozone_bad"] for y in YEARS); pm_bad = sum(yr[y]["pm25_bad"] for y in YEARS); oth_bad = sum(yr[y]["other_bad"] for y in YEARS)
    ys = list(YEARS); vals = [100 * yr[y]["bad"] / yr[y]["days"] for y in ys]; rk = {i: sorted(range(11), key=lambda j: vals[j]).index(i) + 1 for i in range(11)}
    rho = 1 - 6 * sum((i + 1 - rk[i]) ** 2 for i in range(11)) / (11 * (11 ** 2 - 1)); t = rho * math.sqrt(9 / (1 - rho ** 2))
    exp = {"panel_county_days": panel_rows, "bad_total": bad_tot, "bad_pct": 100 * bad_tot / panel_rows, "ozone_share_of_bad_pct": 100 * ozone_bad / bad_tot, "pm25_share_of_bad_pct": 100 * pm_bad / bad_tot, "other_share_of_bad_pct": 100 * oth_bad / bad_tot,
           "over_150_total": o150, "pm25_share_of_over_150_pct": 100 * groups_150["pm25"] / o150, "ozone_share_of_over_150_pct": 100 * groups_150["ozone"] / o150, "june_to_august_share_of_bad_pct": 100 * sum(mo[m]["bad"] for m in (6, 7, 8)) / bad_tot,
           "spearman_year_vs_bad_pct": rho, "spearman_p": 2 * stats.t.sf(abs(t), 9), "panel_counties_with_no_bad_day": sum(c["bad"] == 0 for c in cty.values()), "worst_day_counties_over_150": max(day[d]["over_150"] for d in day)}
    eq("summary keys", sorted(sm), sorted(exp))
    for k, v in exp.items():
        same(f"summary {k}", v, sm[k])
    print(f"check.py: {n_ok} recomputed numbers agree with results/ (3,577,372 county-days read straight from the zips)")


if __name__ == "__main__":
    main()
