-- GPO Hierarchy Load Queries
-- Determines member level from RAW SOURCE DATA before loading into member table
-- ============================================================
--
-- RULE:
--   If Top Parent ID = Direct Parent ID = Member's own ID  → TOP PARENT
--   If Top Parent ID = Direct Parent ID ≠ Member's own ID → DIRECT PARENT
--   If Top Parent ID ≠ Direct Parent ID                   → LEAF MEMBER
--
-- Load order: Top Parents first, then Direct Parents, then Leaf Members
-- ============================================================


-- ============================================================
-- HEALTHTRUST
-- ============================================================

-- Pass 1: Top Parents
SELECT DISTINCT
    "Top Parent GPOID"          AS native_member_id,
    "Top Parent Name 1"         AS name1,
    NULL                        AS top_parent_id,
    NULL                        AS direct_parent_id,
    'Top Parent'                AS hierarchy_level
FROM healthtrust_source
WHERE "GPOID" = "Direct Parent GPOID"
  AND "GPOID" = "Top Parent GPOID";

-- Pass 2: Direct Parents
SELECT DISTINCT
    "Direct Parent GPOID"       AS native_member_id,
    "Direct Parent Name1"       AS name1,
    "Top Parent GPOID"          AS top_parent_id,
    "Direct Parent GPOID"       AS direct_parent_id,
    'Direct Parent'             AS hierarchy_level
FROM healthtrust_source
WHERE "Direct Parent GPOID" = "Top Parent GPOID"
  AND "GPOID" != "Top Parent GPOID";

-- Pass 3: Leaf Members
SELECT
    "GPOID"                         AS native_member_id,
    "Name1"                         AS name1,
    "Name2"                         AS name2,
    "Address1"                      AS address1,
    "Address2"                      AS address2,
    "Address3"                      AS address3,
    "City"                          AS city,
    "State/Province"                AS state,
    "Postal Code"                   AS postal_code,
    "Direct Parent GPOID"           AS direct_parent_id,
    "Top Parent GPOID"              AS top_parent_id,
    "Membership Eligible Date"      AS membership_eligible_date,
    "Member Status"                 AS member_status,
    "Comments"                      AS comments,
    'Member'                        AS hierarchy_level
FROM healthtrust_source
WHERE "GPOID" != "Direct Parent GPOID";


-- ============================================================
-- PREMIER
-- ============================================================

-- Pass 1: Top Parents
SELECT DISTINCT
    "Top Parent GPO ID"         AS native_member_id,
    "Top Parent Name 1"         AS name1,
    NULL                        AS top_parent_id,
    NULL                        AS direct_parent_id,
    'Top Parent'                AS hierarchy_level
FROM premier_source
WHERE "GPO ID" = "Direct Parent GPO ID"
  AND "GPO ID" = "Top Parent GPO ID";

-- Pass 2: Direct Parents
SELECT DISTINCT
    "Direct Parent GPO ID"      AS native_member_id,
    "Direct Parent Name 1"      AS name1,
    "Top Parent GPO ID"         AS top_parent_id,
    "Direct Parent GPO ID"      AS direct_parent_id,
    'Direct Parent'             AS hierarchy_level
FROM premier_source
WHERE "Direct Parent GPO ID" = "Top Parent GPO ID"
  AND "GPO ID" != "Top Parent GPO ID";

-- Pass 3: Leaf Members
SELECT
    "Address ID"                    AS native_member_id,
    "GPO ID"                        AS premier_gpo_id,
    "Name 1"                        AS name1,
    "Name 2"                        AS name2,
    "Override Name"                 AS override_name,
    "Address Type"                  AS address_type,
    "Address 1"                     AS address1,
    "Address 2"                     AS address2,
    "Address 3"                     AS address3,
    "City"                          AS city,
    "State/Province"                AS state,
    "Postal Code"                   AS postal_code,
    "Top Parent GPO ID"             AS top_parent_id,
    "Direct Parent GPO ID"          AS direct_parent_id,
    "Relationship to Top Parent"    AS relationship_to_top_parent,
    "Relationship to Direct Parent" AS relationship_to_direct_parent,
    "Member Status"                 AS member_status,
    "Membership Start Date"         AS membership_eligible_date,
    "Committed Program Eligibility" AS committed_program_eligibility,
    'Member'                        AS hierarchy_level
FROM premier_source
WHERE "GPO ID" != "Direct Parent GPO ID";


-- Pass 4: Premier Programs (AscenDrive, KIINDO, SURPASS)
-- Run after Pass 3 so member rows exist
SELECT "Address ID" AS native_member_id, 'AscenDrive' AS program_name, "AscenDrive Start Date" AS start_date, "AscenDrive End Date" AS end_date FROM premier_source WHERE "AscenDrive Start Date" IS NOT NULL
UNION ALL
SELECT "Address ID", 'KIINDO', "KIINDO Start Date", "KIINDO End Date" FROM premier_source WHERE "KIINDO Start Date" IS NOT NULL
UNION ALL
SELECT "Address ID", 'SURPASS', "SURPASS Start Date", "SURPASS End Date" FROM premier_source WHERE "SURPASS Start Date" IS NOT NULL;


-- ============================================================
-- VIZIENT
-- ============================================================

-- Pass 1: Top Parents  (System ID = Parent ID = Member ID)
SELECT DISTINCT
    "System ID"                 AS native_member_id,   -- use LIC equivalent for system
    "System Name"               AS name1,
    NULL                        AS top_parent_id,
    NULL                        AS direct_parent_id,
    'Top Parent'                AS hierarchy_level
FROM vizient_source
WHERE "Member ID" = "System ID"
  AND "Member ID" = "Parent ID";

-- Pass 2: Direct Parents  (System ID = Parent ID, Member ID != System ID)
SELECT DISTINCT
    "Parent ID"                 AS native_member_id,
    "Parent Name"               AS name1,
    "System ID"                 AS top_parent_id,
    "Parent ID"                 AS direct_parent_id,
    'Direct Parent'             AS hierarchy_level
FROM vizient_source
WHERE "Parent ID" = "System ID"
  AND "Member ID" != "System ID";

-- Pass 3: Leaf Members
SELECT
    "LIC"                           AS native_member_id,
    "Member ID"                     AS vizient_member_id,
    "Member Name"                   AS name1,
    "Address1"                      AS address1,
    "Address2"                      AS address2,
    "City"                          AS city,
    "State"                         AS state,
    "Zip Code"                      AS postal_code,
    "System ID"                     AS top_parent_id,
    "Parent ID"                     AS direct_parent_id,
    "Member Date"                   AS membership_eligible_date,
    "Supply Program"                AS supply_program,
    "AMC Tier Pricing"              AS amc_tier_pricing,
    'Member'                        AS hierarchy_level
FROM vizient_source
WHERE "Member ID" != "Parent ID";
