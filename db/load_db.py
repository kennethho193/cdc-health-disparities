import sqlite3
import pandas as pd
import os

def create_database(db_path, schema_path):
    """
    Creates SQLite database from schema file.
    Drops existing database first to ensure clean load.
    """
    if os.path.exists(db_path):
        os.remove(db_path)
        print("  Removed existing database")

    with open(schema_path, "r") as f:
        schema = f.read()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executescript(schema)
    conn.commit()
    conn.close()

def load_counties(conn, cdc_df):
    """
    Loads unique county identifiers from CDC PLACES data.
    """

    counties_df = cdc_df[[
        "countyfips", "stateabbr", "statedesc",
        "countyname", "totalpopulation", "totalpop18plus"
    ]].drop_duplicates(subset=["countyfips"]).copy()

    counties_df.to_sql(
        "counties", conn,
        if_exists="append",
        index=False
    )

    print(f"  Loaded {len(counties_df)} counties")

def load_health_outcomes(conn, cdc_df):
    """
    Loads CDC PLACES health outcome measures.
    """

    cols = [
        "countyfips",
        "diabetes_adjprev", "obesity_adjprev", "bphigh_adjprev",
        "chd_adjprev", "stroke_adjprev", "copd_adjprev",
        "cancer_adjprev", "casthma_adjprev", "arthritis_adjprev",
        "depression_adjprev", "mhlth_adjprev",
        "csmoking_adjprev", "lpa_adjprev", "sleep_adjprev",
        "binge_adjprev", "checkup_adjprev", "dental_adjprev",
        "cholscreen_adjprev", "ghlth_adjprev", "phlth_adjprev",
        "disability_adjprev", "cognition_adjprev"
    ]

    available = [c for c in cols if c in cdc_df.columns]
    health_df = cdc_df[available].copy()

    health_df.to_sql(
        "health_outcomes", conn,
        if_exists="append",
        index=False
    )

    print(f"  Loaded {len(health_df)} records")

def load_social_determinants(conn, census_df, usda_df):
    """
    Merges Census ACS and USDA Food Atlas data then loads
    into social_determinants table.
    """
    # Merge Census and USDA on FIPS code
    merged_df = census_df.merge(
        usda_df,
        on="countyfips",
        how="outer"
    )

    cols = [
        "countyfips",
        "poverty_rate", "median_household_income",
        "uninsured_rate", "bachelors_rate", "unemployment_rate",
        "pct_low_food_access", "grocery_stores_per_1000",
        "convenience_stores_per_1000", "snap_participation_rate",
        "pct_free_lunch", "food_insecurity_rate",
        "very_low_food_security_rate"
    ]

    available = [c for c in cols if c in merged_df.columns]
    soc_df    = merged_df[available].copy()

    # Only keep counties that exist in our counties table
    cdc_fips  = pd.read_sql("SELECT countyfips FROM counties", conn)
    soc_df    = soc_df[soc_df["countyfips"].isin(cdc_fips["countyfips"])]

    soc_df.to_sql(
        "social_determinants", conn,
        if_exists="append",
        index=False
    )

    print(f"  Loaded {len(soc_df)} records")

def verify_load(conn):
    """
    Runs checks on loaded data with a full three-table join.
    """
    cursor = conn.cursor()

    for table in ["counties", "health_outcomes", "social_determinants"]:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        print(f"  {table}: {cursor.fetchone()[0]} records")

    print(f"\n  Top 5 counties by diabetes prevalence:")
    cursor.execute("""
        SELECT c.countyname, c.stateabbr,
               h.diabetes_adjprev, s.poverty_rate
        FROM health_outcomes h
        JOIN counties c ON h.countyfips = c.countyfips
        JOIN social_determinants s ON h.countyfips = s.countyfips
        WHERE h.diabetes_adjprev IS NOT NULL
        AND s.poverty_rate IS NOT NULL
        ORDER BY h.diabetes_adjprev DESC
        LIMIT 5
    """)
    for row in cursor.fetchall():
        print(f"    {row[0]}, {row[1]} — "
              f"diabetes: {row[2]:.1f}%, poverty: {row[3]:.1f}%")


if __name__ == "__main__":
    db_path     = "db/cdc_health.db"
    schema_path = "db/schema.sql"

    # Step 1: Create database
    create_database(db_path, schema_path)

    # Step 2: Load raw CSVs
    cdc_df    = pd.read_csv("data/raw/cdc_places_raw.csv",
                            dtype={"countyfips": str})
    census_df = pd.read_csv("data/raw/census_acs_raw.csv",
                            dtype={"countyfips": str})
    usda_df   = pd.read_csv("data/raw/usda_food_atlas_raw.csv",
                            dtype={"countyfips": str})

    print(f"  CDC PLACES: {len(cdc_df)} rows")
    print(f"  Census ACS: {len(census_df)} rows")
    print(f"  USDA Atlas: {len(usda_df)} rows")

    # Step 3: Connect and load
    conn = sqlite3.connect(db_path)

    load_counties(conn, cdc_df)
    load_health_outcomes(conn, cdc_df)
    load_social_determinants(conn, census_df, usda_df)

    conn.commit()

    # Step 4: Verify
    verify_load(conn)
    conn.close()
