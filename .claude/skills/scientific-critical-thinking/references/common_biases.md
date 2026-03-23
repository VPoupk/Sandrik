# Common Biases: Comprehensive Taxonomy

## Overview

Bias in research refers to any systematic error that distorts findings away from the truth. Understanding bias is essential for evaluating research quality and designing rigorous studies. This reference organizes biases by category with detection strategies and mitigation approaches.

---

## 1. Cognitive Biases (Researcher)

These biases stem from how researchers think, perceive, and make decisions.

### Confirmation Bias
- **Definition**: Tendency to search for, interpret, and recall information that confirms pre-existing beliefs
- **Detection**: Are only supporting findings highlighted? Are contradictory results dismissed or minimized? Is the literature review one-sided?
- **Mitigation**: Preregister hypotheses; actively seek disconfirming evidence; use blinded analysis; include devil's advocate in team

### Anchoring Bias
- **Definition**: Over-reliance on the first piece of information encountered when making decisions
- **Detection**: Were initial findings or estimates given disproportionate weight? Did early results shape interpretation of later data?
- **Mitigation**: Consider multiple starting points; use systematic analysis protocols; have independent analysts review data

### HARKing (Hypothesizing After Results are Known)
- **Definition**: Presenting post-hoc hypotheses as if they were a priori predictions
- **Detection**: Were hypotheses stated before data collection? Do hypotheses suspiciously match results? Check for preregistration
- **Mitigation**: Preregister studies; clearly label exploratory vs. confirmatory analyses; time-stamp hypothesis documents

### Hindsight Bias
- **Definition**: After learning an outcome, believing it was predictable all along
- **Detection**: Do authors claim findings were "expected" without prior documentation? Are post-hoc explanations presented as predictions?
- **Mitigation**: Document predictions before seeing results; compare actual predictions to outcomes

### Bandwagon Effect
- **Definition**: Adopting beliefs or methods because others have adopted them
- **Detection**: Is the rationale "everyone does it this way"? Are popular methods used without evaluating fit?
- **Mitigation**: Evaluate methods on their merits for each specific question; consider alternatives

### Dunning-Kruger Effect
- **Definition**: Overestimating competence in areas of limited expertise
- **Detection**: Are conclusions drawn outside the authors' expertise? Is confidence disproportionate to evidence?
- **Mitigation**: Seek expert collaborators; have specialists review relevant sections

---

## 2. Selection Biases

These biases arise from how participants, samples, or studies are chosen.

### Sampling Bias
- **Definition**: Sample is not representative of the target population
- **Detection**: Compare sample demographics to target population; check inclusion/exclusion criteria for systematic exclusions
- **Mitigation**: Random sampling; stratified sampling; report sample characteristics and acknowledge limitations

### Volunteer/Self-Selection Bias
- **Definition**: Participants who volunteer differ systematically from those who do not
- **Detection**: Are participants self-selected? What motivations might drive participation? Compare participants to eligible non-participants
- **Mitigation**: Minimize barriers to participation; incentivize broadly; track and report participation rates

### Attrition Bias (Differential Dropout)
- **Definition**: Participants leave the study at different rates across groups
- **Detection**: Compare dropout rates between groups; compare completers vs. non-completers on baseline characteristics; check intent-to-treat vs. per-protocol analysis
- **Mitigation**: Minimize dropout; use intent-to-treat analysis; conduct sensitivity analyses; report reasons for dropout

### Survivorship Bias
- **Definition**: Analyzing only cases that "survived" a selection process, ignoring those that did not
- **Detection**: Are failures or non-survivors invisible in the data? Could successful cases be systematically different from unsuccessful ones?
- **Mitigation**: Include both successful and unsuccessful cases; consider what data might be missing

### Berkson's Bias (Collider Bias)
- **Definition**: Spurious association created by conditioning on a common effect of two variables
- **Detection**: Is the sample restricted to a subset defined by a variable influenced by both exposure and outcome?
- **Mitigation**: Use population-based samples; avoid conditioning on colliders; use causal diagrams (DAGs)

### Healthy Worker Effect
- **Definition**: Working populations appear healthier than the general population because severely ill individuals are excluded
- **Detection**: Is the comparison between workers and the general population? Could baseline health differ?
- **Mitigation**: Use appropriate comparison groups; acknowledge the effect; use internal comparisons

### Immortal Time Bias
- **Definition**: A period during which the outcome cannot occur is misclassified
- **Detection**: Is there a gap between cohort entry and treatment start? Is follow-up time before treatment counted?
- **Mitigation**: Use time-dependent analysis; align start of follow-up with treatment start; use landmark analysis

---

## 3. Measurement Biases

These biases affect the accuracy and consistency of data collection.

### Observer/Experimenter Bias
- **Definition**: Researcher expectations influence data collection, recording, or interpretation
- **Detection**: Was the outcome assessor blinded? Could expectations have influenced measurements? Are subjective measures used?
- **Mitigation**: Blind outcome assessors; use objective measures; standardize protocols; use multiple independent assessors

### Recall Bias
- **Definition**: Systematic differences in how groups remember and report past exposures
- **Detection**: Are cases more motivated to recall exposures than controls? Is information collected retrospectively?
- **Mitigation**: Use prospective designs; verify self-reports with records; use standardized instruments; include memory aids

### Social Desirability Bias
- **Definition**: Participants respond in ways they believe are socially acceptable rather than truthfully
- **Detection**: Are sensitive topics assessed by self-report? Do results seem implausibly positive?
- **Mitigation**: Use anonymous surveys; indirect questioning techniques; validated instruments designed to reduce social desirability; objective measures

### Hawthorne Effect
- **Definition**: Participants change behavior because they know they are being observed
- **Detection**: Could awareness of being studied change the outcome? Is there a "novelty" effect?
- **Mitigation**: Use unobtrusive measures; include observation-only control group; allow acclimatization periods; use deception (ethically)

### Measurement/Instrument Bias
- **Definition**: Systematic error in a measurement tool that consistently over- or under-estimates values
- **Detection**: Is the instrument calibrated? Has it been validated against a gold standard? Is there drift over time?
- **Mitigation**: Use validated instruments; calibrate regularly; use multiple measurement methods; report reliability

### Lead-Time Bias
- **Definition**: Earlier detection appears to improve survival even when it doesn't, because the clock starts ticking sooner
- **Detection**: Is a screening group compared to a non-screening group on survival? Could earlier diagnosis explain apparent benefit?
- **Mitigation**: Use mortality as outcome rather than survival time; compare from same calendar time, not diagnosis time

### Information Bias (Misclassification)
- **Definition**: Errors in classifying exposure or outcome status
- **Non-differential**: Misclassification is equal across groups → biases toward null
- **Differential**: Misclassification differs between groups → biases in either direction
- **Mitigation**: Use validated classification criteria; blind assessors; use multiple data sources

---

## 4. Statistical and Analytical Biases

These biases emerge during data analysis and interpretation.

### P-Hacking
- **Definition**: Manipulating data analysis until non-significant results become significant
- **Forms**: Testing multiple outcomes; trying different statistical models; selectively excluding data points; optional stopping; transforming variables until significant
- **Detection**: Suspicious clustering of p-values just below 0.05; many analyses reported; vague analysis plan; results that don't replicate
- **Mitigation**: Preregister analysis plan; report all analyses; use correction for multiple comparisons; consider p-curve analysis

### Outcome Switching
- **Definition**: Changing the primary outcome after seeing results to report more favorable findings
- **Detection**: Compare published outcomes to preregistration or protocol; check if primary outcome changed between protocol and publication
- **Mitigation**: Preregister primary outcomes; compare published papers to registered protocols; check trial registries

### Selective Reporting
- **Definition**: Reporting only favorable or significant results while suppressing others
- **Detection**: Are all planned outcomes reported? Do methods describe analyses not in results? Check supplementary materials and preregistration
- **Mitigation**: Preregister all outcomes; require complete reporting; check against protocol; use reporting guidelines

### Publication Bias
- **Definition**: Studies with significant results are more likely to be published than those with null results
- **Detection**: Funnel plot asymmetry in meta-analyses; Egger's test; compare published results to registered studies
- **Mitigation**: Preregister studies; publish null results; search grey literature; use bias-adjusted meta-analytic methods

### Subgroup Fishing (Data Dredging)
- **Definition**: Testing many subgroup analyses without correction until a significant one is found
- **Detection**: Were subgroup analyses prespecified? Is there a biological rationale? Were corrections applied for multiple tests?
- **Mitigation**: Prespecify subgroup analyses; limit their number; require biological plausibility; use interaction tests; correct for multiplicity

### Regression to the Mean
- **Definition**: Extreme values on first measurement tend to be less extreme on subsequent measurement, regardless of intervention
- **Detection**: Were participants selected based on extreme scores? Is there no control group? Could improvement be regression rather than treatment effect?
- **Mitigation**: Include a control group; use randomization; account for baseline values in analysis

### Overfitting
- **Definition**: A model fits noise in the training data rather than the true signal, leading to poor generalization
- **Detection**: Model performs much better on training data than test data; too many predictors relative to sample size; model captures implausible relationships
- **Mitigation**: Use cross-validation; limit model complexity; use regularization; validate on held-out data; follow sample size guidelines

### Simpson's Paradox
- **Definition**: A trend that appears in several groups reverses when the groups are combined
- **Detection**: Do subgroup results differ from overall results? Are there confounding variables that create different subgroup proportions?
- **Mitigation**: Always examine subgroup patterns; use appropriate stratification or adjustment; identify confounders

---

## 5. Study Design Biases

These biases are inherent to certain study designs or research contexts.

### Allocation Bias
- **Definition**: Systematic differences in how participants are assigned to groups
- **Detection**: Was randomization properly implemented? Was allocation concealed? Were groups balanced at baseline?
- **Mitigation**: Use computer-generated randomization; conceal allocation sequence; verify baseline balance; use stratified randomization

### Performance Bias
- **Definition**: Systematic differences in care or exposure between groups beyond the intervention
- **Detection**: Were participants or providers aware of group assignment? Could knowledge of assignment influence behavior?
- **Mitigation**: Blind participants and providers; use placebo controls; standardize co-interventions

### Detection Bias
- **Definition**: Systematic differences in how outcomes are ascertained between groups
- **Detection**: Were outcome assessors blinded? Could knowledge of group assignment influence measurement?
- **Mitigation**: Blind outcome assessors; use objective outcomes; standardize assessment procedures

### Reporting Bias (Within Study)
- **Definition**: Selective reporting of outcomes based on results
- **Detection**: Compare protocol/registration to published paper; are some outcomes mentioned in methods but not results?
- **Mitigation**: Preregister all outcomes; follow reporting guidelines; require protocol comparison

### Ecological Fallacy
- **Definition**: Inferring individual-level relationships from group-level data
- **Detection**: Are conclusions about individuals drawn from aggregate data? Could within-group variation be large?
- **Mitigation**: Use individual-level data when possible; avoid individual-level claims from ecological data; conduct multi-level analyses

### Time-Related Biases
- **Protopathic bias**: Early symptoms of the outcome cause the exposure (reverse causation)
- **Length-time bias**: Slower-progressing cases are more likely detected by screening
- **Detection time bias**: Earlier detection ≠ better outcome
- **Mitigation**: Use appropriate lag periods; consider disease natural history; use proper comparison groups

---

## Quick Reference: Bias Detection Checklist

### When Reading a Study, Ask:
1. **Selection**: How were participants chosen? Could selection create systematic differences?
2. **Allocation**: How were groups formed? Was randomization adequate?
3. **Blinding**: Who knew about group assignments? Could this influence results?
4. **Measurement**: How were outcomes measured? Could measurement differ between groups?
5. **Attrition**: Did participants drop out? Was dropout related to treatment or outcome?
6. **Analysis**: Were all outcomes reported? Were corrections applied? Was the analysis plan prespecified?
7. **Reporting**: Do published results match the registered protocol?
8. **Conflicts**: Do authors have financial or intellectual conflicts of interest?

### Severity Classification
- **Critical**: Bias likely changes the direction or existence of the main finding
- **Serious**: Bias likely inflates or deflates the effect substantially
- **Moderate**: Bias may affect the finding but unlikely to change the conclusion
- **Low**: Bias is possible but unlikely to meaningfully affect results
