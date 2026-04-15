-- CDC Health Disparities Database Schema
-- Three source datasets joined on FIPS county code

-- Counties table: identifiers and population
-- One row per US county
CREATE TABLE IF NOT EXISTS counties (
    countyfips      TEXT PRIMARY KEY,
    stateabbr       TEXT NOT NULL,
    statedesc       TEXT NOT NULL,
    countyname      TEXT NOT NULL,
    totalpopulation REAL,
    totalpop18plus  REAL
);

-- Health outcomes table: CDC PLACES measures
-- Age-adjusted prevalence rates per county
CREATE TABLE IF NOT EXISTS health_outcomes (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    countyfips          TEXT NOT NULL,
    -- Chronic disease
    diabetes_adjprev    REAL,
    obesity_adjprev     REAL,
    bphigh_adjprev      REAL,
    chd_adjprev         REAL,
    stroke_adjprev      REAL,
    copd_adjprev        REAL,
    cancer_adjprev      REAL,
    casthma_adjprev     REAL,
    arthritis_adjprev   REAL,
    -- Mental health
    depression_adjprev  REAL,
    mhlth_adjprev       REAL,
    -- Health behaviors
    csmoking_adjprev    REAL,
    lpa_adjprev         REAL,
    sleep_adjprev       REAL,
    binge_adjprev       REAL,
    -- Preventive care
    checkup_adjprev     REAL,
    dental_adjprev      REAL,
    cholscreen_adjprev  REAL,
    -- General health
    ghlth_adjprev       REAL,
    phlth_adjprev       REAL,
    -- Disability
    disability_adjprev  REAL,
    cognition_adjprev   REAL,
    FOREIGN KEY (countyfips) REFERENCES counties (countyfips)
);

-- Social determinants table: Census ACS + USDA Food Atlas
-- Socioeconomic and food environment measures per county
CREATE TABLE IF NOT EXISTS social_determinants (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    countyfips                  TEXT NOT NULL,
    -- Census ACS measures
    poverty_rate                REAL,
    median_household_income     REAL,
    uninsured_rate              REAL,
    bachelors_rate              REAL,
    unemployment_rate           REAL,
    -- USDA Food Atlas measures
    pct_low_food_access         REAL,
    grocery_stores_per_1000     REAL,
    convenience_stores_per_1000 REAL,
    snap_participation_rate     REAL,
    pct_free_lunch              REAL,
    food_insecurity_rate        REAL,
    very_low_food_security_rate REAL,
    FOREIGN KEY (countyfips) REFERENCES counties (countyfips)
);