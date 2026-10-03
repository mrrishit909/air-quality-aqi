# When does the air turn unhealthy?

Eleven years of daily air quality for every US county with a monitor, 2015 to 2025. Five questions:
- how often is the air unhealthy for sensitive groups or worse (an AQI above 100), and has that changed;
- when do the bad days happen, and which pollutant sets them;
- where: which counties, and how concentrated are the bad days;
- how much does the number of monitors in a county matter;
- which were the worst days.

The questions follow GeeksforGeeks' "Air Quality Data Analysis and Dynamic Visualizations"; the dynamic part is an explorer page (`explorer/index.html`) that draws every day of 24 counties and filters them by pollutant.
The data is real and current, not a course file.

Build log: https://mrrishit909.github.io/projects/air-quality-aqi/ &middot; Explorer: https://mrrishit909.github.io/projects/air-quality-aqi/explorer/

## Data

US Environmental Protection Agency, AirData pre-generated "Daily AQI by County" files for 2015 to 2025 (files as of 2026-06-25); US government data, free to use. One row per county per day on which a monitor reported: the day's AQI (the highest of its
monitors and pollutants), its category, the pollutant that set it (ozone, PM2.5, PM10, NO2 or CO) and the number of sites reporting. 3,577,372 county-days. EPA states that every AirData AQI summary uses the current AQI breakpoints, revised for PM2.5 in
May 2024, whatever the year, so values are comparable across years. The zips are about 1.6 MB each, so they are not committed; `download.py` fetches them.

```
./venv/bin/pip install pandas numpy scipy matplotlib certifi      # in a venv
./venv/bin/python download.py        # data/*.zip
./venv/bin/python analyze.py         # results/*
./venv/bin/python check.py
./venv/bin/python build_explorer.py  # explorer/data.json
./venv/bin/python charts.py
```

## Steps

1. **Download** the eleven yearly files.
2. **Audit:** duplicate county-days, whether each row's category agrees with its AQI, stray spaces in names (23,770 county-days, trimmed), values beyond the 500 the scale ends at, and a fixed panel: the 609 counties with at least 300 daily values in every year (67.7% of all county-days, all 50 states
   and DC), so that monitors starting or stopping do not make a trend.
3. **How bad, when:** the share of panel county-days in each category, bad days (AQI above 100) by year and by month and by the pollutant that set them, and a Spearman correlation of year against the share of bad days.
4. **Where, and the worst days:** counties ranked by bad days, how concentrated they are, bad days against the number of sites reporting, and the ten days with the most counties above 150, with their states and pollutant.
5. **Check.** `check.py` recomputes 109,194 numbers in plain Python straight from the zips, with the csv module and counters and no pandas: the audit, the panel, every table, all 4,018 days, and, for the explorer, every day of its 24 counties.
6. **The explorer:** 24 counties from the panel, every day of 2015 to 2025 as a year-by-day grid, a county menu and a pollutant filter. `build_explorer.py` writes its data (about 290 KB). I checked the page's summary boxes for all 24
   counties against a recount from the raw files, with a headless browser: no mismatches (that test is not in the repo).
7. **Charts.**

## Results

- **Rare.** In the panel 68.3% of county-days are good, 30.1% moderate, 1.23% unhealthy for sensitive groups, 0.29% unhealthy, 0.05% very unhealthy and 0.02% hazardous. 38,652 of the 2,423,326 county-days (1.6%) are above 100.
- **Two causes.** Ozone sets 58.8% of the bad days, PM2.5 (smoke, dust, soot) 35.6% and the rest 5.7%; of the 8,856 county-days above 150 PM2.5 sets 57.2% and ozone 34.0%.
- **No steady trend.** The share of bad days ranges from 0.85% in 2019 to 2.16% in 2023, with no direction over the eleven years (Spearman correlation -0.09, p = 0.79). The PM2.5 share of the bad days ranges from 19.6% in 2016 to 51.0% in 2020.
- **Summer, and winter smoke.** June to August hold 56.0% of the bad days. Ozone peaks in June and July (5,314 and 5,209 county-days) and PM2.5 in August (3,129). In November, December and January PM2.5 sets 85%, 89% and 86% of the bad days.
- **A few places.** San Bernardino County, California had 1,513 bad days of 4,018 (37.7%, 91% of them ozone), then Riverside (1,457), Kern (1,211), Los Angeles (1,195), Tulare (1,170), Maricopa, Arizona (931) and Fresno (913). The ten counties
  with the most bad days hold 25.8% of all bad county-days, the twenty 34.8%, the fifty 50.7% and the hundred 64.8%; 5 of the 609 counties (0.8%) had none in eleven years. Fairbanks North Star, Alaska had 437, every one set by PM2.5.
- **More monitors, more bad days.** The share of county-days above 100 is 0.66% for counties reporting one site that day, 1.30% for two, 1.95% for three, 2.68% for four or five and 7.26% for six or more.
- **A few days.** The worst day was 29 June 2023: 113 of 605 reporting counties were above 150 (Pennsylvania 22, Ohio 17, Maryland 11), then 28 June 2023 (104; Ohio, Indiana, Illinois), 14 September 2020 (87; California 35, Washington 22, Oregon 15),
  13 and 15 September 2020, 12 and 16 September 2020, 7 June 2023 (73; New York 16, Pennsylvania 15, New Jersey 11), 8 June 2023 and 17 September 2020. PM2.5 sets 93% to 98% of the county-days above 150 on each of these ten days.
  The dates match the June 2023 Canadian wildfire smoke and the September 2020 West Coast fires.

## Not done, and caveats

- A county's AQI is the highest reading among its monitors, so a county with more monitors has more chances to record a bad day: the share of bad days is 11 times higher for counties with six or more sites than for single-site counties. County
  rankings mix air quality with how many monitors a county has; the monitors are also not spread over the population.
- The panel keeps 609 of the 1,107 counties that ever report. The others have short, seasonal or interrupted records; they are left out so that the trend is not made by monitors coming and going.
- The AQI scale ends at 500, but 323 county-days are above it (178 set by PM10 and 145 by PM2.5), up to 8,368 for PM10 in Mono County, California on 12 June 2022. They are kept as published, count as hazardous, and no average AQI is used.
- I rely on EPA's statement that the files use the current breakpoints for every year; I did not recompute AQI from concentrations.
- That smoke sets the worst days comes from the pollutant (PM2.5) and the dates; no fire data was used.
- "Bad" means above 100, EPA's boundary for unhealthy for sensitive groups; other thresholds would change the shares.
- The explorer shows 24 counties, with an AQI above 500 capped at "over 500".
