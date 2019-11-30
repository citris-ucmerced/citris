CREATE TABLE forms
(
    project_id VARCHAR(200),
    project_title VARCHAR(100),
    deadline DATE,
    pi_name VARCHAR(100),
    pi_email VARCHAR(100),
    sponsor_name VARCHAR(100),
    proposal_url VARCHAR(100),
    preferred_submission VARCHAR(100),
    opportunity_number VARCHAR(100),
    nsf_proposal_number VARCHAR(100),
    nsf_pin_number VARCHAR(100),
    project_start DATE,
    project_end DATE,
    estimated_budget INT,
    budget_items VARCHAR(1000),
    extra_space BIT,
    space_details VARCHAR(1000),
    course_buyout BIT,
    buyout_details VARCHAR(1000),
    applicant_role VARCHAR(100),
    additional_info VARCHAR(1000)
);

