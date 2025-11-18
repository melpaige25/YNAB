# YNAB Financial Analysis Tools

Two Python tools to help you understand and optimize your YNAB budget data.

## Tools Overview

### 1. Cash Flow Analyzer & Income Impact Calculator
**File:** `cash_flow_analyzer.py`

Analyzes your historical income and expenses, then lets you model "what-if" scenarios for additional income.

**Features:**
- Historical cash flow analysis (income vs expenses)
- Net worth growth tracking
- Interactive income scenario calculator
- Beautiful visualizations with 4 charts:
  - Income vs Expenses over time
  - Monthly cash flow trends
  - Net worth growth trajectory
  - Summary statistics

**What You'll Learn:**
- Average monthly income, expenses, and cash flow
- Your current savings rate
- Impact of additional income on debt payoff timeline
- Net worth projections (1 year, 5 years, 10 years)

### 2. Category Structure Optimizer
**File:** `category_optimizer.py`

Analyzes your 100+ budget categories and provides specific recommendations for simplification.

**Features:**
- Category usage analysis (frequency and consistency)
- Identifies rarely-used categories (<$100 total spending)
- Finds sporadic categories (used <30% of months)
- Detects uncategorized transactions
- Provides prioritized recommendations for cleanup

**What You'll Learn:**
- Which categories you actually use vs. which are dormant
- Where your money really goes (top spending categories)
- Specific suggestions for consolidating/eliminating categories
- Opportunities to simplify your budget structure

## Installation

### Prerequisites
```bash
# Install required Python packages
pip3 install pandas numpy matplotlib
```

## Usage

### Cash Flow Analyzer

```bash
# Basic usage - interactive mode
python3 cash_flow_analyzer.py
```

When prompted, enter additional monthly income amounts to see the impact:
- Example: Enter `500` to see impact of $500/month additional income
- Example: Enter `2000` to see impact of $2,000/month additional income
- Type `q` to quit

**Output:**
- Console report with detailed analysis
- `cash_flow_analysis.png` - 4-panel visualization

### Category Optimizer

```bash
# Run the analysis
python3 category_optimizer.py
```

**Output:**
- Comprehensive console report
- `category_analysis.csv` - Detailed data for further analysis in Excel

## Sample Results

### Cash Flow Analysis Results (Current)

Based on your data from Mar 2022 - Nov 2025:

```
Average Monthly Income:      $19,433
Average Monthly Expenses:    $16,587
Average Monthly Cash Flow:   $ 3,116
Savings Rate:                   16.0%

Current Net Worth:           $486,923
```

### Example: +$1,000/month Scenario

```
New Monthly Cash Flow:       $ 4,116 (+$1,000)
New Savings Rate:               20.1% (+4.1%)

Debt Payoff Impact:
  - Current timeline: 88.6 months
  - New timeline: 67.1 months
  - Saves: 21.5 months (24% faster!)

Net Worth Impact:
  - 1 year:  +$12,000
  - 5 years: +$60,000
  - 10 years: +$120,000
```

### Category Optimization Findings

```
Total Categories:                     112
Active Categories (>50% usage):       29
Sporadic Categories (<30% usage):     70
Rare Categories (<$100 total):        24

High Priority Recommendations:
  1. Clean up 30 inactive subscription categories
  2. Clarify 3 unclear categories (Unknown, Money Shuffling)
  3. Categorize 7 uncategorized transactions ($607.68)

Top Spending Categories:
  1. Medical/Health:           $93,987 (97.8% usage)
  2. Essentials, Food, Home:   $82,110 (100% usage)
  3. Education:                $58,248 (100% usage)
```

## Key Insights & Recommendations

### Financial Health Insights

1. **Strong Savings Rate**: 16% savings rate is solid
   - Above the recommended 10-15% minimum
   - Room for improvement toward 20%+ with additional income

2. **Top 10 Categories = 59% of Spending**
   - Focus budget optimization on these high-impact areas
   - Small changes here = big results

3. **Debt Payoff Opportunities**
   - Current debt: $276,297 ($238k mortgage + $38k remodel)
   - Additional $1,000/month saves 21.5 months of payments

### Category Structure Recommendations

1. **Subscription Cleanup** (High Priority)
   - 30 subscription categories rarely/never used
   - **Action**: Archive cancelled subscriptions
   - **Result**: Cleaner budget, easier to spot active subscriptions

2. **Consolidate Rare Categories** (Medium Priority)
   - 24 categories with <$100 total spending over 45 months
   - **Action**: Merge into broader categories
   - **Result**: Reduce decision fatigue, focus on what matters

3. **Education Category Grouping** (Consider)
   - Education expenses spread across 4 different groups
   - **Action**: Create single "Education & Development" group
   - **Result**: Easier to track total education investment

4. **Uncategorized Transactions** (Ongoing)
   - Currently 7 uncategorized ($607.68)
   - **Action**: Weekly review and categorization
   - **Result**: More accurate spending insights

## Files Generated

- `cash_flow_analysis.png` - Visual dashboard (4 charts)
- `category_analysis.csv` - Detailed category usage data
- Both analysis tools output to console with recommendations

## Tips for Best Results

1. **Export Fresh Data**: Before running these tools, export the latest YNAB reports
   - Budget → Reports → "Net Worth" and "Income vs Expense"
   - Include transaction-level detail if available

2. **Regular Analysis**: Run monthly to track progress
   - Cash Flow: See if savings rate is improving
   - Categories: Monitor cleanup progress

3. **Experiment with Scenarios**: Try various income levels
   - Example: Model spouse's potential job change
   - Example: Calculate impact of side hustle income
   - Example: Evaluate raise or promotion impact

4. **Act on Recommendations**: Start with High Priority items
   - Quick wins: Archive old subscription categories
   - Medium effort: Consolidate rare categories
   - Long-term: Restructure category groups

## Understanding Your Data

### Current Financial Picture
- **Net Worth**: $486,923 (Nov 2025)
- **Growth**: From $306k (Apr 2022) to $487k (47% increase in 3.5 years)
- **Annual Growth**: ~$51,000/year average

### Major Assets
- Retirement accounts: ~$828k (401k + IRAs)
- College savings (529s): ~$37k
- Banking/brokerage: Various

### Major Liabilities
- Mortgage: $238k
- Remodel loan: $38k

### Income Sources
- EA Tiburon (primary): $419,559 total
- Stock sales: $168,503 total
- Seminole State: $53,621 total

## Questions?

These tools analyze your exported YNAB data. They:
- Read your CSV exports
- Never modify YNAB data
- Generate reports and visualizations
- Help you make informed budget decisions

For YNAB-specific questions, visit: https://www.ynab.com/support

---

**Created:** November 2025
**Data Period:** March 2022 - November 2025 (45 months)
**Python Version:** 3.x
**Dependencies:** pandas, numpy, matplotlib
