"""Steps 2-4: audit the files, then ask how bad the air is, when, where and what sets the bad days.

    ./venv/bin/python analyze.py
        -> results/audit.csv  extremes.csv  audit_years.csv  categories.csv  by_year.csv  by_month.csv  counties.csv  concentration.csv  sites.csv  worst_days.csv  daily.csv  summary.csv

Data: EPA AirData daily AQI by county, 2015 to 2025: one row per county per day on which a monitor reported. A county's AQI is the highest of its monitors and pollutants.
A "bad" day is AQI above 100 (unhealthy for sensitive groups or worse). The analysis uses a fixed panel: counties with at least 300 daily values in every year from 2015 to 2025, so
monitors that start or stop do not make the trend. "Other" pollutants are PM10, NO2 and CO.
"""
import zipfile
from pathlib import Path

import pandas as pd
from scipy import stats

HERE = Path(__file__).parent
R = HERE / "results"
YEARS = range(2015, 2026)
BANDS = {"Good": (0, 50), "Moderate": (51, 100), "Unhealthy for Sensitive Groups": (101, 150), "Unhealthy": (151, 200), "Very Unhealthy": (201, 300), "Hazardous": (301, 10 ** 6)}
MIN_DAYS = 300


def load():
    frames = []
    for y in YEARS:
        z = zipfile.ZipFile(HERE / "data" / f"daily_aqi_by_county_{y}.zip"); frames.append(pd.read_csv(z.open(z.namelist()[0]), dtype={"State Code": str, "County Code": str}))
    d = pd.concat(frames, ignore_index=True)
    d.columns = ["state", "county", "scode", "ccode", "date", "aqi", "category", "param", "site", "nsites"]
    d["spaces"] = (d["state"] != d["state"].str.strip()) | (d["county"] != d["county"].str.strip()); d["state"] = d["state"].str.strip(); d["county"] = d["county"].str.strip()
    d["fips"] = d["scode"] + d["ccode"]; d["date"] = pd.to_datetime(d["date"]); d["year"] = d["date"].dt.year; d["month"] = d["date"].dt.month
    d["group"] = d["param"].map({"Ozone": "ozone", "PM2.5": "pm25"}).fillna("other")
    return d


def main():
    R.mkdir(exist_ok=True)
    d = load(); cnt = d.groupby(["fips", "year"]).size().unstack(fill_value=0); panel = cnt.index[(cnt >= MIN_DAYS).all(axis=1)]
    p = d[d["fips"].isin(panel)].copy(); p["bad"] = p["aqi"] > 100; bad = p[p["bad"]]
    ykeys = list(YEARS)

    # Step 2: audit
    mismatch = sum(int(((d["category"] == c) & ((d["aqi"] < lo) | (d["aqi"] > hi))).sum()) for c, (lo, hi) in BANDS.items()); beyond = d[d["aqi"] > 500]
    audit = [("county-days, 2015 to 2025", len(d)), ("duplicate county-days", int(d.duplicated(["fips", "date"]).sum())), ("rows whose category disagrees with their AQI", mismatch),
             ("county-days whose state or county name had stray spaces (trimmed)", int(d["spaces"].sum())), ("county-days with AQI above 500", len(beyond)), ("  of them set by PM10", int((beyond["param"] == "PM10").sum())), ("  of them set by PM2.5", int((beyond["param"] == "PM2.5").sum())),
             ("highest AQI", int(d["aqi"].max())), ("counties with data in any year", d["fips"].nunique()),
             (f"panel counties (at least {MIN_DAYS} days in every year)", len(panel)), ("panel share of all county-days (%)", 100 * len(p) / len(d)), ("states and DC in the panel", p["state"].nunique())]
    pd.DataFrame(audit, columns=["check", "value"]).to_csv(R / "audit.csv", index=False)
    ex = d.sort_values(["aqi", "fips", "date"], ascending=[False, True, True]).head(5)[["state", "county", "fips", "date", "aqi", "param"]].copy(); ex["date"] = ex["date"].dt.strftime("%Y-%m-%d"); ex.to_csv(R / "extremes.csv", index=False)
    ay = d.groupby("year").agg(county_days=("aqi", "size"), counties=("fips", "nunique")).reset_index(); ay["panel_county_days"] = p.groupby("year").size().to_numpy(); ay.to_csv(R / "audit_years.csv", index=False)

    # Step 3: how bad, by year, by month
    cat = p["category"].value_counts().reindex(list(BANDS)).rename_axis("category").reset_index(name="county_days"); cat["share_pct"] = 100 * cat["county_days"] / len(p); cat.round(6).to_csv(R / "categories.csv", index=False)
    by = pd.DataFrame({"year": ykeys}).set_index("year"); by["county_days"] = p.groupby("year").size(); by["bad"] = bad.groupby("year").size(); by["bad_pct"] = 100 * by["bad"] / by["county_days"]
    for g in ("ozone", "pm25", "other"):
        by[f"{g}_bad"] = bad[bad["group"] == g].groupby("year").size().reindex(ykeys, fill_value=0)
    by["pm25_share_of_bad_pct"] = 100 * by["pm25_bad"] / by["bad"]; by["ozone_share_of_bad_pct"] = 100 * by["ozone_bad"] / by["bad"]; by["over_150"] = p[p["aqi"] > 150].groupby("year").size().reindex(ykeys, fill_value=0)
    by.round(6).reset_index().to_csv(R / "by_year.csv", index=False)
    bm = pd.DataFrame({"month": range(1, 13)}).set_index("month"); bm["bad"] = bad.groupby("month").size()
    for g in ("ozone", "pm25", "other"):
        bm[g] = bad[bad["group"] == g].groupby("month").size().reindex(range(1, 13), fill_value=0)
    bm.reset_index().to_csv(R / "by_month.csv", index=False)

    # Step 4: where, how concentrated, how much the number of monitors matters, and the worst days
    c = p.groupby(["state", "county", "fips"]).agg(days=("aqi", "size"), bad=("bad", "sum"), mean_sites=("nsites", "mean")).reset_index()
    for g in ("ozone", "pm25"):
        c[f"{g}_bad"] = c["fips"].map(bad[bad["group"] == g].groupby("fips").size()).fillna(0).astype(int)
    c["bad_pct"] = 100 * c["bad"] / c["days"]; c = c.sort_values(["bad", "fips"], ascending=[False, True]).reset_index(drop=True)
    c["ozone_share_of_bad_pct"] = 100 * c["ozone_bad"] / c["bad"]; c["pm25_share_of_bad_pct"] = 100 * c["pm25_bad"] / c["bad"]
    c.head(15).round(6).to_csv(R / "counties.csv", index=False)
    tot = int(c["bad"].sum()); conc = [{"top_counties": k, "share_of_bad_pct": 100 * c["bad"].head(k).sum() / tot} for k in (10, 20, 50, 100)]
    conc += [{"top_counties": -1, "share_of_bad_pct": 100 * (c["bad"] == 0).sum() / len(c)}]                       # -1: the share of panel counties with no bad day at all
    pd.DataFrame(conc).round(6).to_csv(R / "concentration.csv", index=False)
    p["sites_group"] = pd.cut(p["nsites"], [0, 1, 2, 3, 5, 10 ** 6], labels=["1", "2", "3", "4-5", "6+"])
    sg = p.groupby("sites_group", observed=True).agg(county_days=("aqi", "size"), bad=("bad", "sum")).reset_index(); sg["bad_pct"] = 100 * sg["bad"] / sg["county_days"]; sg.round(6).to_csv(R / "sites.csv", index=False)
    day = p.groupby("date").agg(reporting=("aqi", "size"), over_100=("bad", "sum")); day["over_150"] = p[p["aqi"] > 150].groupby("date").size(); day["over_150"] = day["over_150"].fillna(0).astype(int)
    dd = day.reset_index(); dd["date"] = dd["date"].dt.strftime("%Y-%m-%d"); dd.to_csv(R / "daily.csv", index=False)
    top = day.sort_values(["over_150", "over_100"], ascending=[False, False]).head(10).reset_index(); states, pm = [], []
    for dt in top["date"]:
        w = p[(p["date"] == dt) & (p["aqi"] > 150)]; s = w.groupby("state").size().reset_index(name="n").sort_values(["n", "state"], ascending=[False, True]).head(3)
        states.append("; ".join(f"{a} {b}" for a, b in zip(s["state"], s["n"]))); pm.append(100 * (w["group"] == "pm25").mean())
    top["top_states"] = states; top["pm25_share_pct"] = pm; top["date"] = top["date"].dt.strftime("%Y-%m-%d"); top.round(6).to_csv(R / "worst_days.csv", index=False)
    o150 = p[p["aqi"] > 150]; rho, pv = stats.spearmanr(by.index.to_numpy(), by["bad_pct"].to_numpy())
    summ = {"panel_county_days": len(p), "bad_total": len(bad), "bad_pct": 100 * len(bad) / len(p), "ozone_share_of_bad_pct": 100 * (bad["group"] == "ozone").mean(), "pm25_share_of_bad_pct": 100 * (bad["group"] == "pm25").mean(),
            "other_share_of_bad_pct": 100 * (bad["group"] == "other").mean(), "over_150_total": len(o150), "pm25_share_of_over_150_pct": 100 * (o150["group"] == "pm25").mean(), "ozone_share_of_over_150_pct": 100 * (o150["group"] == "ozone").mean(),
            "june_to_august_share_of_bad_pct": 100 * bad[bad["month"].isin([6, 7, 8])].shape[0] / len(bad), "spearman_year_vs_bad_pct": rho, "spearman_p": pv,
            "panel_counties_with_no_bad_day": int((c["bad"] == 0).sum()), "worst_day_counties_over_150": int(top["over_150"].iloc[0])}
    pd.DataFrame(list(summ.items()), columns=["key", "value"]).round(6).to_csv(R / "summary.csv", index=False)

    for f in ("audit", "audit_years", "categories", "by_year", "by_month", "counties", "concentration", "sites", "worst_days", "summary"):
        print("==", f); print(pd.read_csv(R / f"{f}.csv").round(3).to_string(index=False))


if __name__ == "__main__":
    main()
