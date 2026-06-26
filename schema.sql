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
    id                          SERIAL PRIMARY KEY,
    gpo_entity_id               INT          NOT NULL REFERENCES gpo_entity(id),

    -- Natural / cross-GPO keys
    native_member_id            VARCHAR(50)  NOT NULL,  -- GPOID (HT) / Address ID (Premier) / LIC (Vizient)
    gln                         VARCHAR(20),             -- Global Location Number
    hin                         VARCHAR(20),             -- Health Industry Number
    current_coid                VARCHAR(20),             -- Current COID (HealthTrust only)
    ccn                         VARCHAR(20),             -- CMS Certification Number

    -- Name & address
    name1                       VARCHAR(200) NOT NULL,
    name2                       VARCHAR(200),
    address_type                VARCHAR(50),
    address1                    VARCHAR(200),
    address2                    VARCHAR(200),
    address3                    VARCHAR(200),
    city                        VARCHAR(100),
    state                       VARCHAR(10),
    postal_code                 VARCHAR(20),
    country                     VARCHAR(50),
    phone                       VARCHAR(30),
    fax                         VARCHAR(30),

    -- Hierarchy
    -- If direct_parent_id = top_parent_id → 2-level; otherwise → 3-level
    top_parent_id               INT          REFERENCES member(id),
    direct_parent_id            INT          REFERENCES member(id),
    relationship_to_gpo         VARCHAR(100),
    relationship_to_direct_parent VARCHAR(100),
    parent_relationship_type    VARCHAR(100), -- Owned / Joint Venture / Managed / etc.

    -- Membership status
    member_status               VARCHAR(50),
    membership_eligible_date    DATE,
    membership_ineligible_date  DATE,
    org_status                  VARCHAR(50),

    -- Class of trade & classification
    class_of_trade              VARCHAR(100),
    facility_type               VARCHAR(100),
    specialty                   VARCHAR(100),
    investor_org                VARCHAR(100),
    company_name                VARCHAR(200),
    group_name                  VARCHAR(200),
    division                    VARCHAR(200),
    market                      VARCHAR(100),
    licensed_beds               INT,

    -- Pharmacy
    pharmacy_eligible_date      DATE,
    pharmacy_ineligible_date    DATE,
    non_pharmacy_eligible_date  DATE,
    non_pharmacy_ineligible_date DATE,

    -- HRSA (340B)
    hrsa_flag                   BOOLEAN,
    hrsa_number                 VARCHAR(50),
    hrsa_eligible_date          DATE,
    hrsa_ineligible_date        DATE,

    -- Flags
    advantage_trust_flag        BOOLEAN,
    dsh_flag                    BOOLEAN,

    comments                    TEXT,

    created_at                  TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMP    NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_member_gpo_native UNIQUE (gpo_entity_id, native_member_id)
);

-- ============================================================
-- MEMBER DEA
-- One row per DEA number per member
-- Root cause of duplicate rows in HealthTrust source data
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
-- contact_type: 'Material Manager', 'Director of Pharmacy'
-- ============================================================
CREATE TABLE member_contact (
    id              SERIAL PRIMARY KEY,
    member_id       INT          NOT NULL REFERENCES member(id) ON DELETE CASCADE,
    contact_type    VARCHAR(100) NOT NULL,  -- e.g. 'Director of Pharmacy', 'Material Manager'
    contact_name    VARCHAR(200),
    phone           VARCHAR(30),
    fax             VARCHAR(30),

    CONSTRAINT uq_member_contact UNIQUE (member_id, contact_type)
);

-- ============================================================
-- MEMBER COID HISTORY  (HealthTrust only)
-- Tracks Prior COID → COID transitions to preserve audit trail
-- COID is NOT unique; GPOID is the stable key
-- ============================================================
CREATE TABLE member_coid_history (
    id              SERIAL PRIMARY KEY,
    member_id       INT          NOT NULL REFERENCES member(id) ON DELETE CASCADE,
    prior_coid      VARCHAR(20),
    current_coid    VARCHAR(20)  NOT NULL,
    effective_date  DATE,                   -- populated when known from source
    recorded_at     TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- ============================================================
-- INDEXES
-- ============================================================
CREATE INDEX idx_member_gpo          ON member (gpo_entity_id);
CREATE INDEX idx_member_gln          ON member (gln);
CREATE INDEX idx_member_hin          ON member (hin);
CREATE INDEX idx_member_coid         ON member (current_coid);
CREATE INDEX idx_member_top_parent   ON member (top_parent_id);
CREATE INDEX idx_member_direct_parent ON member (direct_parent_id);
CREATE INDEX idx_member_dea_number   ON member_dea (dea_number);
CREATE INDEX idx_member_coid_hist    ON member_coid_history (member_id);
