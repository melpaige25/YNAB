#!/usr/bin/env python3
"""
2026 Income Impact Analysis
Analyzes how additional income sources in 2026 have affected monthly cash flow
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

class Income2026Analyzer:
    def __init__(self, base_dir="."):
        """Initialize 2026 income analyzer"""
        self.base_dir = Path(base_dir)
        self.historical_data = None
        self.data_2026 = None

    def load_data(self):
        """Load historical and 2026 income data"""

        # Load 2025/historical data
        historical_file = self.base_dir / "ynab-reflect-income-expense-2025-11-18.csv"
        if historical_file.exists():
            print(f"Loading historical data: {historical_file.name}")
            hist_df = pd.read_csv(historical_file)

            # Get income categories and their values
            self.historical_data = {}

            # Extract all income source rows (before "Total Income")
            total_income_idx = hist_df[hist_df['Category'] == 'Total Income'].index
            if len(total_income_idx) > 0:
                income_rows = hist_df.iloc[1:total_income_idx[0]]  # Skip "All Income Sources" row

                # Get month columns
                month_cols = [col for col in hist_df.columns
                             if col not in ['Category', 'Average', 'Total']]

                for _, row in income_rows.iterrows():
                    category = row['Category']
                    if pd.notna(category) and category != '':
                        self.historical_data[category] = {
                            month: float(row[month]) if pd.notna(row[month]) else 0
                            for month in month_cols
                        }

        # Load 2026 data
        file_2026 = self.base_dir / "ynab-reflect-income-expense-2026-05-17.csv"
        if file_2026.exists():
            print(f"Loading 2026 data: {file_2026.name}")
            df_2026 = pd.read_csv(file_2026)

            self.data_2026 = {}

            # Extract income sources
            total_income_idx = df_2026[df_2026['Category'] == 'Total Income'].index
            if len(total_income_idx) > 0:
                income_rows = df_2026.iloc[1:total_income_idx[0]]

                month_cols = [col for col in df_2026.columns
                             if col not in ['Category', 'Average', 'Total']]

                for _, row in income_rows.iterrows():
                    category = row['Category']
                    if pd.notna(category) and category != '':
                        self.data_2026[category] = {
                            month: float(row[month]) if pd.notna(row[month]) else 0
                            for month in month_cols
                        }

            # Also get expense data
            self.expenses_2026 = {}
            expense_row = df_2026[df_2026['Category'] == 'Total Expenses']
            if not expense_row.empty:
                for month in month_cols:
                    self.expenses_2026[month] = abs(float(expense_row[month].values[0]))

        return True

    def identify_new_income_sources(self):
        """Identify income sources that are new in 2026"""

        historical_sources = set(self.historical_data.keys())
        sources_2026 = set(self.data_2026.keys())

        new_sources = sources_2026 - historical_sources
        continuing_sources = sources_2026 & historical_sources

        return new_sources, continuing_sources

    def calculate_historical_baseline(self):
        """Calculate average historical income by source"""

        baseline = {}

        for source, monthly_data in self.historical_data.items():
            values = [v for v in monthly_data.values() if v > 0]
            if values:
                baseline[source] = {
                    'avg': np.mean(values),
                    'total': sum(values),
                    'months_active': len(values)
                }

        return baseline

    def analyze_2026_impact(self):
        """Analyze the impact of 2026 income changes"""

        new_sources, continuing = self.identify_new_income_sources()
        baseline = self.calculate_historical_baseline()

        # Calculate 2026 totals
        totals_2026 = {}
        for source, monthly_data in self.data_2026.items():
            total = sum(monthly_data.values())
            if total > 0:
                totals_2026[source] = {
                    'total': total,
                    'avg': total / len(monthly_data),
                    'months': list(monthly_data.keys()),
                    'values': list(monthly_data.values())
                }

        return {
            'new_sources': new_sources,
            'continuing_sources': continuing,
            'totals_2026': totals_2026,
            'baseline': baseline
        }

    def compare_cash_flow(self):
        """Compare 2026 cash flow with and without new income"""

        months_2026 = ['Feb 2026', 'Mar 2026', 'Apr 2026', 'May 2026']

        results = []

        for month in months_2026:
            # Total income in 2026
            total_income = sum(
                data[month] for data in self.data_2026.values()
            )

            # Income from new sources only
            new_sources, _ = self.identify_new_income_sources()
            new_income = sum(
                self.data_2026[source][month]
                for source in new_sources
                if source in self.data_2026
            )

            # Income without new sources
            base_income = total_income - new_income

            # Expenses
            expenses = self.expenses_2026.get(month, 0)

            # Cash flow scenarios
            actual_cash_flow = total_income - expenses
            baseline_cash_flow = base_income - expenses
            impact = actual_cash_flow - baseline_cash_flow

            results.append({
                'month': month,
                'total_income': total_income,
                'new_income': new_income,
                'base_income': base_income,
                'expenses': expenses,
                'actual_cash_flow': actual_cash_flow,
                'baseline_cash_flow': baseline_cash_flow,
                'impact': impact
            })

        return pd.DataFrame(results)

    def visualize_2026_income_impact(self, save_path='income_2026_analysis.png'):
        """Create visualizations showing 2026 income impact"""

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('2026 Income Impact Analysis', fontsize=16, fontweight='bold')

        # Get analysis data
        analysis = self.analyze_2026_impact()
        cash_flow_df = self.compare_cash_flow()

        # Plot 1: Income sources comparison
        ax1 = axes[0, 0]

        # Get all unique sources
        all_sources = set(analysis['baseline'].keys()) | set(analysis['totals_2026'].keys())

        source_names = []
        historical_vals = []
        current_vals = []

        for source in sorted(all_sources):
            if source in analysis['totals_2026'] and analysis['totals_2026'][source]['total'] > 100:
                source_names.append(source[:25])  # Truncate long names

                hist_val = analysis['baseline'].get(source, {}).get('avg', 0)
                curr_val = analysis['totals_2026'][source]['avg']

                historical_vals.append(hist_val)
                current_vals.append(curr_val)

        x = np.arange(len(source_names))
        width = 0.35

        ax1.barh(x - width/2, historical_vals, width, label='Historical Avg', alpha=0.7, color='blue')
        ax1.barh(x + width/2, current_vals, width, label='2026 Avg', alpha=0.7, color='green')

        ax1.set_xlabel('Average Monthly Income ($)')
        ax1.set_title('Income Sources: Historical vs 2026', fontweight='bold')
        ax1.set_yticks(x)
        ax1.set_yticklabels(source_names, fontsize=9)
        ax1.legend()
        ax1.grid(True, alpha=0.3, axis='x')

        # Plot 2: Cash flow impact by month
        ax2 = axes[0, 1]

        months_short = [m.split()[0] for m in cash_flow_df['month']]
        x2 = np.arange(len(months_short))
        width2 = 0.25

        ax2.bar(x2 - width2, cash_flow_df['baseline_cash_flow'], width2,
               label='Without New Income', alpha=0.7, color='red')
        ax2.bar(x2, cash_flow_df['actual_cash_flow'], width2,
               label='With New Income', alpha=0.7, color='green')
        ax2.bar(x2 + width2, cash_flow_df['impact'], width2,
               label='Impact', alpha=0.7, color='blue')

        ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
        ax2.set_xlabel('Month')
        ax2.set_ylabel('Cash Flow ($)')
        ax2.set_title('Cash Flow Impact of New Income Sources', fontweight='bold')
        ax2.set_xticks(x2)
        ax2.set_xticklabels(months_short)
        ax2.legend()
        ax2.grid(True, alpha=0.3, axis='y')

        # Plot 3: Income composition by month
        ax3 = axes[1, 0]

        new_sources_vals = cash_flow_df['new_income'].values
        base_income_vals = cash_flow_df['base_income'].values

        ax3.bar(months_short, base_income_vals, label='Base Income', alpha=0.7, color='blue')
        ax3.bar(months_short, new_sources_vals, bottom=base_income_vals,
               label='New Income Sources', alpha=0.7, color='green')

        ax3.set_xlabel('Month')
        ax3.set_ylabel('Income ($)')
        ax3.set_title('Income Composition: Base vs New Sources', fontweight='bold')
        ax3.legend()
        ax3.grid(True, alpha=0.3, axis='y')

        # Plot 4: Summary statistics
        ax4 = axes[1, 1]
        ax4.axis('off')

        # Calculate summary stats
        total_new_income = cash_flow_df['new_income'].sum()
        avg_new_income = cash_flow_df['new_income'].mean()
        total_impact = cash_flow_df['impact'].sum()
        avg_impact = cash_flow_df['impact'].mean()

        # Identify new sources
        new_sources_list = [s for s in analysis['new_sources']
                           if s in analysis['totals_2026']]

        summary_text = f"""
2026 INCOME IMPACT SUMMARY
{'='*45}

NEW INCOME SOURCES:
{chr(10).join(f"  • {source}" for source in new_sources_list)}

FINANCIAL IMPACT (Feb - May 2026):

Total New Income:        ${total_new_income:>12,.2f}
Average New Income/mo:   ${avg_new_income:>12,.2f}

Total Cash Flow Impact:  ${total_impact:>12,.2f}
Avg CF Impact/mo:        ${avg_impact:>12,.2f}

MONTHLY BREAKDOWN:
  Feb: ${cash_flow_df.iloc[0]['impact']:>10,.2f} impact
  Mar: ${cash_flow_df.iloc[1]['impact']:>10,.2f} impact
  Apr: ${cash_flow_df.iloc[2]['impact']:>10,.2f} impact
  May: ${cash_flow_df.iloc[3]['impact']:>10,.2f} impact

WITHOUT NEW INCOME:
  Avg cash flow: ${cash_flow_df['baseline_cash_flow'].mean():>10,.2f}

WITH NEW INCOME:
  Avg cash flow: ${cash_flow_df['actual_cash_flow'].mean():>10,.2f}
        """

        ax4.text(0.1, 0.9, summary_text, transform=ax4.transAxes,
                fontsize=10, verticalalignment='top', family='monospace',
                bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))

        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"\nVisualization saved to: {save_path}")

        return fig

    def print_report(self):
        """Print comprehensive 2026 income analysis report"""

        print("\n" + "="*100)
        print("2026 INCOME IMPACT ANALYSIS")
        print("="*100)

        analysis = self.analyze_2026_impact()
        cash_flow_df = self.compare_cash_flow()

        # Identify new vs continuing sources
        print("\n--- INCOME SOURCE CHANGES ---")
        print(f"\nNEW income sources in 2026:")
        for source in sorted(analysis['new_sources']):
            if source in analysis['totals_2026']:
                total = analysis['totals_2026'][source]['total']
                avg = analysis['totals_2026'][source]['avg']
                print(f"  • {source:<40} Total: ${total:>10,.2f}  Avg: ${avg:>10,.2f}/month")

        if not analysis['new_sources']:
            print("  (None - all income sources were present historically)")

        print(f"\nCONTINUING income sources:")
        for source in sorted(analysis['continuing_sources']):
            if source in analysis['totals_2026']:
                historical_avg = analysis['baseline'].get(source, {}).get('avg', 0)
                current_avg = analysis['totals_2026'][source]['avg']
                change = current_avg - historical_avg
                change_pct = (change / historical_avg * 100) if historical_avg > 0 else 0

                print(f"  • {source:<40} "
                      f"Historical: ${historical_avg:>10,.2f}  "
                      f"2026: ${current_avg:>10,.2f}  "
                      f"Change: {'+' if change > 0 else ''}{change_pct:>6.1f}%")

        # Cash flow impact analysis
        print("\n" + "="*100)
        print("MONTHLY CASH FLOW IMPACT")
        print("="*100)

        print(f"\n{'Month':<12} {'Total Income':>15} {'New Sources':>15} {'Base Income':>15} "
              f"{'Expenses':>15} {'Actual CF':>15} {'Base CF':>15} {'Impact':>15}")
        print("-"*100)

        for _, row in cash_flow_df.iterrows():
            month_short = row['month'].split()[0]
            print(f"{month_short:<12} "
                  f"${row['total_income']:>13,.2f} "
                  f"${row['new_income']:>13,.2f} "
                  f"${row['base_income']:>13,.2f} "
                  f"${row['expenses']:>13,.2f} "
                  f"${row['actual_cash_flow']:>13,.2f} "
                  f"${row['baseline_cash_flow']:>13,.2f} "
                  f"${row['impact']:>13,.2f}")

        # Summary statistics
        print("\n" + "="*100)
        print("SUMMARY (Feb - May 2026)")
        print("="*100)

        total_new = cash_flow_df['new_income'].sum()
        avg_new = cash_flow_df['new_income'].mean()
        total_impact = cash_flow_df['impact'].sum()
        avg_impact = cash_flow_df['impact'].mean()

        print(f"\nNew Income Sources:")
        print(f"  Total over 4 months:        ${total_new:>12,.2f}")
        print(f"  Average per month:          ${avg_new:>12,.2f}")

        print(f"\nCash Flow Impact:")
        print(f"  Total improvement:          ${total_impact:>12,.2f}")
        print(f"  Average monthly improvement:${avg_impact:>12,.2f}")

        baseline_cf = cash_flow_df['baseline_cash_flow'].mean()
        actual_cf = cash_flow_df['actual_cash_flow'].mean()

        print(f"\nAverage Monthly Cash Flow:")
        print(f"  WITHOUT new income:         ${baseline_cf:>12,.2f}")
        print(f"  WITH new income:            ${actual_cf:>12,.2f}")
        print(f"  Improvement:                ${actual_cf - baseline_cf:>12,.2f}")

        # Month-by-month insights
        print("\n" + "="*100)
        print("MONTH-BY-MONTH INSIGHTS")
        print("="*100)

        for _, row in cash_flow_df.iterrows():
            month = row['month']
            print(f"\n{month}:")
            print(f"  • Total income: ${row['total_income']:,.2f}")
            print(f"  • New income sources contributed: ${row['new_income']:,.2f} "
                  f"({row['new_income']/row['total_income']*100:.1f}% of total)")

            if row['actual_cash_flow'] > 0 and row['baseline_cash_flow'] < 0:
                print(f"  ✓ New income turned negative cash flow into positive!")
                print(f"    Without: ${row['baseline_cash_flow']:,.2f}")
                print(f"    With: ${row['actual_cash_flow']:,.2f}")
            elif row['actual_cash_flow'] > row['baseline_cash_flow']:
                improvement = row['actual_cash_flow'] - row['baseline_cash_flow']
                print(f"  ✓ New income improved cash flow by ${improvement:,.2f}")

        print("\n" + "="*100)

def main():
    """Main entry point"""
    print("="*100)
    print("2026 INCOME IMPACT ANALYZER")
    print("="*100)

    analyzer = Income2026Analyzer()

    # Load data
    print("\nLoading data...")
    if not analyzer.load_data():
        print("Error loading data")
        return

    # Print report
    analyzer.print_report()

    # Generate visualizations
    print("\nGenerating visualizations...")
    analyzer.visualize_2026_income_impact()

    print("\n" + "="*100)
    print("Analysis complete!")
    print("="*100)

if __name__ == "__main__":
    main()
