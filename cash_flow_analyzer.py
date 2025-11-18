#!/usr/bin/env python3
"""
YNAB Cash Flow Analyzer & Income Impact Calculator
Analyzes historical cash flow and projects impact of additional income
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from pathlib import Path
import sys

class YNABCashFlowAnalyzer:
    def __init__(self, base_dir="."):
        """Initialize analyzer with YNAB data files"""
        self.base_dir = Path(base_dir)
        self.income_df = None
        self.networth_df = None
        self.months = []

    def load_data(self):
        """Load YNAB CSV files"""
        # Find the most recent files
        income_files = list(self.base_dir.glob("ynab-reflect-income-expense*.csv"))
        networth_files = list(self.base_dir.glob("ynab-reflect-net-worth*.csv"))

        if not income_files or not networth_files:
            print("Error: Could not find YNAB CSV files")
            print(f"Looking in: {self.base_dir.absolute()}")
            return False

        # Load income/expense data
        income_file = sorted(income_files)[-1]
        print(f"Loading income/expense data from: {income_file.name}")
        self.income_df = pd.read_csv(income_file)

        # Load net worth data
        networth_file = sorted(networth_files)[-1]
        print(f"Loading net worth data from: {networth_file.name}")
        self.networth_df = pd.read_csv(networth_file)

        # Extract month columns (skip first column which is Category/Account name)
        self.months = [col for col in self.income_df.columns if col not in ['Category', 'Average', 'Total']]

        print(f"Loaded data for {len(self.months)} months: {self.months[0]} to {self.months[-1]}")
        return True

    def calculate_cash_flow(self):
        """Calculate monthly cash flow (income - expenses)"""
        cash_flow_data = []

        # Find the "Total Income" row
        income_row = self.income_df[self.income_df['Category'] == 'Total Income']

        if income_row.empty:
            print("Error: Could not find 'Total Income' row")
            return None

        # Calculate total expenses for each month (sum of all expense categories)
        # Expense categories start after income categories
        expense_categories = [
            'Day to Day Variables',
            'Variable Expenses',
            'Fixed Monthly Expenses',
            'Fixed Infrequent Expenses',
            'Fun Money',
            'Subscriptions ⏱️',
            'Paying Off'
        ]

        for month in self.months:
            income = float(income_row[month].values[0])

            # Sum all expenses (they're negative in YNAB)
            expenses = 0
            for category in expense_categories:
                category_rows = self.income_df[self.income_df['Category'] == category]
                if not category_rows.empty:
                    exp_value = float(category_rows[month].values[0])
                    expenses += exp_value

            cash_flow = income + expenses  # expenses are negative, so we add them

            cash_flow_data.append({
                'Month': month,
                'Income': income,
                'Expenses': abs(expenses),
                'Cash Flow': cash_flow
            })

        return pd.DataFrame(cash_flow_data)

    def get_net_worth_data(self):
        """Extract net worth data over time"""
        networth_row = self.networth_df[self.networth_df['Account'] == 'Net Worth']

        if networth_row.empty:
            return None

        networth_data = []
        for month in self.months:
            value = float(networth_row[month].values[0])
            networth_data.append({
                'Month': month,
                'Net Worth': value
            })

        return pd.DataFrame(networth_data)

    def calculate_impact_scenarios(self, cash_flow_df, additional_monthly_income):
        """Calculate impact of additional income on financial picture"""
        avg_monthly_income = cash_flow_df['Income'].mean()
        avg_monthly_expenses = cash_flow_df['Expenses'].mean()
        avg_cash_flow = cash_flow_df['Cash Flow'].mean()

        # New scenario with additional income
        new_monthly_income = avg_monthly_income + additional_monthly_income
        new_cash_flow = avg_cash_flow + additional_monthly_income

        # Calculate debt payoff acceleration
        # Get current debt balances
        mortgage_row = self.networth_df[self.networth_df['Account'] == 'Longwood Mortgage']
        remodel_row = self.networth_df[self.networth_df['Account'] == 'Mom+Jane Remodel Loan']

        mortgage_balance = abs(float(mortgage_row[self.months[-1]].values[0])) if not mortgage_row.empty else 0
        remodel_balance = abs(float(remodel_row[self.months[-1]].values[0])) if not remodel_row.empty else 0

        total_debt = mortgage_balance + remodel_balance

        # Calculate payoff timeline (simplified - assumes all extra cash flow goes to debt)
        months_current = total_debt / avg_cash_flow if avg_cash_flow > 0 else float('inf')
        months_new = total_debt / new_cash_flow if new_cash_flow > 0 else float('inf')
        months_saved = months_current - months_new

        # Calculate net worth projection
        current_networth = float(self.networth_df[self.networth_df['Account'] == 'Net Worth'][self.months[-1]].values[0])
        networth_1yr_current = current_networth + (avg_cash_flow * 12)
        networth_1yr_new = current_networth + (new_cash_flow * 12)
        networth_5yr_current = current_networth + (avg_cash_flow * 60)
        networth_5yr_new = current_networth + (new_cash_flow * 60)

        return {
            'current': {
                'monthly_income': avg_monthly_income,
                'monthly_expenses': avg_monthly_expenses,
                'monthly_cash_flow': avg_cash_flow,
                'mortgage_balance': mortgage_balance,
                'remodel_balance': remodel_balance,
                'total_debt': total_debt,
                'debt_payoff_months': months_current,
                'current_networth': current_networth,
                'networth_1yr': networth_1yr_current,
                'networth_5yr': networth_5yr_current
            },
            'new': {
                'monthly_income': new_monthly_income,
                'monthly_expenses': avg_monthly_expenses,
                'monthly_cash_flow': new_cash_flow,
                'debt_payoff_months': months_new,
                'months_saved': months_saved,
                'networth_1yr': networth_1yr_new,
                'networth_5yr': networth_5yr_new,
                'networth_gain_1yr': networth_1yr_new - networth_1yr_current,
                'networth_gain_5yr': networth_5yr_new - networth_5yr_current
            }
        }

    def visualize_cash_flow(self, cash_flow_df, save_path='cash_flow_analysis.png'):
        """Create visualizations of cash flow data"""
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('YNAB Cash Flow Analysis', fontsize=16, fontweight='bold')

        # Prepare data for plotting
        month_indices = range(len(cash_flow_df))
        months_display = [m[:7] if len(m) > 7 else m for m in cash_flow_df['Month']]  # Shorten month labels

        # Plot 1: Income vs Expenses over time
        ax1 = axes[0, 0]
        ax1.plot(month_indices, cash_flow_df['Income'], label='Income', color='green', linewidth=2)
        ax1.plot(month_indices, cash_flow_df['Expenses'], label='Expenses', color='red', linewidth=2)
        ax1.fill_between(month_indices, cash_flow_df['Income'], alpha=0.3, color='green')
        ax1.fill_between(month_indices, cash_flow_df['Expenses'], alpha=0.3, color='red')
        ax1.set_title('Monthly Income vs Expenses', fontsize=12, fontweight='bold')
        ax1.set_xlabel('Month')
        ax1.set_ylabel('Amount ($)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.tick_params(axis='x', rotation=45)
        # Set x-ticks to show every 6 months
        tick_indices = range(0, len(months_display), 6)
        ax1.set_xticks(tick_indices)
        ax1.set_xticklabels([months_display[i] for i in tick_indices], rotation=45, ha='right')

        # Plot 2: Cash Flow over time
        ax2 = axes[0, 1]
        colors = ['green' if x > 0 else 'red' for x in cash_flow_df['Cash Flow']]
        ax2.bar(month_indices, cash_flow_df['Cash Flow'], color=colors, alpha=0.6)
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
        ax2.axhline(y=cash_flow_df['Cash Flow'].mean(), color='blue', linestyle='--',
                   label=f"Avg: ${cash_flow_df['Cash Flow'].mean():,.0f}", linewidth=2)
        ax2.set_title('Monthly Cash Flow (Income - Expenses)', fontsize=12, fontweight='bold')
        ax2.set_xlabel('Month')
        ax2.set_ylabel('Cash Flow ($)')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.set_xticks(tick_indices)
        ax2.set_xticklabels([months_display[i] for i in tick_indices], rotation=45, ha='right')

        # Plot 3: Net Worth over time
        ax3 = axes[1, 0]
        networth_df = self.get_net_worth_data()
        if networth_df is not None:
            ax3.plot(month_indices, networth_df['Net Worth'], color='purple', linewidth=2.5, marker='o', markersize=3)
            ax3.fill_between(month_indices, networth_df['Net Worth'], alpha=0.3, color='purple')
            ax3.set_title('Net Worth Growth', fontsize=12, fontweight='bold')
            ax3.set_xlabel('Month')
            ax3.set_ylabel('Net Worth ($)')
            ax3.grid(True, alpha=0.3)
            ax3.set_xticks(tick_indices)
            ax3.set_xticklabels([months_display[i] for i in tick_indices], rotation=45, ha='right')

            # Add trend line
            z = np.polyfit(month_indices, networth_df['Net Worth'], 1)
            p = np.poly1d(z)
            ax3.plot(month_indices, p(month_indices), "r--", alpha=0.8, linewidth=2,
                    label=f"Trend: ${z[0]*12:,.0f}/year")
            ax3.legend()

        # Plot 4: Summary Statistics
        ax4 = axes[1, 1]
        ax4.axis('off')

        avg_income = cash_flow_df['Income'].mean()
        avg_expenses = cash_flow_df['Expenses'].mean()
        avg_cash_flow = cash_flow_df['Cash Flow'].mean()

        summary_text = f"""
        SUMMARY STATISTICS
        {'='*50}

        Average Monthly Income:    ${avg_income:>15,.2f}
        Average Monthly Expenses:  ${avg_expenses:>15,.2f}
        Average Monthly Cash Flow: ${avg_cash_flow:>15,.2f}

        Savings Rate:              {(avg_cash_flow/avg_income*100):>15.1f}%

        Total Period Analyzed:     {len(cash_flow_df):>15} months
        Total Income:              ${cash_flow_df['Income'].sum():>15,.2f}
        Total Expenses:            ${cash_flow_df['Expenses'].sum():>15,.2f}
        Total Cash Flow:           ${cash_flow_df['Cash Flow'].sum():>15,.2f}

        Best Month (Cash Flow):    ${cash_flow_df['Cash Flow'].max():>15,.2f}
        Worst Month (Cash Flow):   ${cash_flow_df['Cash Flow'].min():>15,.2f}
        """

        ax4.text(0.1, 0.9, summary_text, transform=ax4.transAxes,
                fontsize=10, verticalalignment='top', family='monospace',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"\nVisualization saved to: {save_path}")

        return fig

    def print_scenario_report(self, scenarios):
        """Print detailed scenario comparison report"""
        current = scenarios['current']
        new = scenarios['new']

        print("\n" + "="*80)
        print("CASH FLOW & INCOME IMPACT ANALYSIS")
        print("="*80)

        print("\n--- CURRENT SCENARIO ---")
        print(f"  Average Monthly Income:      ${current['monthly_income']:>12,.2f}")
        print(f"  Average Monthly Expenses:    ${current['monthly_expenses']:>12,.2f}")
        print(f"  Average Monthly Cash Flow:   ${current['monthly_cash_flow']:>12,.2f}")
        print(f"  Savings Rate:                {(current['monthly_cash_flow']/current['monthly_income']*100):>11,.1f}%")

        print("\n--- DEBT SNAPSHOT ---")
        print(f"  Mortgage Balance:            ${current['mortgage_balance']:>12,.2f}")
        print(f"  Remodel Loan Balance:        ${current['remodel_balance']:>12,.2f}")
        print(f"  Total Debt:                  ${current['total_debt']:>12,.2f}")

        print("\n--- NET WORTH PROJECTION (Current Scenario) ---")
        print(f"  Current Net Worth:           ${current['current_networth']:>12,.2f}")
        print(f"  Projected (1 year):          ${current['networth_1yr']:>12,.2f}")
        print(f"  Projected (5 years):         ${current['networth_5yr']:>12,.2f}")

        additional_income = new['monthly_income'] - current['monthly_income']

        print("\n" + "="*80)
        print(f"--- NEW SCENARIO: +${additional_income:,.2f}/month (${additional_income*12:,.2f}/year) ---")
        print("="*80)

        print(f"\n  New Monthly Income:          ${new['monthly_income']:>12,.2f}  (+${additional_income:>12,.2f})")
        print(f"  Monthly Expenses:            ${new['monthly_expenses']:>12,.2f}  (unchanged)")
        print(f"  New Monthly Cash Flow:       ${new['monthly_cash_flow']:>12,.2f}  (+${new['monthly_cash_flow']-current['monthly_cash_flow']:>12,.2f})")
        print(f"  New Savings Rate:            {(new['monthly_cash_flow']/new['monthly_income']*100):>11,.1f}%  (+{(new['monthly_cash_flow']/new['monthly_income']*100)-(current['monthly_cash_flow']/current['monthly_income']*100):.1f}%)")

        print("\n--- IMPACT ON DEBT ---")
        if current['debt_payoff_months'] < float('inf'):
            print(f"  Debt Payoff Timeline:        {new['debt_payoff_months']:>11,.1f} months  (saves {new['months_saved']:.1f} months)")
            print(f"  Payoff Acceleration:         {(new['months_saved']/current['debt_payoff_months']*100):>11,.1f}% faster")
        else:
            print("  Note: Current cash flow insufficient to project debt payoff")

        print("\n--- NET WORTH PROJECTION (New Scenario) ---")
        print(f"  Projected (1 year):          ${new['networth_1yr']:>12,.2f}  (+${new['networth_gain_1yr']:>12,.2f})")
        print(f"  Projected (5 years):         ${new['networth_5yr']:>12,.2f}  (+${new['networth_gain_5yr']:>12,.2f})")

        print("\n--- LONG-TERM IMPACT ---")
        print(f"  Additional wealth (1 year):  ${new['networth_gain_1yr']:>12,.2f}")
        print(f"  Additional wealth (5 years): ${new['networth_gain_5yr']:>12,.2f}")
        print(f"  Additional wealth (10 years):${additional_income*12*10:>12,.2f}")

        print("\n" + "="*80)

def main():
    """Main entry point"""
    print("="*80)
    print("YNAB CASH FLOW ANALYZER & INCOME IMPACT CALCULATOR")
    print("="*80)

    # Initialize analyzer
    analyzer = YNABCashFlowAnalyzer()

    # Load data
    if not analyzer.load_data():
        return

    # Calculate cash flow
    print("\nCalculating cash flow...")
    cash_flow_df = analyzer.calculate_cash_flow()

    if cash_flow_df is None:
        print("Error calculating cash flow")
        return

    print(f"Successfully calculated cash flow for {len(cash_flow_df)} months")

    # Generate visualizations
    print("\nGenerating visualizations...")
    analyzer.visualize_cash_flow(cash_flow_df)

    # Interactive income scenario calculator
    print("\n" + "="*80)
    print("INCOME IMPACT CALCULATOR")
    print("="*80)

    while True:
        try:
            print("\nEnter additional monthly income to analyze (or 'q' to quit):")
            print("Examples: 500, 1000, 2500, etc.")
            user_input = input("\nAdditional monthly income $: ").strip()

            if user_input.lower() in ['q', 'quit', 'exit']:
                break

            additional_income = float(user_input)

            # Calculate scenarios
            scenarios = analyzer.calculate_impact_scenarios(cash_flow_df, additional_income)

            # Print report
            analyzer.print_scenario_report(scenarios)

            # Ask if user wants to try another scenario
            print("\n" + "-"*80)

        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break

    print("\n" + "="*80)
    print("Analysis complete!")
    print("="*80)

if __name__ == "__main__":
    main()
