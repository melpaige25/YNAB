#!/usr/bin/env python3
"""
YNAB Category Structure Optimization Analyzer
Analyzes category usage and provides recommendations for optimization
"""

import pandas as pd
import numpy as np
from pathlib import Path
from collections import defaultdict

class YNABCategoryOptimizer:
    def __init__(self, base_dir="."):
        """Initialize category optimizer"""
        self.base_dir = Path(base_dir)
        self.spending_df = None
        self.transactions_df = None
        self.months = []

    def load_data(self):
        """Load YNAB spending breakdown data"""
        # Find spending breakdown files
        spending_files = list(self.base_dir.glob("**/ynab-reflect-spending-breakdown*.csv"))
        transaction_files = list(self.base_dir.glob("**/ynab-reflect-*-transactions.csv"))

        # Exclude the transactions files from spending files
        spending_files = [f for f in spending_files if 'transactions' not in f.name]

        if not spending_files:
            print("Error: Could not find spending breakdown CSV file")
            return False

        # Load spending breakdown
        spending_file = sorted(spending_files)[-1]
        print(f"Loading spending data from: {spending_file.name}")
        self.spending_df = pd.read_csv(spending_file)

        # Load transactions if available
        if transaction_files:
            trans_file = sorted(transaction_files)[-1]
            print(f"Loading transaction data from: {trans_file.name}")
            try:
                self.transactions_df = pd.read_csv(trans_file)
                print(f"  Loaded {len(self.transactions_df)} transactions")
            except Exception as e:
                print(f"  Warning: Could not load transactions: {e}")
                self.transactions_df = None

        # Extract month columns
        self.months = [col for col in self.spending_df.columns
                      if col not in ['Category Group', 'Category', 'Average', 'Total']]

        print(f"Loaded spending data for {len(self.months)} months")
        print(f"Found {len(self.spending_df)} categories")

        return True

    def analyze_category_usage(self):
        """Analyze how frequently and consistently each category is used"""
        analysis = []

        for idx, row in self.spending_df.iterrows():
            category_group = row['Category Group']
            category = row['Category']

            # Skip empty categories
            if pd.isna(category) or category == '':
                continue

            # Get monthly values
            monthly_values = []
            for month in self.months:
                val = row[month]
                if pd.notna(val):
                    monthly_values.append(float(val))
                else:
                    monthly_values.append(0.0)

            # Calculate statistics
            monthly_array = np.array(monthly_values)
            non_zero_months = np.count_nonzero(monthly_array)
            total_spent = abs(monthly_array.sum())
            avg_monthly = abs(monthly_array.mean())

            # Calculate usage percentage
            usage_pct = (non_zero_months / len(monthly_values)) * 100

            # Check for inconsistent usage (sporadic)
            is_sporadic = usage_pct < 30  # Used in less than 30% of months
            is_rare = total_spent < 100  # Less than $100 total

            analysis.append({
                'category_group': category_group,
                'category': category,
                'total_spent': total_spent,
                'avg_monthly': avg_monthly,
                'months_used': non_zero_months,
                'usage_pct': usage_pct,
                'is_sporadic': is_sporadic,
                'is_rare': is_rare
            })

        return pd.DataFrame(analysis)

    def find_uncategorized_transactions(self):
        """Find transactions that aren't categorized"""
        if self.transactions_df is None:
            return None

        # Look for empty or uncategorized transactions
        uncategorized = self.transactions_df[
            (self.transactions_df['Category'].isna()) |
            (self.transactions_df['Category'] == '') |
            (self.transactions_df['Category'] == 'Uncategorized')
        ]

        return uncategorized

    def identify_similar_categories(self, analysis_df):
        """Identify potentially redundant or overlapping categories"""
        similar_pairs = []

        # Group by category group
        for group in analysis_df['category_group'].unique():
            if pd.isna(group) or group == '':
                continue

            group_cats = analysis_df[analysis_df['category_group'] == group]

            # Look for similar patterns
            categories = group_cats['category'].tolist()

            # Check for similar names or purposes
            for i, cat1 in enumerate(categories):
                for cat2 in categories[i+1:]:
                    # Simple similarity check - could be enhanced
                    if self._are_similar(cat1, cat2):
                        cat1_data = group_cats[group_cats['category'] == cat1].iloc[0]
                        cat2_data = group_cats[group_cats['category'] == cat2].iloc[0]

                        similar_pairs.append({
                            'group': group,
                            'category1': cat1,
                            'category2': cat2,
                            'total1': cat1_data['total_spent'],
                            'total2': cat2_data['total_spent'],
                            'reason': 'Similar names'
                        })

        return similar_pairs

    def _are_similar(self, cat1, cat2):
        """Check if two category names are similar"""
        # Simple similarity checks
        cat1_lower = str(cat1).lower()
        cat2_lower = str(cat2).lower()

        # Remove emojis and special chars for comparison
        cat1_clean = ''.join(c for c in cat1_lower if c.isalnum() or c.isspace())
        cat2_clean = ''.join(c for c in cat2_lower if c.isalnum() or c.isspace())

        # Check if one contains the other
        if cat1_clean in cat2_clean or cat2_clean in cat1_clean:
            return True

        return False

    def generate_recommendations(self, analysis_df):
        """Generate optimization recommendations"""
        recommendations = []

        # 1. Identify rarely used categories
        rare_cats = analysis_df[analysis_df['is_rare'] == True]
        if len(rare_cats) > 0:
            recommendations.append({
                'type': 'CONSOLIDATE_RARE',
                'priority': 'Medium',
                'title': 'Consolidate Rarely Used Categories',
                'description': f'Found {len(rare_cats)} categories with less than $100 total spending',
                'categories': rare_cats['category'].tolist(),
                'suggestion': 'Consider combining these into more general categories'
            })

        # 2. Identify sporadic categories
        sporadic_cats = analysis_df[
            (analysis_df['is_sporadic'] == True) &
            (analysis_df['is_rare'] == False)
        ]
        if len(sporadic_cats) > 0:
            recommendations.append({
                'type': 'REVIEW_SPORADIC',
                'priority': 'Low',
                'title': 'Review Sporadically Used Categories',
                'description': f'Found {len(sporadic_cats)} categories used in less than 30% of months',
                'categories': sporadic_cats['category'].tolist(),
                'suggestion': 'Consider if these need dedicated categories or can be merged'
            })

        # 3. Analyze subscription categories
        subscription_cats = analysis_df[
            analysis_df['category_group'] == 'Subscriptions ⏱️'
        ]
        if len(subscription_cats) > 0:
            active_subs = subscription_cats[subscription_cats['months_used'] >= len(self.months) * 0.8]
            inactive_subs = subscription_cats[subscription_cats['months_used'] < len(self.months) * 0.2]

            if len(inactive_subs) > 0:
                recommendations.append({
                    'type': 'CLEAN_SUBSCRIPTIONS',
                    'priority': 'High',
                    'title': 'Clean Up Inactive Subscriptions',
                    'description': f'Found {len(inactive_subs)} subscription categories rarely used',
                    'categories': inactive_subs['category'].tolist(),
                    'suggestion': 'Remove categories for cancelled subscriptions, or use "Subscriptions to Categorize" bucket'
                })

        # 4. Check for "Unknown" or unclear categories
        unclear_cats = analysis_df[
            analysis_df['category'].str.contains('Unknown|Money Shuffling|to Categorize|unclear',
                                                 case=False, na=False)
        ]
        if len(unclear_cats) > 0:
            recommendations.append({
                'type': 'CLARIFY_UNCLEAR',
                'priority': 'High',
                'title': 'Clarify Unclear Categories',
                'description': f'Found {len(unclear_cats)} categories with unclear purposes',
                'categories': unclear_cats['category'].tolist(),
                'suggestion': 'Review and properly categorize or eliminate these catch-all categories'
            })

        # 5. Analyze category distribution
        total_spending = analysis_df['total_spent'].sum()
        top_categories = analysis_df.nlargest(10, 'total_spent')
        top_10_pct = (top_categories['total_spent'].sum() / total_spending) * 100

        recommendations.append({
            'type': 'FOCUS_INSIGHT',
            'priority': 'Info',
            'title': 'Category Focus Insight',
            'description': f'Top 10 categories account for {top_10_pct:.1f}% of all spending',
            'categories': top_categories['category'].tolist(),
            'suggestion': 'Focus budget management efforts on these high-impact categories'
        })

        # 6. Check for "Paying Off" category structure
        paying_off = analysis_df[analysis_df['category_group'] == 'Paying Off']
        if len(paying_off) > 0:
            completed = paying_off[paying_off['months_used'] < 5]  # Not used in recent months
            if len(completed) > 0:
                recommendations.append({
                    'type': 'ARCHIVE_PAID_OFF',
                    'priority': 'Low',
                    'title': 'Archive Paid-Off Items',
                    'description': f'Found {len(completed)} items in "Paying Off" that appear complete',
                    'categories': completed['category'].tolist(),
                    'suggestion': 'Archive or remove categories for items that are fully paid off'
                })

        return recommendations

    def print_analysis_report(self, analysis_df, recommendations):
        """Print comprehensive analysis report"""
        print("\n" + "="*100)
        print("YNAB CATEGORY STRUCTURE OPTIMIZATION REPORT")
        print("="*100)

        # Summary Statistics
        print("\n--- CATEGORY OVERVIEW ---")
        print(f"  Total Categories:                    {len(analysis_df)}")
        print(f"  Active Categories (used >50% time):  {len(analysis_df[analysis_df['usage_pct'] > 50])}")
        print(f"  Sporadic Categories (<30% time):     {len(analysis_df[analysis_df['is_sporadic']])}")
        print(f"  Rare Categories (<$100 total):       {len(analysis_df[analysis_df['is_rare']])}")

        # Category Groups
        print("\n--- CATEGORY GROUPS ---")
        groups = analysis_df.groupby('category_group').agg({
            'category': 'count',
            'total_spent': 'sum'
        }).sort_values('total_spent', ascending=False)

        for group, data in groups.iterrows():
            if pd.notna(group) and group != '':
                print(f"  {group:45s}  {data['category']:3.0f} categories  ${data['total_spent']:>12,.2f}")

        # Top Spending Categories
        print("\n--- TOP 15 SPENDING CATEGORIES ---")
        top_cats = analysis_df.nlargest(15, 'total_spent')
        for idx, row in top_cats.iterrows():
            usage_bar = '█' * int(row['usage_pct'] / 5) + '░' * (20 - int(row['usage_pct'] / 5))
            print(f"  {row['category']:45s}  ${row['total_spent']:>10,.0f}  {usage_bar} {row['usage_pct']:>5.1f}%")

        # Uncategorized Transactions
        if self.transactions_df is not None:
            uncategorized = self.find_uncategorized_transactions()
            if uncategorized is not None and len(uncategorized) > 0:
                # Convert Outflow to numeric, removing $ signs if present
                outflow_values = pd.to_numeric(uncategorized['Outflow'].astype(str).str.replace('$', '').str.replace(',', ''), errors='coerce').fillna(0)
                total_uncategorized = outflow_values.sum()
                print("\n--- UNCATEGORIZED TRANSACTIONS ---")
                print(f"  Count:  {len(uncategorized)} transactions")
                print(f"  Total:  ${total_uncategorized:,.2f}")
                print("\n  Recent Uncategorized Transactions:")
                for idx, trans in uncategorized.head(10).iterrows():
                    outflow = pd.to_numeric(str(trans['Outflow']).replace('$', '').replace(',', ''), errors='coerce')
                    if pd.notna(outflow):
                        print(f"    {trans['Date']:10s}  {trans['Payee']:30s}  ${outflow:>10,.2f}")

        # Recommendations
        print("\n" + "="*100)
        print("OPTIMIZATION RECOMMENDATIONS")
        print("="*100)

        high_priority = [r for r in recommendations if r['priority'] == 'High']
        medium_priority = [r for r in recommendations if r['priority'] == 'Medium']
        low_priority = [r for r in recommendations if r['priority'] == 'Low']
        info_items = [r for r in recommendations if r['priority'] == 'Info']

        for priority_group, priority_name in [(high_priority, 'HIGH PRIORITY'),
                                                (medium_priority, 'MEDIUM PRIORITY'),
                                                (low_priority, 'LOW PRIORITY'),
                                                (info_items, 'INSIGHTS')]:
            if priority_group:
                print(f"\n--- {priority_name} ---\n")
                for rec in priority_group:
                    print(f"  {rec['title']}")
                    print(f"  {'-' * 90}")
                    print(f"  Description: {rec['description']}")
                    print(f"  Suggestion:  {rec['suggestion']}")
                    if len(rec['categories']) <= 10:
                        print(f"  Categories:  {', '.join(str(c) for c in rec['categories'])}")
                    else:
                        print(f"  Categories:  {', '.join(str(c) for c in rec['categories'][:10])}")
                        print(f"               ... and {len(rec['categories']) - 10} more")
                    print()

        # Specific Optimization Suggestions
        print("\n" + "="*100)
        print("SPECIFIC OPTIMIZATION SUGGESTIONS")
        print("="*100)

        print("\n1. SUBSCRIPTION MANAGEMENT")
        print("   Current: Individual categories for each subscription service")
        print("   Suggestion: Consider consolidating rarely-used subscriptions into a single")
        print("               'Misc Subscriptions' category, keeping detailed categories only for")
        print("               major subscriptions (>$20/month or used year-round)")

        print("\n2. CATEGORY GROUP CONSOLIDATION")
        print("   Current: 'Day to Day Variables' and 'Variable Expenses' groups")
        print("   Potential overlap: Review if some categories could be merged")
        print("   Example: Consider if 'Holiday/Party Spending', 'Gifts/Presents', and 'Charity'")
        print("            could be under a single 'Giving' category group")

        print("\n3. EMOJI USAGE")
        print("   Current: Many categories use emojis for visual identification")
        print("   Suggestion: This is helpful! Consider adding emojis to ALL categories for")
        print("               consistency and easier visual scanning")

        print("\n4. EDUCATION TRACKING")
        print("   Current: Education expenses across multiple categories")
        print("   Present in: 'Day to Day Variables: Education', 'Fixed Monthly Expenses: School',")
        print("               'Fixed Infrequent Expenses: Kids College Funds',")
        print("               'Fixed Monthly Expenses: Mel Education'")
        print("   Suggestion: Consider if these should all be in one 'Education' category group")
        print("               for easier education budget management")

        print("\n5. 'UNKNOWN' AND 'UNCATEGORIZED' CATEGORIES")
        print("   Suggestion: Set a monthly reminder to review and properly categorize these")
        print("               transactions. Aim to eliminate these categories over time.")

        print("\n" + "="*100)

def main():
    """Main entry point"""
    print("="*100)
    print("YNAB CATEGORY STRUCTURE OPTIMIZATION ANALYZER")
    print("="*100)

    # Initialize optimizer
    optimizer = YNABCategoryOptimizer()

    # Load data
    if not optimizer.load_data():
        return

    # Analyze category usage
    print("\nAnalyzing category usage patterns...")
    analysis_df = optimizer.analyze_category_usage()

    # Generate recommendations
    print("Generating optimization recommendations...")
    recommendations = optimizer.generate_recommendations(analysis_df)

    # Print report
    optimizer.print_analysis_report(analysis_df, recommendations)

    # Save detailed analysis to CSV
    output_file = 'category_analysis.csv'
    analysis_df.to_csv(output_file, index=False)
    print(f"\n\nDetailed analysis saved to: {output_file}")
    print("="*100)

if __name__ == "__main__":
    main()
