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
-- HealthTrust  native_member_id = GPOID
-- Premier      native_member_id = GPO ID
-- Vizient      native_member_id = LIC (business-facing identifier)
-- ============================================================
CREATE TABLE member (
    id                              SERIAL PRIMARY KEY,
    gpo_entity_id                   INT          NOT NULL REFERENCES gpo_entity(id),

    -- Natural / cross-GPO keys
    native_member_id                VARCHAR(50)  NOT NULL,  -- GPOID (HT) / Address ID (Premier) / LIC (Vizient)
    current_coid                    VARCHAR(20),             -- Current COID (HealthTrust only)
    ccn                             VARCHAR(20),             -- CMS Certification Number (HealthTrust)
    premier_gpo_id                  VARCHAR(50),             -- Premier GPO ID (account-level, alongside Address ID)
    vizient_member_id               VARCHAR(50),             -- Vizient numeric Member ID (secondary to LIC)

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
    -- 2-level:   top_parent_id = direct_parent_id != self.id
    -- 3-level:   top_parent_id != direct_parent_id != self.id
    top_parent_id                   INT          REFERENCES member(id),
    direct_parent_id                INT          REFERENCES member(id),
    relationship_to_gpo             VARCHAR(100),            -- HealthTrust
    relationship_to_top_parent      VARCHAR(100),            -- Premier
    relationship_to_direct_parent   VARCHAR(100),            -- Premier & HealthTrust
    parent_relationship_type        VARCHAR(100),            -- Owned / Joint Venture / Managed / etc.

    -- Membership status
    member_status                   VARCHAR(50),
    membership_eligible_date        DATE,                    -- HT: Membership Eligible Date / Premier: Membership Start Date / Vizient: Member Date
    membership_ineligible_date      DATE,                    -- HT: Membership Ineligible Date
    org_status                      VARCHAR(50),
    committed_program_eligibility   VARCHAR(200),            -- Premier

    -- Class of trade & classification
    class_of_trade                  VARCHAR(100),            -- HealthTrust
    facility_type                   VARCHAR(100),            -- HealthTrust
    specialty                       VARCHAR(100),            -- HealthTrust
    investor_org                    VARCHAR(100),            -- HealthTrust
    company_name                    VARCHAR(200),            -- HealthTrust
    group_name                      VARCHAR(200),            -- HealthTrust
    division                        VARCHAR(200),            -- HealthTrust
    market                          VARCHAR(100),            -- HealthTrust
    licensed_beds                   INT,                     -- HealthTrust

    -- Pharmacy (HealthTrust only)
    pharmacy_eligible_date          DATE,
    pharmacy_ineligible_date        DATE,
    non_pharmacy_eligible_date      DATE,
    non_pharmacy_ineligible_date    DATE,

    -- HRSA / DSH (340B) (HealthTrust only)
    hrsa_flag                       BOOLEAN,
    hrsa_number                     VARCHAR(50),
    hrsa_eligible_date              DATE,
    hrsa_ineligible_date            DATE,
    dsh_flag                        BOOLEAN,
    advantage_trust_flag            BOOLEAN,

    -- Vizient-specific
    supply_program                  VARCHAR(100),            -- Vizient: Supply Program
    amc_tier_pricing                VARCHAR(100),            -- Vizient: AMC Tier Pricing

    comments                        TEXT,                    -- HealthTrust

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
-- MEMBER PROGRAM
-- Named programs with start/end dates
-- Premier: AscenDrive, KIINDO, SURPASS
-- ============================================================
CREATE TABLE member_program (
    id              SERIAL PRIMARY KEY,
    member_id       INT          NOT NULL REFERENCES member(id) ON DELETE CASCADE,
    program_name    VARCHAR(100) NOT NULL,  -- 'AscenDrive', 'KIINDO', 'SURPASS'
    start_date      DATE,
    end_date        DATE,

    CONSTRAINT uq_member_program UNIQUE (member_id, program_name)
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
CREATE INDEX idx_member_gpo             ON member (gpo_entity_id);
CREATE INDEX idx_member_gln             ON member (gln);
CREATE INDEX idx_member_hin             ON member (hin);
CREATE INDEX idx_member_coid            ON member (current_coid);
CREATE INDEX idx_member_top_parent      ON member (top_parent_id);
CREATE INDEX idx_member_direct_parent   ON member (direct_parent_id);
CREATE INDEX idx_member_dea_number      ON member_dea (dea_number);
CREATE INDEX idx_member_coid_hist       ON member_coid_history (member_id);
CREATE INDEX idx_member_group           ON member_group (member_id);
CREATE INDEX idx_member_program         ON member_program (member_id);
CREATE INDEX idx_member_affiliation     ON member_affiliation (member_id);

-- ============================================================
-- HIERARCHY LEVEL VIEW
-- Derives the role of each member row based on ID comparisons:
--
--   Top Parent    : top_parent_id = direct_parent_id = self.id
--   Direct Parent : top_parent_id = direct_parent_id != self.id
--   Member        : top_parent_id != direct_parent_id
--
-- Load order must follow this hierarchy:
--   Pass 1 → Top Parents  (no parent reference needed)
--   Pass 2 → Direct Parents (top parent already loaded)
--   Pass 3 → Leaf Members   (both parents already loaded)
-- ============================================================
CREATE VIEW v_member_hierarchy AS
SELECT
    m.id,
    m.gpo_entity_id,
    g.code                          AS gpo_code,
    m.native_member_id,
    m.name1,
    m.top_parent_id,
    m.direct_parent_id,
    CASE
        WHEN m.top_parent_id = m.id
         AND m.direct_parent_id = m.id
        THEN 'Top Parent'

        WHEN m.top_parent_id = m.direct_parent_id
         AND m.top_parent_id != m.id
        THEN 'Direct Parent'

        ELSE 'Member'
    END                             AS hierarchy_level
FROM member m
JOIN gpo_entity g ON g.id = m.gpo_entity_id;


-- ============================================================
-- HIERARCHY LOAD QUERIES
-- Use these to extract rows in correct load order per GPO
-- Replace :gpo_code with 'HEALTHTRUST', 'PREMIER', or 'VIZIENT'
-- ============================================================

-- Pass 1: Top Parents
-- (top_parent native_member_id = direct_parent native_member_id = own native_member_id)
-- SELECT * FROM v_member_hierarchy WHERE hierarchy_level = 'Top Parent' AND gpo_code = :gpo_code;

-- Pass 2: Direct Parents
-- SELECT * FROM v_member_hierarchy WHERE hierarchy_level = 'Direct Parent' AND gpo_code = :gpo_code;

-- Pass 3: Leaf Members
-- SELECT * FROM v_member_hierarchy WHERE hierarchy_level = 'Member' AND gpo_code = :gpo_code;
