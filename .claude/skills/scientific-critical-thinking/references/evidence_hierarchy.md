# Evidence Hierarchy and Quality Assessment

## Overview

Not all evidence is created equal. This reference provides frameworks for evaluating evidence strength, including the traditional evidence hierarchy, the GRADE system, study quality assessment tools, and practical decision frameworks.

---

## 1. Traditional Evidence Hierarchy

### Levels of Evidence (for Intervention/Treatment Questions)

| Level | Study Design | Strength |
|---|---|---|
| **I** | Systematic reviews and meta-analyses of RCTs | Highest |
| **II** | Well-designed randomized controlled trials (RCTs) | High |
| **III** | Controlled trials without randomization (quasi-experimental) | Moderate-High |
| **IV** | Cohort studies and case-control studies | Moderate |
| **V** | Cross-sectional studies, ecological studies | Low-Moderate |
| **VI** | Case series and case reports | Low |
| **VII** | Expert opinion, physiological reasoning, bench research | Lowest |

### Important Caveats
- **The hierarchy is a starting point, not a final judgment.** A well-conducted observational study can be more informative than a poorly conducted RCT.
- **Different questions require different designs:**
  - Intervention effectiveness → RCT preferred
  - Prognosis → Cohort studies
  - Diagnosis → Cross-sectional with gold standard comparison
  - Etiology/harm → Cohort or case-control (RCTs often unethical)
  - Prevalence → Cross-sectional surveys
- **Quality within a level matters more than the level itself.** A high-quality cohort study outranks a biased, underpowered RCT.

---

## 2. The GRADE System

### Overview
GRADE (Grading of Recommendations, Assessment, Development and Evaluation) is the most widely adopted framework for rating certainty of evidence and strength of recommendations.

### Starting Ratings
| Study Design | Starting Certainty |
|---|---|
| Randomized trials | **High** (⊕⊕⊕⊕) |
| Observational studies | **Low** (⊕⊕○○) |

### Factors That Lower Certainty (Downgrade)

#### 1. Risk of Bias
- Inadequate randomization or allocation concealment
- Lack of blinding when outcomes are subjective
- Incomplete outcome data (high attrition)
- Selective outcome reporting
- Other biases (funding, conflicts of interest)
- **Downgrade**: One level for serious risk, two for very serious

#### 2. Inconsistency
- Results vary substantially across studies
- Point estimates differ in direction or magnitude
- Confidence intervals show limited overlap
- Heterogeneity is unexplained (I² > 50%)
- **Downgrade**: One level for serious inconsistency

#### 3. Indirectness
- **Population**: Study population differs from target population
- **Intervention**: Studied intervention differs from intervention of interest
- **Comparator**: Comparison group doesn't match the clinical question
- **Outcome**: Surrogate outcomes used instead of patient-important outcomes
- **Downgrade**: One level for each serious indirectness issue

#### 4. Imprecision
- Wide confidence intervals
- Small number of events
- Small total sample size
- Confidence interval crosses clinically important thresholds
- **Downgrade**: One level for serious imprecision
- **Rule of thumb**: Consider downgrading if total events < 300 or CI spans both clinically meaningful benefit and harm

#### 5. Publication Bias
- Funnel plot asymmetry
- Small studies show larger effects
- Industry-funded studies show systematically different results
- Known unpublished trials exist
- **Downgrade**: One level for strongly suspected publication bias

### Factors That Raise Certainty (Upgrade — Observational Studies Only)

#### 1. Large Effect
- **Large** (RR > 2 or < 0.5): Upgrade one level
- **Very large** (RR > 5 or < 0.2): Upgrade two levels
- Only when no plausible confounders could explain the effect

#### 2. Dose-Response Gradient
- Clear relationship between dose/exposure level and outcome magnitude
- Upgrade one level when a dose-response pattern is evident

#### 3. Plausible Confounding Would Reduce Effect
- All plausible confounders would bias results toward null
- Yet an association is still observed
- Upgrade one level

### GRADE Certainty Levels

| Rating | Symbol | Meaning |
|---|---|---|
| **High** | ⊕⊕⊕⊕ | Very confident the true effect is close to the estimate |
| **Moderate** | ⊕⊕⊕○ | Moderately confident; true effect likely close but may differ |
| **Low** | ⊕⊕○○ | Limited confidence; true effect may be substantially different |
| **Very Low** | ⊕○○○ | Very little confidence; true effect likely substantially different |

---

## 3. Study Quality Assessment Tools

### For Randomized Controlled Trials

#### Cochrane Risk of Bias Tool (ROB 2)
Assesses five domains:
1. **Randomization process**: Was allocation sequence random? Was it concealed?
2. **Deviations from intended interventions**: Were participants/providers blinded? Were there protocol deviations?
3. **Missing outcome data**: Was data complete? Could missingness depend on the outcome?
4. **Measurement of the outcome**: Were assessors blinded? Could measurement be influenced?
5. **Selection of reported result**: Were multiple outcomes/analyses possible? Were results selected based on findings?

**Judgments per domain**: Low risk / Some concerns / High risk

#### Jadad Scale (Simpler Alternative)
Scores 0-5 based on:
- Was the study randomized? (+1) Appropriately? (+1 or -1)
- Was it double-blind? (+1) Appropriately? (+1 or -1)
- Were withdrawals described? (+1)

### For Observational Studies

#### Newcastle-Ottawa Scale (NOS)
Assesses three domains (max 9 stars):

**Selection (max 4 stars):**
- Representativeness of exposed cohort
- Selection of non-exposed cohort
- Ascertainment of exposure
- Outcome not present at start

**Comparability (max 2 stars):**
- Controls for most important factor
- Controls for additional factors

**Outcome (max 3 stars):**
- Assessment of outcome
- Adequate follow-up length
- Adequacy of follow-up completeness

#### ROBINS-I (for Non-Randomized Studies of Interventions)
Seven domains:
1. Confounding
2. Selection of participants
3. Classification of interventions
4. Deviations from intended interventions
5. Missing data
6. Measurement of outcomes
7. Selection of reported results

### For Diagnostic Studies

#### QUADAS-2
Four domains:
1. **Patient selection**: Consecutive/random enrollment? Appropriate exclusions?
2. **Index test**: Interpreted without knowledge of reference standard? Pre-specified threshold?
3. **Reference standard**: Correctly classifies condition? Interpreted without knowledge of index test?
4. **Flow and timing**: Appropriate interval? All patients receive both tests? All included in analysis?

### For Systematic Reviews

#### AMSTAR 2
16-item tool assessing:
- Registered protocol
- Comprehensive literature search
- Duplicate study selection and extraction
- Adequate description of included studies
- Risk of bias assessment
- Appropriate statistical methods
- Assessment of publication bias
- Conflict of interest reported

---

## 4. Domain-Specific Considerations

### Clinical/Medical Research
- Prioritize patient-important outcomes over surrogates
- Consider number needed to treat (NNT) and number needed to harm (NNH)
- Assess whether comparison group received standard of care
- Check for industry funding bias
- Evaluate applicability to the specific patient population

### Social/Behavioral Sciences
- Consider replication status (has the finding been independently replicated?)
- Evaluate measurement validity carefully (constructs are often abstract)
- Assess cultural generalizability
- Consider demand characteristics and experimenter effects
- Check for preregistration (especially important given replication crisis)

### Environmental/Ecological Sciences
- Long-term studies weighted more heavily
- Multiple independent data sources strengthen conclusions
- Consider spatial and temporal scale
- Evaluate model assumptions and sensitivity analyses
- Recognize that RCTs are often impossible — strong observational evidence may be the best available

### Technology/Computer Science
- Benchmarks: Are they standardized? Are baselines fair?
- Ablation studies: Is the contribution of each component verified?
- Dataset bias: Does training data represent the target domain?
- Reproducibility: Are code and data available? Has anyone replicated?
- Statistical testing: Are results tested for significance, or just reported as point estimates?

---

## 5. Evidence Synthesis Principles

### Strengthening Evidence Through Convergence
Evidence is strongest when:
- **Multiple independent studies** reach the same conclusion
- **Different methodologies** produce consistent results (methodological triangulation)
- **Different research groups** find similar effects (reduces group-specific bias)
- **Different populations** show the effect (generalizability)
- **Mechanistic and empirical evidence** align (biological plausibility + observed effect)

### Weakening Factors
- Single study or single research group only
- Contradictory findings in the literature
- Evidence of publication bias
- No attempted replication
- Conflicts of interest across the evidence base
- All studies share the same methodological limitation

### Hierarchy of Evidence Synthesis
1. **Systematic review with meta-analysis** — quantitative synthesis
2. **Systematic review without meta-analysis** — qualitative synthesis
3. **Scoping review** — maps the evidence landscape
4. **Narrative review** — expert summary (prone to bias)
5. **Single study** — needs context of broader literature

---

## 6. Practical Decision Framework

### For Evaluating a Single Study
1. **Identify the question type** (therapy, diagnosis, prognosis, harm, etc.)
2. **Assess study design appropriateness** for the question
3. **Evaluate internal validity** using appropriate quality tool
4. **Assess external validity** (generalizability to your context)
5. **Examine results** (effect size, precision, significance)
6. **Consider the broader evidence** (is this consistent with other studies?)
7. **Rate overall confidence** in the finding

### For Comparing Conflicting Studies
1. **Compare study quality** — higher quality evidence gets more weight
2. **Look for methodological differences** that explain discrepancies
3. **Consider sample differences** — different populations may genuinely differ
4. **Assess statistical power** — underpowered studies may miss real effects
5. **Check for publication bias** — are negative results missing?
6. **Look for dose-response patterns** — do results form a coherent pattern?
7. **Favor larger, more rigorous studies** when studies directly conflict

### For Making Evidence-Based Decisions
1. **Formulate a clear question** (PICO format for clinical questions)
2. **Search systematically** for all relevant evidence
3. **Appraise quality** of each piece of evidence
4. **Synthesize** findings across studies
5. **Grade the overall certainty** (e.g., using GRADE)
6. **Consider values and preferences** alongside evidence
7. **Apply with monitoring** and reassess as new evidence emerges

---

## Quick Reference: Evidence Evaluation Questions

| Question | What to Check |
|---|---|
| How strong is the study design? | Hierarchy level, appropriateness for question |
| How well was the study conducted? | Risk of bias assessment using appropriate tool |
| How large is the effect? | Effect size with confidence interval |
| How precise is the estimate? | Width of confidence interval |
| How consistent is the evidence? | Agreement across studies (I², visual inspection) |
| How direct is the evidence? | Match to your specific question (population, intervention, outcome) |
| Is there publication bias? | Funnel plot, registry comparison, small-study effects |
| What is the overall certainty? | GRADE or equivalent summary rating |
