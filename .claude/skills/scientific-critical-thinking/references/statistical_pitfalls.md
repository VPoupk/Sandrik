# Statistical Pitfalls: Common Errors and Misinterpretations

## Overview

Statistical misuse is one of the most pervasive problems in scientific research. This reference catalogs the most common statistical pitfalls with explanations of why they're wrong, how to detect them, and what correct practice looks like.

---

## 1. P-Value Misunderstandings

### What p-values actually mean
The p-value is the probability of observing data as extreme as (or more extreme than) the observed results, **assuming the null hypothesis is true**.

### Common Misinterpretations

| Misinterpretation | Reality |
|---|---|
| "p = 0.03 means there's a 3% chance the null is true" | P-value is P(data \| H₀), not P(H₀ \| data) |
| "p < 0.05 means the result is real/true" | Significance threshold is arbitrary; does not confirm truth |
| "p = 0.06 means no effect" | Non-significance ≠ no effect; may lack power |
| "p < 0.001 means a large effect" | P-values conflate effect size with sample size |
| "p = 0.049 is meaningfully different from p = 0.051" | These are essentially identical in evidence strength |
| "The result is highly significant (p < 0.001)" | Statistical significance is binary against chosen α; degrees of "significance" are misleading |

### Correct Practice
- Report exact p-values (e.g., p = 0.034, not p < 0.05)
- Always pair with effect sizes and confidence intervals
- Interpret p-values as continuous evidence, not binary decisions
- Consider the prior probability of the hypothesis (Bayesian thinking)
- Remember: a "significant" result from an underpowered study with a low prior may well be a false positive

### The ASA Statement on P-Values (Key Points)
1. P-values can indicate data incompatibility with a model
2. P-values do not measure the probability that a hypothesis is true
3. Scientific conclusions should not be based solely on p-value thresholds
4. Proper inference requires full reporting and transparency
5. A p-value does not measure the size or importance of an effect
6. A p-value alone does not provide a good measure of evidence

---

## 2. Multiple Comparisons Problem

### The Problem
When multiple statistical tests are performed, the probability of at least one false positive increases dramatically.

**Family-wise error rate:**
- 1 test at α = 0.05: 5% false positive rate
- 10 tests: 1 - (0.95)^10 = 40% chance of at least one false positive
- 20 tests: 1 - (0.95)^20 = 64% chance of at least one false positive
- 100 tests: 1 - (0.95)^100 = 99.4% chance of at least one false positive

### Common Scenarios
- Testing multiple outcomes
- Comparing multiple groups pairwise
- Testing at multiple time points
- Subgroup analyses
- Trying different model specifications

### Correction Methods

| Method | Approach | When to Use |
|---|---|---|
| **Bonferroni** | Divide α by number of tests | Conservative; few, independent tests |
| **Holm-Bonferroni** | Sequential rejection procedure | Less conservative than Bonferroni |
| **Benjamini-Hochberg (FDR)** | Controls false discovery rate | Many tests; discovery-oriented research |
| **Tukey's HSD** | Pairwise comparison correction | All pairwise group comparisons |
| **Šidák correction** | 1 - (1-α)^(1/k) | Independent tests |
| **Permutation tests** | Empirical null distribution | Non-parametric; preserves correlation structure |

### Detection
- Count the total number of statistical tests reported
- Check if any correction was applied
- Look for suspicious "significant" findings among many tested outcomes
- Examine whether primary outcomes were prespecified

---

## 3. Sample Size Issues

### Underpowered Studies
- **Problem**: Too few participants to detect real effects
- **Consequence**: True effects are missed (false negatives); detected effects are inflated ("winner's curse")
- **Detection**: Check for power analysis; small N with non-significant results; large confidence intervals
- **Rule of thumb**: Be suspicious of null findings from small samples

### Inflated Effect Sizes from Small Samples
- **Problem**: Significant findings from underpowered studies tend to overestimate the true effect
- **Why**: Only unusually large observed effects will reach significance when power is low
- **Detection**: Effect size seems implausibly large; small sample with significant result; effect shrinks in replication
- **Mitigation**: Use meta-analytic estimates; discount large effects from small studies; consider prior distributions

### Overpowered Studies
- **Problem**: Extremely large samples can make trivially small effects statistically significant
- **Consequence**: Statistically significant but practically meaningless results
- **Detection**: Very large N with very small effect sizes; very small p-values with tiny effects
- **Mitigation**: Focus on effect sizes and practical significance, not p-values alone

### Sample Size Determination
- **Best practice**: Conduct a priori power analysis based on:
  - Minimum effect size of practical interest
  - Desired power (typically 0.80 or higher)
  - Significance level (α)
  - Expected variability
- **Report**: How sample size was determined and whether target was met

---

## 4. Effect Size Mistakes

### Ignoring Effect Sizes
- **Problem**: Reporting only p-values without quantifying how large the effect is
- **Why it matters**: P-values tell you whether an effect exists; effect sizes tell you whether it matters
- **Correct practice**: Always report standardized or unstandardized effect sizes

### Common Effect Size Measures

| Measure | Type | Small | Medium | Large |
|---|---|---|---|---|
| Cohen's d | Mean difference | 0.2 | 0.5 | 0.8 |
| Pearson's r | Correlation | 0.1 | 0.3 | 0.5 |
| η² (eta-squared) | Variance explained | 0.01 | 0.06 | 0.14 |
| Odds Ratio | Binary outcome | 1.5 | 2.5 | 4.0 |
| Cohen's f | ANOVA | 0.1 | 0.25 | 0.4 |

*Note: Cohen's benchmarks are general guidelines. "Small," "medium," and "large" are context-dependent — a "small" effect in medicine may save thousands of lives.*

### Misinterpreting Effect Sizes
- Confusing r² with r (squaring reduces the apparent magnitude)
- Interpreting odds ratios as relative risks (they diverge when outcomes are common)
- Comparing effect sizes across different metrics without conversion
- Ignoring confidence intervals around effect sizes

---

## 5. Correlation and Causation

### The Core Problem
Correlation between X and Y can arise from:
1. **X causes Y** (direct causation)
2. **Y causes X** (reverse causation)
3. **Z causes both X and Y** (confounding)
4. **X causes Z causes Y** (mediation)
5. **Conditioning on a collider** (spurious association)
6. **Chance** (random variation, especially with small samples)

### Language Red Flags
Causal language from correlational/observational designs:
- "X leads to Y"
- "X increases/decreases Y"
- "X causes Y"
- "Y is due to X"
- "The effect of X on Y"

**Acceptable alternatives for observational data:**
- "X is associated with Y"
- "X predicts Y"
- "X and Y are correlated"
- "Higher X was observed alongside higher Y"

### When Can Observational Studies Support Causal Claims?
- Natural experiments with quasi-random assignment
- Instrumental variable approaches
- Regression discontinuity designs
- Interrupted time series
- Mendelian randomization
- When Bradford Hill criteria are substantially met

---

## 6. Regression Pitfalls

### Overfitting
- **Problem**: Model captures noise rather than signal
- **Detection**: High R² on training data, poor performance on new data; too many predictors relative to observations
- **Rule of thumb**: Need at least 10-20 observations per predictor for linear regression; more for logistic
- **Mitigation**: Cross-validation; regularization (LASSO, Ridge); information criteria (AIC, BIC)

### Extrapolation
- **Problem**: Making predictions outside the range of observed data
- **Detection**: Are predictions made for values of X not represented in the data?
- **Mitigation**: Clearly state the range of data; avoid predictions beyond observed range; use caution with projections

### Multicollinearity
- **Problem**: Predictor variables are highly correlated, making individual coefficients unstable
- **Detection**: High VIF (Variance Inflation Factor > 5-10); coefficients change dramatically when predictors are added/removed; large standard errors
- **Mitigation**: Remove redundant predictors; use PCA or factor analysis; combine correlated variables; use regularization

### Omitted Variable Bias
- **Problem**: A relevant variable is excluded from the model, biasing other coefficients
- **Detection**: Are important confounders missing? Does the model have a theoretical basis for included variables?
- **Mitigation**: Include known confounders; use DAGs to identify required adjustments; acknowledge unmeasured confounding

### Inappropriate Linearity Assumptions
- **Problem**: Assuming a linear relationship when it's actually curved, threshold-based, or otherwise nonlinear
- **Detection**: Plot residuals vs. fitted values; examine scatterplots; test polynomial or spline terms
- **Mitigation**: Use residual diagnostics; consider nonlinear models; transform variables; use GAMs or splines

### Ecological Fallacy in Regression
- **Problem**: Group-level regression coefficients don't apply to individuals
- **Detection**: Is the analysis at a group level but conclusions are at an individual level?
- **Mitigation**: Use individual-level data; multi-level modeling; be explicit about level of analysis

---

## 7. Confidence Interval Misinterpretations

### Common Errors

| Misinterpretation | Reality |
|---|---|
| "95% CI means 95% chance the true value is in this range" | The true value is fixed; 95% of CIs from repeated sampling would contain it |
| "Values outside the CI are impossible" | Values outside are less compatible with data, not impossible |
| "Non-overlapping CIs mean significant difference" | CIs can overlap and still be significantly different (use CI of the difference) |
| "Narrow CI means the result is correct" | Narrow CI means high precision, not accuracy (systematic bias can exist) |

### Correct Interpretation
A 95% CI represents a range of values that are reasonably compatible with the observed data, given the statistical model and its assumptions.

### What to Look For
- Width of CI (precision of estimate)
- Whether CI includes clinically/practically meaningful values
- Whether CI includes null value (e.g., 0 for differences, 1 for ratios)
- Asymmetry (may indicate skewness or transformation issues)

---

## 8. Bayesian vs. Frequentist Confusions

### Key Differences

| Aspect | Frequentist | Bayesian |
|---|---|---|
| Probability refers to | Long-run frequency of events | Degree of belief/uncertainty |
| Parameters are | Fixed but unknown | Random variables with distributions |
| Key output | P-values, confidence intervals | Posterior distributions, credible intervals |
| Prior information | Not formally incorporated | Explicitly modeled |

### Common Confusion
- Interpreting frequentist results in Bayesian terms (e.g., treating p-values as posterior probabilities)
- Ignoring base rates when interpreting significant results
- Not recognizing that a p < 0.05 result may have a high false positive rate if the prior probability of the hypothesis is low

---

## 9. Missing Data Problems

### Types of Missing Data
1. **MCAR (Missing Completely at Random)**: Missingness unrelated to any variables — safest but rarest
2. **MAR (Missing at Random)**: Missingness related to observed but not unobserved data — can be handled with proper methods
3. **MNAR (Missing Not at Random)**: Missingness related to the unobserved value itself — most problematic

### Common (Often Inappropriate) Approaches
| Method | Problem |
|---|---|
| Complete case analysis (listwise deletion) | Loses data; biased if not MCAR |
| Mean imputation | Underestimates variance; distorts relationships |
| Last observation carried forward (LOCF) | Assumes no change; biased in many scenarios |
| Zero imputation | Almost always inappropriate |

### Better Approaches
- Multiple imputation (MI)
- Maximum likelihood estimation
- Full information maximum likelihood (FIML)
- Pattern mixture models (for MNAR)
- Sensitivity analyses to test assumptions

### Detection Questions
- How much data is missing? (>5-10% warrants concern)
- Is missingness related to the outcome or exposure?
- How was missing data handled?
- Were sensitivity analyses conducted?

---

## 10. Meta-Analysis Pitfalls

### Garbage In, Garbage Out
- Meta-analyzing low-quality studies produces a precise but potentially biased estimate
- Quality assessment should precede or accompany synthesis

### Heterogeneity Ignored
- If studies are too different (clinically or statistically), combining them may be misleading
- Check I² statistic (>50% suggests substantial heterogeneity)
- Use random-effects models when heterogeneity is expected
- Explore sources of heterogeneity through subgroup analysis or meta-regression

### Publication Bias in Meta-Analysis
- If negative studies are missing, the pooled estimate is inflated
- Detection: Funnel plot asymmetry; Egger's test; trim-and-fill; p-curve
- Mitigation: Search for unpublished studies; use bias-adjusted estimators

### Apples and Oranges
- Combining studies with different populations, interventions, or outcomes
- Just because studies examine "similar" topics doesn't mean they should be pooled
- Clinical and methodological homogeneity should be assessed before statistical pooling

---

## Quick Reference: Statistical Checklist for Readers

1. **Was sample size justified?** (power analysis reported?)
2. **Are the right tests used?** (matched to data type and design?)
3. **Were assumptions checked?** (normality, homogeneity, independence?)
4. **Is multiple testing addressed?** (correction applied if needed?)
5. **Are effect sizes reported?** (with confidence intervals?)
6. **Are p-values interpreted correctly?** (not treated as probability of truth?)
7. **Is missing data addressed?** (amount, mechanism, handling?)
8. **Are causal claims supported?** (design supports causation, not just association?)
9. **Is overfitting possible?** (too many predictors? cross-validation used?)
10. **Are results practically meaningful?** (not just statistically significant?)
