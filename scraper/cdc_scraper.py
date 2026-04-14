import requests
import pandas as pd
import os
import time

def scrape_cdc_places():
    """
    Downloads county-level health data from CDC PLACES 2025 release.
    GIS friendly format — one row per county, all measures as columns.
    Uses dataset ID i46a-9kgh via CDC Socrata API.
    """

    #keep identifiers plus key health outcomes and social determinants already in the dataset
    keep_cols = [
        #Identifiers
        "stateabbr", "statedesc", "countyname", "countyfips",
        "totalpopulation", "totalpop18plus",
        #Chronic disease outcomes (age-adjusted prevalence)
        "diabetes_adjprev", "obesity_adjprev", "bphigh_adjprev",
        "chd_adjprev", "stroke_adjprev", "copd_adjprev",
        "cancer_adjprev", "casthma_adjprev", "arthritis_adjprev",
        #Mental health
        "depression_adjprev", "mhlth_adjprev",
        #Health behaviors
        "csmoking_adjprev", "lpa_adjprev", "sleep_adjprev",
        "binge_adjprev",
        #Preventive care
        "checkup_adjprev", "dental_adjprev", "cholscreen_adjprev",
        #Social determinants
        "foodinsecu_adjprev", "housinsecu_adjprev",
        "lacktrpt_adjprev", "foodstamp_adjprev",
        #Disability
        "disability_adjprev", "cognition_adjprev",
        #Loneliness
        "loneliness_adjprev",
        #General health
        "ghlth_adjprev", "phlth_adjprev"
    ]

    all_records = []
    limit       = 1000
    offset      = 0
    base_url    = "https://data.cdc.gov/resource/i46a-9kgh.json"

    while True:
        url = f"{base_url}?%24limit={limit}&%24offset={offset}"

        response = requests.get(url)

        if response.status_code != 200:
            print(f"  Error: {response.status_code}")
            break

        batch = response.json()

        if not batch:
            break

        all_records.extend(batch)
        print(f"  Fetched {len(all_records)} counties so far...")
        offset += limit

        #Small delay to avoid hitting API rate limits
        time.sleep(0.5)

        #CDC PLACES has ~3200 counties so stop after 4 pages
        if len(all_records) >= 4000:
            break

    df = pd.DataFrame(all_records)
    print(f"\nRaw data: {len(df)} rows, {len(df.columns)} columns")

    #Keep only the columns we need
    available = [c for c in keep_cols if c in df.columns]
    df = df[available].copy()

    #Convert prevalence columns to numeric
    prev_cols = [c for c in df.columns if "prev" in c]
    for col in prev_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    #Convert population to numeric
    df["totalpopulation"] = pd.to_numeric(
        df["totalpopulation"], errors="coerce")
    df["totalpop18plus"]  = pd.to_numeric(
        df["totalpop18plus"], errors="coerce")

    print(f"Kept {len(df.columns)} columns")
    print(f"Missing values per column:")
    print(df.isnull().sum()[df.isnull().sum() > 0])

    return df


if __name__ == "__main__":
    os.makedirs("data/raw", exist_ok=True)

    df = scrape_cdc_places()

    output_path = "data/raw/cdc_places_raw.csv"
    df.to_csv(output_path, index=False)
