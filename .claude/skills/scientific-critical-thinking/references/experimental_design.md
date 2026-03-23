# Experimental Design: Comprehensive Checklist

## Overview

This reference provides a comprehensive checklist for designing rigorous experiments, covering every stage from research question formulation to reporting. Use it when planning new studies, reviewing research proposals, or evaluating the design quality of published research.

---

## 1. Research Question

### Clarity and Specificity
- [ ] Is the question clearly stated and specific?
- [ ] Is it answerable with available methods and resources?
- [ ] Does it address a meaningful gap in knowledge?
- [ ] Is it framed in testable terms?

### PICO(T) Format (for intervention studies)
- **P**opulation: Who is being studied?
- **I**ntervention: What is being tested?
- **C**omparison: What is the control or alternative?
- **O**utcome: What is being measured?
- **T**ime: Over what time period?

### FINER Criteria
- **F**easible: Can it be done with available resources?
- **I**nteresting: Does the scientific community care?
- **N**ovel: Does it add new knowledge?
- **E**thical: Can it be conducted ethically?
- **R**elevant: Does it matter for practice, policy, or theory?

---

## 2. Hypotheses

### Formulation
- [ ] Null hypothesis (H₀) clearly stated
- [ ] Alternative hypothesis (H₁) clearly stated
- [ ] Hypotheses are falsifiable and specific
- [ ] Direction of effect specified (one-tailed vs. two-tailed justified)
- [ ] Primary hypothesis distinguished from secondary/exploratory

### Preregistration
- [ ] Hypotheses documented before data collection
- [ ] Analysis plan specified before data collection
- [ ] Registered on a public platform (OSF, AsPredicted, ClinicalTrials.gov)
- [ ] Deviations from preregistration will be documented and justified

---

## 3. Study Design Selection

### Design Types and When to Use Them

| Design | Use When | Strengths | Limitations |
|---|---|---|---|
| **Between-subjects RCT** | Testing intervention effects; participants can only receive one condition | Strongest causal inference; controls for confounders | Requires more participants; individual differences add noise |
| **Within-subjects (crossover)** | Each participant can experience all conditions | More power with fewer participants; controls individual differences | Carryover effects; order effects; not always feasible |
| **Factorial** | Testing multiple factors and their interactions | Efficient; tests interactions; tests multiple hypotheses | Complexity increases with factors; requires larger samples |
| **Quasi-experimental** | Randomization impossible or unethical | Feasible when RCT isn't; pragmatic | Weaker causal inference; confounding harder to control |
| **Cohort (prospective)** | Studying exposures and long-term outcomes | Establishes temporality; multiple outcomes; incidence rates | Expensive; time-consuming; attrition |
| **Case-control** | Rare outcomes; efficient for exploratory etiology | Efficient; good for rare diseases | Recall bias; selection bias; can't calculate incidence |
| **Cross-sectional** | Prevalence; associations at one time point | Quick; inexpensive; good for prevalence | Can't establish causation or temporality |
| **N-of-1 trial** | Individual treatment decisions; rare conditions | Direct relevance to individual; controls for individual variation | Limited generalizability; carryover effects |

### Design Decisions
- [ ] Design matched to research question type
- [ ] Between-subjects vs. within-subjects justified
- [ ] Number of factors and levels determined
- [ ] Temporal structure planned (cross-sectional, longitudinal, time-series)
- [ ] Comparison groups defined and justified

---

## 4. Variables

### Independent Variables (IV)
- [ ] Clearly defined and operationalized
- [ ] Levels/conditions specified
- [ ] Manipulation is meaningful and realistic
- [ ] Manipulation check planned (if applicable)

### Dependent Variables (DV)
- [ ] Primary outcome clearly designated
- [ ] Secondary outcomes listed
- [ ] Measurement method specified for each
- [ ] Timing of measurement determined
- [ ] Clinical/practical significance threshold defined

### Control Variables
- [ ] Known confounders identified (use literature review and causal diagrams)
- [ ] Method of control specified for each (randomization, matching, stratification, statistical adjustment)
- [ ] Potential unmeasured confounders acknowledged

### Moderating and Mediating Variables
- [ ] Potential moderators identified (who/when does the effect vary?)
- [ ] Potential mediators identified (how/why does the effect occur?)
- [ ] Analysis plan for moderation/mediation specified

---

## 5. Sampling

### Sample Size Determination
- [ ] A priori power analysis conducted
  - Effect size: Based on prior research, pilot data, or minimum meaningful effect
  - Alpha level: Typically 0.05 (justify if different)
  - Power: Minimum 0.80, ideally 0.90+
  - Statistical test: Matched to planned analysis
- [ ] Sample size accounts for expected attrition (inflate by expected dropout rate)
- [ ] Rationale for effect size estimate documented

### Sampling Strategy
- [ ] Target population defined
- [ ] Sampling frame identified
- [ ] Sampling method specified:
  - Simple random sampling
  - Stratified random sampling
  - Cluster sampling
  - Convenience sampling (acknowledge limitations)
  - Purposive sampling (qualitative research)
- [ ] Inclusion criteria clearly defined
- [ ] Exclusion criteria clearly defined and justified
- [ ] Recruitment strategy planned

### Sample Characteristics
- [ ] Key demographic variables will be collected
- [ ] Sample representativeness will be assessed
- [ ] Baseline characteristics will be compared across groups

---

## 6. Randomization

### Method
- [ ] Randomization method specified:
  - Simple randomization (coin flip / random number generator)
  - Block randomization (ensures balanced groups)
  - Stratified randomization (balances key prognostic factors)
  - Adaptive randomization (adjusts based on enrollment)
  - Cluster randomization (randomizes groups, not individuals)
- [ ] Computer-generated sequence (not manual)
- [ ] Seed documented for reproducibility

### Allocation Concealment
- [ ] Allocation sequence concealed from those enrolling participants
- [ ] Method of concealment specified (sealed envelopes, central phone system, web-based system)
- [ ] Cannot be predicted or tampered with

### Verification
- [ ] Baseline balance will be checked after randomization
- [ ] Deviations from randomized allocation will be documented
- [ ] Intent-to-treat analysis planned (analyzing as randomized, not as treated)

---

## 7. Blinding

### Levels of Blinding
| Level | Who Is Blinded | Why It Matters |
|---|---|---|
| **Single-blind** | Participants | Reduces placebo effects, demand characteristics |
| **Double-blind** | Participants + providers | Also reduces performance bias |
| **Triple-blind** | Participants + providers + outcome assessors | Also reduces detection bias |
| **Quadruple-blind** | + data analysts | Also reduces analysis bias |

### Implementation
- [ ] Feasibility of blinding assessed for each level
- [ ] Blinding method described (identical placebos, matching interventions, coded conditions)
- [ ] Blinding success will be verified (ask participants/assessors to guess condition)
- [ ] Procedures if blinding is broken (emergency unblinding protocol)

### When Blinding Is Impossible
- [ ] Acknowledged explicitly
- [ ] Objective outcomes used when possible
- [ ] Outcome assessors blinded even if participants can't be
- [ ] Potential impact on results discussed

---

## 8. Control Groups

### Types of Controls
| Type | Description | When to Use |
|---|---|---|
| **Placebo** | Inert treatment matching appearance | When testing specific treatment effects beyond expectations |
| **Active control** | Existing standard treatment | When withholding treatment is unethical; for comparative effectiveness |
| **No treatment** | Nothing additional provided | When measuring natural course; when placebo isn't feasible |
| **Waitlist** | Delayed treatment for control group | When no treatment seems unethical; provides eventual access |
| **Attention control** | Matched for time/attention without active ingredient | When isolating the specific active component |
| **Sham procedure** | Mimics procedure without active component | Surgical or device trials |

### Control Group Checklist
- [ ] Type of control justified for the research question
- [ ] Control condition is credible to participants (if blinded)
- [ ] Contact time/attention is matched (if relevant)
- [ ] Ethical considerations addressed (especially for no-treatment/placebo)
- [ ] Standard of care maintained for all groups

---

## 9. Procedures

### Standardization
- [ ] Detailed protocol document created
- [ ] Step-by-step procedures for each session/visit
- [ ] Scripts for participant interactions (if applicable)
- [ ] Training plan for research staff
- [ ] Fidelity/adherence monitoring planned
- [ ] Protocol deviations will be documented

### Data Collection
- [ ] Data collection points defined (timeline)
- [ ] Data collection methods standardized
- [ ] Procedures for ensuring data quality (double entry, range checks)
- [ ] Backup procedures for equipment failure or missing data
- [ ] Data security and storage plan

---

## 10. Measurement

### Instrument Selection
- [ ] Instruments are validated for the study population
- [ ] Reliability established (internal consistency, test-retest, inter-rater)
- [ ] Sensitivity to change demonstrated (if measuring change over time)
- [ ] Cultural/linguistic appropriateness verified
- [ ] Psychometric properties documented

### Measurement Types
- [ ] **Objective measures** used when possible (physiological, behavioral, performance-based)
- [ ] **Subjective measures** supplemented with objective ones when feasible
- [ ] **Multiple measures** of key constructs (triangulation)
- [ ] **Validated scales** preferred over ad hoc measures

### Measurement Quality Checklist
- [ ] Measurement protocol standardized
- [ ] Assessors trained and calibrated
- [ ] Inter-rater reliability will be assessed and reported
- [ ] Equipment calibrated and maintained
- [ ] Blinding of assessors implemented (if possible)

---

## 11. Bias Minimization

### Design-Level Protections
- [ ] Randomization (eliminates selection bias)
- [ ] Blinding (reduces performance and detection bias)
- [ ] Allocation concealment (prevents selection after randomization)
- [ ] Standardized protocols (reduces measurement variability)

### Analysis-Level Protections
- [ ] Intent-to-treat analysis planned (preserves randomization)
- [ ] Multiple comparison correction specified
- [ ] Sensitivity analyses planned
- [ ] Subgroup analyses prespecified and limited
- [ ] Missing data strategy defined

### Reporting-Level Protections
- [ ] Study preregistered
- [ ] Reporting guideline selected (CONSORT, STROBE, PRISMA, etc.)
- [ ] All outcomes will be reported (not just significant ones)
- [ ] Exploratory analyses will be labeled as such
- [ ] Conflicts of interest will be disclosed

---

## 12. Data Management

### Data Collection and Storage
- [ ] Data management plan documented
- [ ] Database structure designed before collection begins
- [ ] Data dictionary created (variable names, definitions, coding)
- [ ] Data entry procedures specified
- [ ] Quality checks planned (range checks, logic checks, double entry)

### Data Security
- [ ] Data stored securely (encrypted, access-controlled)
- [ ] Identifiable data separated from research data
- [ ] Backup procedures in place
- [ ] Data retention policy defined
- [ ] Compliance with institutional and legal requirements (IRB, GDPR, HIPAA)

### Data Sharing
- [ ] Plan for data sharing specified
- [ ] De-identification procedures planned
- [ ] Repository identified (if sharing publicly)
- [ ] Data documentation sufficient for reuse

---

## 13. Statistical Analysis Plan

### Pre-Specified Analyses
- [ ] Primary analysis specified (test, assumptions, model)
- [ ] Secondary analyses listed
- [ ] Exploratory analyses labeled as exploratory
- [ ] Decision rules defined (e.g., what p-value threshold for conclusions)

### Statistical Methods
- [ ] Tests appropriate for data type (continuous, categorical, ordinal, count)
- [ ] Tests appropriate for design (paired, independent, repeated measures)
- [ ] Assumptions listed with planned checks
  - Normality (Shapiro-Wilk, Q-Q plots)
  - Homogeneity of variance (Levene's test)
  - Independence of observations
  - Linearity (for regression)
- [ ] Alternative tests if assumptions are violated

### Reporting Plan
- [ ] Effect sizes will be reported (with type specified)
- [ ] Confidence intervals will be reported
- [ ] Exact p-values will be reported
- [ ] Descriptive statistics specified (means, SDs, medians, IQRs)
- [ ] Missing data: amount, mechanism assessment, handling method

### Sensitivity Analyses
- [ ] Per-protocol analysis (in addition to intent-to-treat)
- [ ] Analysis with different missing data assumptions
- [ ] Analysis with and without outliers (if applicable)
- [ ] Robustness to analytic choices

---

## 14. Ethical Considerations

### Approval and Oversight
- [ ] Ethics committee / IRB approval obtained
- [ ] Study registered in public registry (if applicable)
- [ ] Data safety monitoring board established (if needed)
- [ ] Stopping rules defined (for interim analyses)

### Participant Protection
- [ ] Informed consent process designed
- [ ] Risks clearly communicated to participants
- [ ] Benefits accurately described (not overstated)
- [ ] Voluntary participation ensured
- [ ] Right to withdraw without penalty
- [ ] Privacy and confidentiality protections

### Special Considerations
- [ ] Vulnerable populations: Additional protections in place
- [ ] Deception: Justified and debriefing planned
- [ ] Risk-benefit ratio: Favorable
- [ ] Equipoise: Genuine uncertainty about which treatment is better
- [ ] Post-trial access: Plan for providing effective treatment to all participants

---

## 15. Validity Threats Checklist

### Internal Validity Threats
| Threat | Description | Mitigation |
|---|---|---|
| History | External events affect outcome | Control group; short duration |
| Maturation | Natural change over time | Control group; within-subjects |
| Testing | Prior testing affects later scores | Control group; alternate forms |
| Instrumentation | Measurement changes over time | Calibration; standardization |
| Regression to mean | Extreme scores move toward average | Random selection; control group |
| Selection | Groups differ at baseline | Randomization; matching |
| Attrition | Differential dropout | ITT analysis; minimize dropout |
| Diffusion | Control learns treatment | Separate settings; blinding |

### External Validity Threats
| Threat | Description | Mitigation |
|---|---|---|
| Sample | Non-representative participants | Random sampling; diverse recruitment |
| Setting | Lab ≠ real world | Field studies; ecological validity |
| Time | Results specific to era | Replication over time |
| Reactivity | Awareness changes behavior | Unobtrusive measures; deception |
| Treatment variation | Standardized ≠ real implementation | Pragmatic trials |

---

## 16. Reporting Standards

### CONSORT (Randomized Controlled Trials)
Key items:
- Participant flow diagram
- Enrollment, allocation, follow-up, analysis numbers
- Baseline characteristics by group
- Primary and secondary outcomes with effect sizes and CIs
- Harms and adverse events
- Trial registration number
- Protocol availability

### STROBE (Observational Studies)
Key items:
- Study design identified in title/abstract
- Setting, locations, dates, periods of recruitment/follow-up
- Eligibility criteria and sources of participants
- Variables: outcomes, exposures, confounders
- Data sources and measurement
- Bias: efforts to address potential sources
- Statistical methods including confounding control

### PRISMA (Systematic Reviews)
Key items:
- Search strategy reproducible
- Inclusion/exclusion criteria
- Risk of bias assessment
- Synthesis methods
- Forest plots
- Heterogeneity assessment
- Publication bias assessment

### General Reporting Principles
- [ ] Report all planned outcomes (not just significant ones)
- [ ] Distinguish confirmatory from exploratory analyses
- [ ] Provide complete statistical results (test statistic, df, p-value, effect size, CI)
- [ ] Discuss limitations honestly
- [ ] Make data and code available when possible
- [ ] Disclose conflicts of interest
- [ ] Provide protocol or preregistration reference

---

## Quick Reference: Design Quality Checklist

### Essential (Must Have)
- [ ] Clear, answerable research question
- [ ] Appropriate design for the question
- [ ] Adequate sample size (power analysis)
- [ ] Valid and reliable measures
- [ ] Appropriate statistical analysis
- [ ] Ethical approval

### Important (Should Have)
- [ ] Preregistration
- [ ] Randomization (for intervention studies)
- [ ] Blinding (where feasible)
- [ ] Control group (appropriate type)
- [ ] Pre-specified primary outcome
- [ ] Intent-to-treat analysis plan

### Best Practice (Ideal)
- [ ] Multiple measures of key constructs
- [ ] Sensitivity analyses
- [ ] Open data and code
- [ ] Following reporting guidelines
- [ ] Replication plan
- [ ] Data safety monitoring (for clinical trials)
