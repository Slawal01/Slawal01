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
        varchar current_coid
        varchar ccn
        varchar stibo_parent_id
        varchar name1
        varchar name2
        varchar address_type
        varchar address1
        varchar address2
        varchar address3
        varchar city
        varchar state
        varchar postal_code
        varchar country
        varchar phone
        varchar fax
        int top_parent_id FK
        int direct_parent_id FK
        varchar relationship_to_gpo
        varchar relationship_to_direct_parent
        varchar parent_relationship_type
        varchar member_status
        date membership_eligible_date
        date membership_ineligible_date
        date member_date
        varchar org_status
        varchar class_of_trade
        varchar facility_category
        varchar facility_type
        varchar specialty
        varchar investor_org
        varchar company_name
        varchar group_name
        varchar division
        varchar market
        int licensed_beds
        date pharmacy_eligible_date
        date pharmacy_ineligible_date
        date non_pharmacy_eligible_date
        date non_pharmacy_ineligible_date
        boolean hrsa_flag
        varchar hrsa_number
        date hrsa_eligible_date
        date hrsa_ineligible_date
        boolean advantage_trust_flag
        boolean dsh_flag
        varchar provista_member_flag
        boolean medassets_member_flag
        boolean cha_member_flag
        varchar excelerate_member_type
        date excelerate_date
        varchar supply_program
        varchar rx_group
        varchar provista_group
        varchar amc_tier_pricing
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
        timestamp recorded_at
    }

    member_group {
        int id PK
        int member_id FK
        varchar group_name
    }

    gpo_entity ||--o{ member : "has"

    member ||--o{ member : "top_parent_id (self-ref)"
    member ||--o{ member : "direct_parent_id (self-ref)"

    member ||--o{ member_dea : "has DEA numbers"
    member ||--o{ member_contact : "has contacts"
    member ||--o{ member_coid_history : "has COID history"
    member ||--o{ member_group : "belongs to groups"
```

## Hierarchy Rules

| Condition | Member Role |
|---|---|
| `top_parent_id = direct_parent_id = self.id` | **Top Parent** (root node) |
| `top_parent_id = direct_parent_id ≠ self.id` | **Direct child of top** (2-level) |
| `top_parent_id ≠ direct_parent_id ≠ self.id` | **Leaf Member** (3-level) |

## GPO Native Member ID

| GPO | native_member_id source | Unique? |
|---|---|---|
| HealthTrust | GPOID | Yes (after dedup) |
| Premier | Address ID | Yes |
| Vizient | LIC | Yes (business-facing identifier) |

## Child Tables by GPO

| Table | HealthTrust | Premier | Vizient |
|---|---|---|---|
| member_dea | Yes (DEA Number) | — | — |
| member_contact | Director of Pharmacy, Material Manager | — | Account Manager |
| member_coid_history | Yes (Prior COID) | — | — |
| member_group | — | — | Yes (Group 1/2/3) |
