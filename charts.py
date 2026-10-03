"""Step 6: charts.   ./venv/bin/python charts.py -> charts/00_cover.png, 01_years.png, 02_months.png, 03_counties.png, 04_sites.png, 05_days.png"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).parent
R = HERE / "results"
INK, DIM, GRID, BG, BLUE, ORANGE, GRAY, GREEN = "#f2f2f0", "#8a8a87", "#1d1d1d", "#0b0b0b", "#3987e5", "#d95926", "#9a9a96", "#3aa876"
plt.rcParams.update({"figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG, "text.color": INK,
                     "axes.edgecolor": "#3a3a3a", "axes.labelcolor": DIM, "xtick.color": DIM, "ytick.color": DIM,
                     "axes.grid": True, "axes.axisbelow": True, "grid.color": GRID, "grid.linewidth": 1,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "font.family": ["Helvetica Neue", "Arial", "DejaVu Sans"], "font.size": 11, "axes.titlesize": 13,
                     "axes.titlelocation": "left", "axes.titlepad": 12})
COLORS = {"ozone": ORANGE, "pm25": BLUE, "other": GRAY}
LABELS = {"ozone": "ozone", "pm25": "PM2.5 (smoke, dust, soot)", "other": "other (PM10, NO2, CO)"}


def save(fig, name):
    fig.tight_layout(); fig.savefig(HERE / "charts" / name, dpi=150); plt.close(fig)


def stacked(ax, x, parts, labels=True):
    bottom = np.zeros(len(x))
    for g in ("ozone", "pm25", "other"):
        v = np.asarray(parts[g], float); ax.bar(x, v, bottom=bottom, color=COLORS[g], width=0.72, label=LABELS[g] if labels else None); bottom += v
    return bottom


def years(ax):
    b = pd.read_csv(R / "by_year.csv"); top = stacked(ax, b["year"], {"ozone": b["ozone_bad"], "pm25": b["pm25_bad"], "other": b["other_bad"]})
    for x, t, pct in zip(b["year"], top, b["bad_pct"]):
        ax.text(x, t + 60, f"{pct:.1f}%", ha="center", color=INK, fontsize=9)
    ax.set_xticks(b["year"]); ax.set_ylim(0, top.max() * 1.12); ax.set_ylabel("county-days above 100"); ax.grid(axis="x", visible=False); ax.legend(frameon=False, labelcolor=INK, fontsize=9, loc="upper left", ncol=3)
    ax.set_title("Bad days by year (labels: share of all county-days), 609 counties")


def months(ax):
    b = pd.read_csv(R / "by_month.csv"); top = stacked(ax, b["month"], {"ozone": b["ozone"], "pm25": b["pm25"], "other": b["other"]})
    ax.set_xticks(b["month"]); ax.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]); ax.set_ylabel("county-days above 100, 2015 to 2025"); ax.grid(axis="x", visible=False)
    ax.legend(frameon=False, labelcolor=INK, fontsize=9, loc="upper left"); ax.set_title("Bad days by month")


def counties(ax, n=12):
    c = pd.read_csv(R / "counties.csv").head(n).iloc[::-1].reset_index(drop=True); y = np.arange(len(c)); other = c["bad"] - c["ozone_bad"] - c["pm25_bad"]
    stacked_h = np.zeros(len(c))
    for g, v in (("ozone", c["ozone_bad"]), ("pm25", c["pm25_bad"]), ("other", other)):
        ax.barh(y, v, left=stacked_h, color=COLORS[g], height=0.66, label=LABELS[g]); stacked_h += v.to_numpy()
    ab = {"California": "CA", "Arizona": "AZ", "Alaska": "AK", "Texas": "TX"}
    for yi, (_, r) in zip(y, c.iterrows()):
        ax.text(r["bad"] + 20, yi, f"{int(r['bad']):,}  ·  {r['mean_sites']:.0f} sites", va="center", color=INK, fontsize=8.5)
    ax.set_yticks(y); ax.set_yticklabels([f"{r['county']} {ab.get(r['state'], r['state'])}" for _, r in c.iterrows()]); ax.set_xlim(0, c["bad"].max() * 1.28); ax.grid(axis="y", visible=False)
    ax.set_xlabel("county-days above 100, 2015 to 2025 (each county reported on 4,018 days)"); ax.legend(frameon=False, labelcolor=INK, fontsize=9, loc="lower right"); ax.set_title(f"The {n} counties with the most bad days")


def sites(ax):
    s = pd.read_csv(R / "sites.csv"); ax.bar(range(len(s)), s["bad_pct"], color=BLUE, width=0.62)
    for i, v in enumerate(s["bad_pct"]):
        ax.text(i, v + 0.12, f"{v:.1f}%", ha="center", color=INK, fontsize=10)
    ax.set_xticks(range(len(s))); ax.set_xticklabels([f"{g} site{'s' if g != '1' else ''}" for g in s["sites_group"]]); ax.set_ylabel("% of county-days above 100"); ax.grid(axis="x", visible=False); ax.set_ylim(0, s["bad_pct"].max() * 1.15)
    ax.set_title("More monitors in a county, more bad days"); ax.set_xlabel("monitoring sites reporting that day in the county")


def days(ax):
    d = pd.read_csv(R / "daily.csv", parse_dates=["date"]); e = d[d["over_150"] > 0]; ax.vlines(e["date"], 0, e["over_150"], color=ORANGE, linewidth=1.0)
    w = pd.read_csv(R / "worst_days.csv", parse_dates=["date"])
    for dt, label, dx, dy in ((pd.Timestamp("2020-09-14"), "14 Sep 2020", -45, 6), (pd.Timestamp("2023-06-29"), "29 Jun 2023", -45, 6)):
        n = int(d.loc[d["date"] == dt, "over_150"].iloc[0]); ax.annotate(f"{label}: {n} counties", (dt, n), xytext=(dt + pd.Timedelta(days=-300 if dt.year == 2023 else 40), n + 6), color=INK, fontsize=9, arrowprops={"arrowstyle": "-", "color": INK, "linewidth": 0.8})
    ax.set_ylabel("counties above 150 that day"); ax.set_ylim(0, 135); ax.grid(axis="x", visible=False); ax.set_title("The worst days: counties with an AQI above 150, of 609 monitored")


def main():
    (HERE / "charts").mkdir(exist_ok=True)
    fig, (a, b) = plt.subplots(1, 2, figsize=(14, 8), gridspec_kw={"width_ratios": [1, 1.15]})
    months(a); counties(b, 10)
    for ax in (a, b):
        ax.title.set_fontsize(15)
    fig.suptitle("When does the air turn unhealthy? Rarely, in summer, in a few places, on a few days", x=0.01, ha="left", fontsize=20, color=INK, y=0.98)
    fig.tight_layout(rect=(0, 0, 1, 0.94)); fig.savefig(HERE / "charts" / "00_cover.png", dpi=100); plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 3.8)); years(ax); save(fig, "01_years.png")
    fig, ax = plt.subplots(figsize=(10, 3.6)); months(ax); save(fig, "02_months.png")
    fig, ax = plt.subplots(figsize=(10, 4.4)); counties(ax, 12); save(fig, "03_counties.png")
    fig, ax = plt.subplots(figsize=(10, 3.4)); sites(ax); save(fig, "04_sites.png")
    fig, ax = plt.subplots(figsize=(10, 3.6)); days(ax); save(fig, "05_days.png")


if __name__ == "__main__":
    main()
