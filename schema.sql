-- GPO Normalized Data Model
-- Covers: Premier, HealthTrust, Vizient
-- ============================================================

-- GPO entity registry
CREATE TABLE gpo_entity (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(20)  NOT NULL UNIQUE,  -- 'PREMIER', 'HEALTHTRUST', 'VIZIENT'
    name        VARCHAR(100) NOT NULL
);

INSERT INTO gpo_entity (code, name) VALUES
    ('PREMIER',     'Premier GPO'),
    ('HEALTHTRUST', 'HealthTrust'),
    ('VIZIENT',     'Vizient');

-- ============================================================
-- MEMBER
-- One row per unique member per GPO (keyed by native_member_id)
-- HealthTrust native_member_id = GPOID
-- Premier      native_member_id = Address ID
-- Vizient      native_member_id = LIC (business-facing identifier)
-- ============================================================
CREATE TABLE member (
    id                              SERIAL PRIMARY KEY,
    gpo_entity_id                   INT          NOT NULL REFERENCES gpo_entity(id),

    -- Natural / cross-GPO keys
    native_member_id                VARCHAR(50)  NOT NULL,  -- GPOID (HT) / Address ID (Premier) / LIC (Vizient)
    gln                             VARCHAR(20),             -- Global Location Number
    hin                             VARCHAR(20),             -- Health Industry Number
    current_coid                    VARCHAR(20),             -- Current COID (HealthTrust only)
    ccn                             VARCHAR(20),             -- CMS Certification Number
    premier_gpo_id                  VARCHAR(50),             -- Premier GPO ID (alternate ID alongside Address ID)
    lic                             VARCHAR(20),             -- Vizient LIC code

    -- Name & address
    name1                           VARCHAR(200) NOT NULL,
    name2                           VARCHAR(200),
    override_name                   VARCHAR(200),            -- Premier Override Name
    address_type                    VARCHAR(50),
    address1                        VARCHAR(200),
    address2                        VARCHAR(200),
    address3                        VARCHAR(200),
    city                            VARCHAR(100),
    state                           VARCHAR(10),
    postal_code                     VARCHAR(20),
    country                         VARCHAR(50),
    phone                           VARCHAR(30),
    fax                             VARCHAR(30),

    -- Hierarchy (3-level max across all GPOs)
    -- Root node: top_parent_id = direct_parent_id = self.id
    -- 2-level:   top_parent_id = direct_parent_id != self.id  (Premier 2-level cases)
    -- 3-level:   top_parent_id != direct_parent_id != self.id
    top_parent_id                   INT          REFERENCES member(id),
    direct_parent_id                INT          REFERENCES member(id),
    top_parent_flag                 BOOLEAN,                 -- Premier: explicit top parent marker
    top_parent_gln                  VARCHAR(20),             -- Premier: GLN of top parent
    direct_parent_gln               VARCHAR(20),             -- Premier: GLN of direct parent
    relationship_to_gpo             VARCHAR(100),            -- HealthTrust
    relationship_to_direct_parent   VARCHAR(100),            -- HealthTrust
    relationship_to_top_parent      VARCHAR(100),            -- Premier: Relationship to Top Parent
    parent_relationship_type        VARCHAR(100),            -- Owned / Joint Venture / Managed / etc.

    -- Corporate parent (Premier — separate from main hierarchy)
    corporate_parent_id             INT          REFERENCES member(id),

    -- Food service parent (Premier — separate branch)
    food_service_parent_id          INT          REFERENCES member(id),
    food_service_classification     VARCHAR(100),
    food_service_start_date         DATE,
    food_service_end_date           DATE,

    -- Membership status
    member_status                   VARCHAR(50),
    membership_eligible_date        DATE,                    -- HT: Membership Eligible Date / Premier: Membership Start Date
    membership_ineligible_date      DATE,                    -- HT: Membership Ineligible Date / Premier: Membership Termination Date
    org_status                      VARCHAR(50),
    participation_type              VARCHAR(100),            -- Premier
    committed_program_eligibility   VARCHAR(200),            -- Premier

    -- Class of trade & classification
    class_of_trade                  VARCHAR(100),
    facility_type                   VARCHAR(100),
    service_provider_classification VARCHAR(100),            -- Premier
    specialty                       VARCHAR(100),
    type                            VARCHAR(100),            -- Premier: Type field
    investor_org                    VARCHAR(100),
    company_name                    VARCHAR(200),
    group_name                      VARCHAR(200),
    division                        VARCHAR(200),
    market                          VARCHAR(100),
    licensed_beds                   INT,

    -- Pharmacy
    pharmacy_eligible_date          DATE,                    -- HT: Pharmacy Eligible Date / Premier: Pharmacy Start Date
    pharmacy_ineligible_date        DATE,                    -- HT: Pharmacy InEligible Date / Premier: Pharmacy End Date
    non_pharmacy_eligible_date      DATE,
    non_pharmacy_ineligible_date    DATE,

    -- HRSA / DSH (340B)
    hrsa_flag                       BOOLEAN,                 -- HealthTrust
    hrsa_number                     VARCHAR(50),             -- HealthTrust: HRSA Number
    hrsa_eligible_date              DATE,
    hrsa_ineligible_date            DATE,
    dsh_hrsa_number                 VARCHAR(50),             -- Premier: combined DSH and/or HRSA Number
    dsh_flag                        BOOLEAN,                 -- HealthTrust

    -- Vizient-specific flags & programs
    advantage_trust_flag            BOOLEAN,
    provista_member_flag            VARCHAR(20),
    medassets_member_flag           BOOLEAN,
    cha_member_flag                 BOOLEAN,
    excelerate_member_type          VARCHAR(100),
    excelerate_date                 DATE,
    supply_program                  VARCHAR(100),
    rx_group                        VARCHAR(100),
    provista_group                  VARCHAR(100),
    amc_tier_pricing                VARCHAR(100),
    stibo_parent_id                 VARCHAR(50),
    facility_category               VARCHAR(100),
    member_date                     DATE,

    comments                        TEXT,

    created_at                      TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at                      TIMESTAMP    NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_member_gpo_native UNIQUE (gpo_entity_id, native_member_id)
);

-- ============================================================
-- MEMBER DEA
-- One row per DEA number per member
-- Used by: HealthTrust (root cause of duplicate rows), Premier
-- ============================================================
CREATE TABLE member_dea (
    id                      SERIAL PRIMARY KEY,
    member_id               INT          NOT NULL REFERENCES member(id) ON DELETE CASCADE,
    dea_number              VARCHAR(20)  NOT NULL,
    dea_registrant_name     VARCHAR(200),

    CONSTRAINT uq_member_dea UNIQUE (member_id, dea_number)
);

-- ============================================================
-- MEMBER CONTACT
-- One row per contact type per member
-- HealthTrust: 'Director of Pharmacy', 'Material Manager'
-- Vizient:     'Account Manager'
-- ============================================================
CREATE TABLE member_contact (
    id              SERIAL PRIMARY KEY,
    member_id       INT          NOT NULL REFERENCES member(id) ON DELETE CASCADE,
    contact_type    VARCHAR(100) NOT NULL,
    contact_name    VARCHAR(200),
    phone           VARCHAR(30),
    fax             VARCHAR(30),
    email           VARCHAR(200),

    CONSTRAINT uq_member_contact UNIQUE (member_id, contact_type)
);

-- ============================================================
-- MEMBER COID HISTORY  (HealthTrust only)
-- Tracks Prior COID -> COID transitions
-- COID is NOT unique; GPOID is the stable key
-- ============================================================
CREATE TABLE member_coid_history (
    id              SERIAL PRIMARY KEY,
    member_id       INT          NOT NULL REFERENCES member(id) ON DELETE CASCADE,
    prior_coid      VARCHAR(20),
    current_coid    VARCHAR(20)  NOT NULL,
    effective_date  DATE,
    recorded_at     TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- ============================================================
-- MEMBER PROGRAM
-- Named programs with start/end dates
-- Premier:  AscenDrive, KIINDO, SURPASS
-- Vizient:  Excelerate (with date)
-- ============================================================
CREATE TABLE member_program (
    id              SERIAL PRIMARY KEY,
    member_id       INT          NOT NULL REFERENCES member(id) ON DELETE CASCADE,
    program_name    VARCHAR(100) NOT NULL,
    start_date      DATE,
    end_date        DATE,

    CONSTRAINT uq_member_program UNIQUE (member_id, program_name)
);

-- ============================================================
-- MEMBER GROUP
-- Multi-value group affiliations
-- Vizient: Vizient Group 1, Group 2, Group 3
-- ============================================================
CREATE TABLE member_group (
    id              SERIAL PRIMARY KEY,
    member_id       INT          NOT NULL REFERENCES member(id) ON DELETE CASCADE,
    group_name      VARCHAR(200) NOT NULL,

    CONSTRAINT uq_member_group UNIQUE (member_id, group_name)
);

-- ============================================================
-- MEMBER AFFILIATION
-- Multi-value aggregation affiliations with date ranges
-- Premier: Aggregation Affiliation 1/2/3 with Start/End Dates
-- ============================================================
CREATE TABLE member_affiliation (
    id              SERIAL PRIMARY KEY,
    member_id       INT          NOT NULL REFERENCES member(id) ON DELETE CASCADE,
    affiliation     VARCHAR(200) NOT NULL,
    start_date      DATE,
    end_date        DATE,

    CONSTRAINT uq_member_affiliation UNIQUE (member_id, affiliation)
);

-- ============================================================
-- INDEXES
-- ============================================================
CREATE INDEX idx_member_gpo                ON member (gpo_entity_id);
CREATE INDEX idx_member_gln                ON member (gln);
CREATE INDEX idx_member_hin                ON member (hin);
CREATE INDEX idx_member_coid               ON member (current_coid);
CREATE INDEX idx_member_top_parent         ON member (top_parent_id);
CREATE INDEX idx_member_direct_parent      ON member (direct_parent_id);
CREATE INDEX idx_member_corporate_parent   ON member (corporate_parent_id);
CREATE INDEX idx_member_food_svc_parent    ON member (food_service_parent_id);
CREATE INDEX idx_member_dea_number         ON member_dea (dea_number);
CREATE INDEX idx_member_coid_hist          ON member_coid_history (member_id);
CREATE INDEX idx_member_program            ON member_program (member_id);
CREATE INDEX idx_member_group              ON member_group (member_id);
CREATE INDEX idx_member_affiliation        ON member_affiliation (member_id);
