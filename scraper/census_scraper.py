import requests
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("Census_API_KEY")

def scrape_census_data():
    """
    Download county-level social determinants from Census American Community Survey (ACS)
    5-year estimates. Pulls poverty rate, median income, 
    uninsured rate, educational attainment, and unemployment by county.
    """

    if not API_KEY:
        print("Error: Census API key not found. Please set CENSUS_API_KEY in .env file.")
        return None
    
    variables = ",".join([
        "NAME",
        "B17001_002E", "B17001_001E",
        "B19013_001E",
        "B27001_005E", "B27001_001E",
        "B15003_022E", "B15003_001E",
        "B23025_005E", "B23025_001E",
        "B01003_001E"
    ])

    url = (
        f"https://api.census.gov/data/2022/acs/acs5"
        f"?get={variables}"
        f"&for=county:*"
        f"&key={API_KEY}"
    )

    response = requests.get(url)

    if response.status_code != 200:
        print(f"  Error: {response.status_code}")
        print(f"  Message: {response.text[:200]}")
        return None
    
    data = response.json()
    headers = data[0]
    rows = data[1:]

    df = pd.DataFrame(rows, columns=headers)
    print(f"  Got {len(df)} counties")

    #Create FIPS code by combining state and county codes
    df["countyfips"] = df["state"] + df["county"]

    #rename columns to readable names
    df = df.rename(columns={
        "NAME":          "county_name",
        "B17001_002E":   "pop_below_poverty",
        "B17001_001E":   "pop_poverty_denom",
        "B19013_001E":   "median_household_income",
        "B27001_005E":   "pop_uninsured",
        "B27001_001E":   "pop_insurance_denom",
        "B15003_022E":   "pop_bachelors_plus",
        "B15003_001E":   "pop_education_denom",
        "B23025_005E":   "pop_unemployed",
        "B23025_001E":   "pop_labor_force",
        "B01003_001E":   "total_population"
    })

    #Convert to numeric
    numeric_cols = [
        "pop_below_poverty", "pop_poverty_denom",
        "median_household_income",
        "pop_uninsured", "pop_insurance_denom",
        "pop_bachelors_plus", "pop_education_denom",
        "pop_unemployed", "pop_labor_force",
        "total_population"
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    #Calculate rates from raw counts
    df["poverty_rate"] = (
        df["pop_below_poverty"] / df["pop_poverty_denom"] * 100
    )
    df["uninsured_rate"] = (
        df["pop_uninsured"] / df["pop_insurance_denom"] * 100
    )
    df["bachelors_rate"] = (
        df["pop_bachelors_plus"] / df["pop_education_denom"] * 100
    )
    df["unemployment_rate"] = (
        df["pop_unemployed"] / df["pop_labor_force"] * 100
    )

    #Replace Census missing value codes with NaN
    df["median_household_income"] = df["median_household_income"].where(
        df["median_household_income"] > 0, other=pd.NA
    )

    #replace any other extreme negative values
    for col in ["poverty_rate", "uninsured_rate", 
                "bachelors_rate", "unemployment_rate"]:
        df[col] = df[col].where(df[col] >= 0, other=pd.NA)

    #Keep only the calculated rates and identifiers
    final_cols = [
        "countyfips", "county_name", "state", "county",
        "total_population",
        "poverty_rate", "median_household_income",
        "uninsured_rate", "bachelors_rate", "unemployment_rate"
    ]
    df = df[final_cols]

    print(f"\nFinal dataset: {len(df)} counties, {len(df.columns)} columns")
    print(f"\nSummary statistics:")
    print(df[["poverty_rate", "median_household_income",
              "uninsured_rate", "bachelors_rate",
              "unemployment_rate"]].describe().round(2))

    return df

if __name__ == "__main__":
    os.makedirs("data/raw", exist_ok=True)

    df = scrape_census_data()

    if df is not None:
        output_path = "data/raw/census_acs_raw.csv"
        df.to_csv(output_path, index=False)
        print(f"\nDone! Saved {len(df)} rows to {output_path}")
        print("\nFirst 3 rows:")
        print(df.head(3))