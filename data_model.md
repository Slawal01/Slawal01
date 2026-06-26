# GPO Data Model — Entity Relationship Diagram

```mermaid
erDiagram
    gpo_entity {
        int id PK
        varchar code UK
        varchar name
    }

    member {
        int id PK
        int gpo_entity_id FK
        varchar native_member_id
        varchar gln
        varchar hin
        varchar lic
        varchar premier_gpo_id
        varchar current_coid
        varchar ccn
        varchar name1
        varchar name2
        varchar override_name
        varchar address_type
        varchar address1
        varchar city
        varchar state
        varchar postal_code
        varchar country
        varchar phone
        varchar fax
        int top_parent_id FK
        int direct_parent_id FK
        int corporate_parent_id FK
        int food_service_parent_id FK
        boolean top_parent_flag
        varchar top_parent_gln
        varchar direct_parent_gln
        varchar relationship_to_top_parent
        varchar relationship_to_direct_parent
        varchar parent_relationship_type
        varchar member_status
        date membership_eligible_date
        date membership_ineligible_date
        varchar org_status
        varchar participation_type
        varchar class_of_trade
        varchar facility_type
        varchar facility_category
        varchar service_provider_classification
        varchar food_service_classification
        date food_service_start_date
        date food_service_end_date
        varchar committed_program_eligibility
        int licensed_beds
        date pharmacy_eligible_date
        date pharmacy_ineligible_date
        boolean hrsa_flag
        varchar hrsa_number
        varchar dsh_hrsa_number
        boolean dsh_flag
        text comments
        timestamp created_at
        timestamp updated_at
    }

    member_dea {
        int id PK
        int member_id FK
        varchar dea_number
        varchar dea_registrant_name
    }

    member_contact {
        int id PK
        int member_id FK
        varchar contact_type
        varchar contact_name
        varchar phone
        varchar fax
        varchar email
    }

    member_coid_history {
        int id PK
        int member_id FK
        varchar prior_coid
        varchar current_coid
        date effective_date
    }

    member_program {
        int id PK
        int member_id FK
        varchar program_name
        date start_date
        date end_date
    }

    member_group {
        int id PK
        int member_id FK
        varchar group_name
    }

    member_affiliation {
        int id PK
        int member_id FK
        varchar affiliation
        date start_date
        date end_date
    }

    gpo_entity ||--o{ member : "has"

    member ||--o{ member : "top_parent_id"
    member ||--o{ member : "direct_parent_id"
    member ||--o{ member : "corporate_parent_id"
    member ||--o{ member : "food_service_parent_id"

    member ||--o{ member_dea         : "has DEA numbers"
    member ||--o{ member_contact     : "has contacts"
    member ||--o{ member_coid_history : "COID history"
    member ||--o{ member_program     : "program enrollments"
    member ||--o{ member_group       : "group affiliations"
    member ||--o{ member_affiliation : "aggregation affiliations"
```

---

## Hierarchy Rules

| Condition | Member Role |
|---|---|
| `top_parent_id = direct_parent_id = self.id` | **Top Parent** (root node) |
| `top_parent_id = direct_parent_id != self.id` | **Direct child of top** (2-level) |
| `top_parent_id != direct_parent_id != self.id` | **Leaf Member** (3-level) |

---

## Native Member ID by GPO

| GPO | native_member_id | Unique? |
|---|---|---|
| HealthTrust | GPOID | Yes (after dedup) |
| Premier | Address ID | Yes |
| Vizient | LIC | Yes |

---

## Column Source by GPO

### member table
| Column | HealthTrust | Premier | Vizient |
|---|---|---|---|
| native_member_id | GPOID | Address ID | LIC |
| premier_gpo_id | — | GPO ID | — |
| gln | GLN | — | GLN |
| hin | HIN | HIN | HIN |
| current_coid | COID | — | — |
| ccn | CCN | — | — |
| name1 | Name1 | Name 1 | Member Name |
| name2 | Name2 | Name 2 | — |
| override_name | — | Override Name | — |
| address_type | Address Type | Address Type | — |
| city/state/postal | yes | yes | yes |
| country | Country | Country | — |
| phone | Phone | Phone | Member Phone |
| fax | Fax | Fax | — |
| top_parent_id | Top Parent GPOID | Top Parent GPO ID | System ID |
| direct_parent_id | Direct Parent GPOID | Direct Parent GPO ID | Parent ID |
| top_parent_flag | — | Top Parent Flag | — |
| top_parent_gln | — | Top Parent GLN | — |
| direct_parent_gln | — | Direct Parent GLN | — |
| corporate_parent_id | — | Corporate Parent GPO ID | — |
| food_service_parent_id | — | Food Service Parent GPO ID | — |
| food_service_classification | — | Food Service Classification | — |
| food_service_start_date | — | Food Service Start Date | — |
| food_service_end_date | — | Food Service End Date | — |
| relationship_to_gpo | Relationship to GPO | — | — |
| relationship_to_top_parent | — | Relationship to Top Parent | — |
| relationship_to_direct_parent | Relationship to Direct Parent | Relationship to Direct Parent | — |
| member_status | Member Status | Member Status | — |
| membership_eligible_date | Membership Eligible Date | Membership Start Date | Member Date |
| membership_ineligible_date | Membership Ineligible Date | Membership Termination Date | — |
| org_status | Organizational Status | Organizational Status | — |
| participation_type | — | Participation Type | — |
| committed_program_eligibility | — | Committed Program Eligibility | — |
| class_of_trade | Class of Trade | Class of Trade | — |
| facility_type | Facility Type | — | Facility Type |
| facility_category | — | — | Facility Category |
| service_provider_classification | — | Service Provider Classification | — |
| type | — | Type | — |
| group_name | Group | Group | — |
| licensed_beds | Licensed Beds | — | — |
| pharmacy_eligible_date | Pharmacy Eligible Date | Pharmacy Start Date | — |
| pharmacy_ineligible_date | Pharmacy InEligible Date | Pharmacy End Date | — |
| hrsa_flag | HRSA | — | — |
| hrsa_number | HRSA Number | — | — |
| hrsa_eligible_date | HRSA Eligible Date | — | — |
| hrsa_ineligible_date | HRSA InEligible Date | — | — |
| dsh_flag | DSH Flag | — | — |
| dsh_hrsa_number | — | DSH and/or HRSA Number | — |
| advantage_trust_flag | AdvantageTrust | — | — |
| provista_member_flag | — | — | Provista Member |
| excelerate_member_type | — | — | Excelerate Member |
| supply_program | — | — | Supply Program |
| rx_group | — | — | Rx Group |
| amc_tier_pricing | — | — | AMC Tier Pricing |
| comments | Comments | — | — |

---

## Child Tables by GPO

| Table | HealthTrust | Premier | Vizient |
|---|---|---|---|
| member_dea | DEA Number | DEA # | — |
| member_contact | Dir. of Pharmacy, Material Mgr | — | Account Manager |
| member_coid_history | Prior COID → COID | — | — |
| member_program | — | AscenDrive, KIINDO, SURPASS | Excelerate |
| member_group | — | — | Vizient Group 1/2/3 |
| member_affiliation | — | Aggregation Affiliation 1/2/3 | — |

---

## Load Order (all GPOs)

1. **Pass 1** — Top Parents (`top_parent_id = direct_parent_id = self`)
2. **Pass 2** — Direct Parents (`direct_parent_id = top_parent_id != self`)
3. **Pass 3** — Leaf Members (`direct_parent_id != top_parent_id`)
4. **Pass 4** — Child table records (DEA, contacts, COID history, programs, groups, affiliations)
