import pandas as pd
import os

def scrape_usda_food_atlas():
    """
    Read USDA Food Environment Atlas Excel file and extract food access, store availability,
    assistance program participation, and food insecurity measures by county.
    """

    filepath = "data/raw/2025-food-environment-atlas-data.xlsx"

    if not os.path.exists(filepath):
        print(f"    ERROR: File not found at {filepath}")
        return None
    
    #Read each relevant sheet with header on Row 2
    access_df = pd.read_excel(filepath, sheet_name="ACCESS", header=1)[["FIPS", "PCT_LACCESS_POP19"]].copy()

    stores_df = pd.read_excel(filepath, sheet_name="STORES", header=1)[["FIPS", "GROCPTH20", "CONVSPTH20"]].copy()

    assist_df = pd.read_excel(filepath, sheet_name="ASSISTANCE", header=1)[["FIPS", "PCT_SNAP22", "PCT_FREE_LUNCH15"]].copy()

    insec_df = pd.read_excel(filepath, sheet_name="INSECURITY", header=1)[["FIPS", "FOODINSEC_21_23", "VLFOODSEC_21_23"]].copy()

    #Merging all sheets on FIPS code
    df = access_df.merge(stores_df, on="FIPS", how="outer")
    df = df.merge(assist_df, on="FIPS", how="outer")
    df = df.merge(insec_df, on="FIPS", how="outer")

    #Rename columns
    df = df.rename(columns={
        "FIPS":              "countyfips",
        "PCT_LACCESS_POP19": "pct_low_food_access",
        "GROCPTH20":         "grocery_stores_per_1000",
        "CONVSPTH20":        "convenience_stores_per_1000",
        "PCT_SNAP22":        "snap_participation_rate",
        "PCT_FREE_LUNCH15":  "pct_free_lunch",
        "FOODINSEC_21_23":   "food_insecurity_rate",
        "VLFOODSEC_21_23":   "very_low_food_security_rate"
    })

    #Convert FIPS to string with leading zeros to match CDC format
    df["countyfips"] = df["countyfips"].astype(str).str.zfill(5)

    #Convert all measures to numeric
    measure_cols = [
            "pct_low_food_access", "grocery_stores_per_1000",
            "convenience_stores_per_1000", "snap_participation_rate",
            "pct_free_lunch", "food_insecurity_rate",
            "very_low_food_security_rate"
        ]
    for col in measure_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    #Replace USDA missing value codes with NaN
    for col in measure_cols:
        df[col] = df[col].where(df[col] >= 0, other=pd.NA)

    print(f"\nFinal dataset: {len(df)} counties, {len(df.columns)} columns")
    print(f"\nMissing values per column:")
    print(df.isnull().sum())
    print(f"\nSummary statistics:")
    print(df[measure_cols].describe().round(2))

    return df
if __name__ == "__main__":
    os.makedirs("data/raw", exist_ok=True)

    df = scrape_usda_food_atlas()

    if df is not None:
        output_path = "data/raw/usda_food_atlas_raw.csv"
        df.to_csv(output_path, index=False)
        print(f"\nDone! Saved {len(df)} rows to {output_path}")
        print("\nFirst 3 rows:")
        print(df.head(3))