#!/usr/bin/env python3
"""
YNAB Seasonal Spending Analyzer
Analyzes spending patterns across months and years to identify seasonal trends
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime
import calendar

class SeasonalSpendingAnalyzer:
    def __init__(self, base_dir="."):
        """Initialize seasonal analyzer"""
        self.base_dir = Path(base_dir)
        self.all_data = []
        self.monthly_data = None

    def load_all_data(self):
        """Load all available YNAB income/expense CSV files"""
        income_files = list(self.base_dir.glob("*income-expense*.csv"))

        if not income_files:
            print("Error: No income/expense files found")
            return False

        print(f"Found {len(income_files)} income/expense file(s)")

        for file in sorted(income_files):
            print(f"  Loading: {file.name}")
            df = pd.read_csv(file)

            # Extract month columns (skip Category, Average, Total)
            month_cols = [col for col in df.columns
                         if col not in ['Category', 'Average', 'Total']]

            # Find income and expense rows
            income_row = df[df['Category'].str.contains('Total Income', na=False)]

            # For older files, expenses might be spread across categories
            # For newer files, might have "Total Expenses" or "Net Income"
            expense_row = df[df['Category'].str.contains('Total Expenses', na=False)]
            net_row = df[df['Category'].str.contains('Net Income', na=False)]

            for month in month_cols:
                try:
                    income = float(income_row[month].values[0]) if not income_row.empty else 0

                    # Try to get expenses
                    if not expense_row.empty:
                        expenses = abs(float(expense_row[month].values[0]))
                    elif not net_row.empty:
                        net = float(net_row[month].values[0])
                        expenses = income - net
                    else:
                        # Calculate from category groups
                        expense_categories = df[
                            ~df['Category'].str.contains('Income|Total', na=False) &
                            df['Category'].notna()
                        ]
                        expenses = abs(expense_categories[month].sum())

                    self.all_data.append({
                        'month': month,
                        'income': income,
                        'expenses': expenses,
                        'cash_flow': income - expenses,
                        'source_file': file.name
                    })
                except Exception as e:
                    print(f"    Warning: Could not parse {month}: {e}")
                    continue

        if not self.all_data:
            print("Error: No data could be loaded")
            return False

        self.monthly_data = pd.DataFrame(self.all_data)

        # Parse dates and add time components
        self.monthly_data['date'] = pd.to_datetime(
            self.monthly_data['month'],
            format='%b %Y',
            errors='coerce'
        )
        self.monthly_data = self.monthly_data.dropna(subset=['date'])
        self.monthly_data = self.monthly_data.sort_values('date')

        # Extract year, month number, month name
        self.monthly_data['year'] = self.monthly_data['date'].dt.year
        self.monthly_data['month_num'] = self.monthly_data['date'].dt.month
        self.monthly_data['month_name'] = self.monthly_data['date'].dt.strftime('%B')

        print(f"\nLoaded {len(self.monthly_data)} months of data")
        print(f"Date range: {self.monthly_data['date'].min().strftime('%b %Y')} to {self.monthly_data['date'].max().strftime('%b %Y')}")

        return True

    def analyze_seasonal_patterns(self):
        """Analyze spending patterns by month across years"""

        # Group by month number to find seasonal patterns
        by_month = self.monthly_data.groupby('month_num').agg({
            'expenses': ['mean', 'std', 'min', 'max', 'count'],
            'income': ['mean', 'std'],
            'cash_flow': ['mean', 'std']
        }).round(2)

        # Group by year and month to see year-over-year trends
        by_year_month = self.monthly_data.pivot_table(
            values=['expenses', 'income', 'cash_flow'],
            index='month_num',
            columns='year',
            aggfunc='mean'
        ).round(2)

        return by_month, by_year_month

    def identify_high_expense_months(self, threshold_percentile=75):
        """Identify which months typically have high expenses"""

        # Calculate percentile threshold
        threshold = self.monthly_data['expenses'].quantile(threshold_percentile / 100)

        high_expense_months = self.monthly_data[
            self.monthly_data['expenses'] > threshold
        ].copy()

        # Add percentage above average
        avg_expenses = self.monthly_data['expenses'].mean()
        high_expense_months['pct_above_avg'] = (
            (high_expense_months['expenses'] - avg_expenses) / avg_expenses * 100
        ).round(1)

        return high_expense_months.sort_values('expenses', ascending=False)

    def detect_anomalies(self, std_threshold=2):
        """Detect months with unusually high or low spending"""

        mean_expenses = self.monthly_data['expenses'].mean()
        std_expenses = self.monthly_data['expenses'].std()

        # Identify anomalies (more than 2 standard deviations from mean)
        self.monthly_data['z_score'] = (
            (self.monthly_data['expenses'] - mean_expenses) / std_expenses
        )

        anomalies = self.monthly_data[
            abs(self.monthly_data['z_score']) > std_threshold
        ].copy()

        anomalies['type'] = anomalies['z_score'].apply(
            lambda x: 'High' if x > 0 else 'Low'
        )

        return anomalies.sort_values('date')

    def predict_upcoming_months(self):
        """Predict expenses for upcoming months based on historical patterns"""

        # Get the last date in our data
        last_date = self.monthly_data['date'].max()

        # Calculate average by month
        monthly_avg = self.monthly_data.groupby('month_num').agg({
            'expenses': 'mean',
            'income': 'mean',
            'cash_flow': 'mean'
        }).round(2)

        # Generate predictions for next 6 months
        predictions = []
        for i in range(1, 7):
            next_date = last_date + pd.DateOffset(months=i)
            month_num = next_date.month

            if month_num in monthly_avg.index:
                pred_expenses = monthly_avg.loc[month_num, 'expenses']
                pred_income = monthly_avg.loc[month_num, 'income']
                pred_cash_flow = monthly_avg.loc[month_num, 'cash_flow']
            else:
                # Use overall average if no data for that month
                pred_expenses = self.monthly_data['expenses'].mean()
                pred_income = self.monthly_data['income'].mean()
                pred_cash_flow = self.monthly_data['cash_flow'].mean()

            predictions.append({
                'month': next_date.strftime('%b %Y'),
                'predicted_expenses': pred_expenses,
                'predicted_income': pred_income,
                'predicted_cash_flow': pred_cash_flow
            })

        return pd.DataFrame(predictions)

    def visualize_seasonal_patterns(self, save_path='seasonal_analysis.png'):
        """Create comprehensive seasonal pattern visualizations"""

        fig = plt.figure(figsize=(20, 12))
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

        # Plot 1: Expenses over time
        ax1 = fig.add_subplot(gs[0, :])
        ax1.plot(self.monthly_data['date'], self.monthly_data['expenses'],
                marker='o', linewidth=2, markersize=4, color='red', alpha=0.7)
        ax1.axhline(y=self.monthly_data['expenses'].mean(),
                   color='blue', linestyle='--', linewidth=2,
                   label=f"Average: ${self.monthly_data['expenses'].mean():,.0f}")
        ax1.fill_between(self.monthly_data['date'],
                         self.monthly_data['expenses'],
                         alpha=0.3, color='red')
        ax1.set_title('Monthly Expenses Over Time', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Expenses ($)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Plot 2: Average expenses by month (seasonal pattern)
        ax2 = fig.add_subplot(gs[1, 0])
        monthly_avg = self.monthly_data.groupby('month_num')['expenses'].mean()
        months = [calendar.month_abbr[i] for i in monthly_avg.index]
        colors = ['red' if x > self.monthly_data['expenses'].mean() else 'green'
                 for x in monthly_avg.values]
        ax2.bar(months, monthly_avg.values, color=colors, alpha=0.7)
        ax2.axhline(y=self.monthly_data['expenses'].mean(),
                   color='blue', linestyle='--', linewidth=2)
        ax2.set_title('Average Expenses by Month\n(Seasonal Pattern)',
                     fontsize=12, fontweight='bold')
        ax2.set_ylabel('Average Expenses ($)')
        ax2.tick_params(axis='x', rotation=45)
        ax2.grid(True, alpha=0.3, axis='y')

        # Plot 3: Year-over-year comparison (heatmap style)
        ax3 = fig.add_subplot(gs[1, 1:])
        pivot_data = self.monthly_data.pivot_table(
            values='expenses',
            index='month_num',
            columns='year',
            aggfunc='mean'
        )

        # Create grouped bar chart for year-over-year
        x = np.arange(len(pivot_data.index))
        width = 0.8 / len(pivot_data.columns)

        for i, year in enumerate(pivot_data.columns):
            offset = (i - len(pivot_data.columns)/2) * width + width/2
            ax3.bar(x + offset, pivot_data[year], width,
                   label=str(year), alpha=0.8)

        ax3.set_xlabel('Month')
        ax3.set_ylabel('Expenses ($)')
        ax3.set_title('Year-over-Year Comparison by Month',
                     fontsize=12, fontweight='bold')
        ax3.set_xticks(x)
        ax3.set_xticklabels([calendar.month_abbr[i] for i in pivot_data.index])
        ax3.legend()
        ax3.grid(True, alpha=0.3, axis='y')

        # Plot 4: Cash flow patterns
        ax4 = fig.add_subplot(gs[2, 0])
        monthly_cf = self.monthly_data.groupby('month_num')['cash_flow'].mean()
        colors_cf = ['green' if x > 0 else 'red' for x in monthly_cf.values]
        ax4.bar(months, monthly_cf.values, color=colors_cf, alpha=0.7)
        ax4.axhline(y=0, color='black', linestyle='-', linewidth=1)
        ax4.set_title('Average Cash Flow by Month', fontsize=12, fontweight='bold')
        ax4.set_ylabel('Cash Flow ($)')
        ax4.tick_params(axis='x', rotation=45)
        ax4.grid(True, alpha=0.3, axis='y')

        # Plot 5: Income vs Expenses trend
        ax5 = fig.add_subplot(gs[2, 1])
        yearly_data = self.monthly_data.groupby('year').agg({
            'income': 'sum',
            'expenses': 'sum'
        })
        x_years = np.arange(len(yearly_data.index))
        ax5.bar(x_years - 0.2, yearly_data['income'], 0.4,
               label='Income', color='green', alpha=0.7)
        ax5.bar(x_years + 0.2, yearly_data['expenses'], 0.4,
               label='Expenses', color='red', alpha=0.7)
        ax5.set_xlabel('Year')
        ax5.set_ylabel('Amount ($)')
        ax5.set_title('Annual Income vs Expenses', fontsize=12, fontweight='bold')
        ax5.set_xticks(x_years)
        ax5.set_xticklabels(yearly_data.index)
        ax5.legend()
        ax5.grid(True, alpha=0.3, axis='y')

        # Plot 6: Statistics summary
        ax6 = fig.add_subplot(gs[2, 2])
        ax6.axis('off')

        # Calculate statistics
        avg_expenses = self.monthly_data['expenses'].mean()
        std_expenses = self.monthly_data['expenses'].std()
        min_expenses = self.monthly_data['expenses'].min()
        max_expenses = self.monthly_data['expenses'].max()

        # Find most expensive months
        expensive_months = self.monthly_data.groupby('month_num')['expenses'].mean().sort_values(ascending=False)
        top_3_months = [calendar.month_name[i] for i in expensive_months.head(3).index]

        # Find cheapest months
        cheap_months = self.monthly_data.groupby('month_num')['expenses'].mean().sort_values()
        bottom_3_months = [calendar.month_name[i] for i in cheap_months.head(3).index]

        summary_text = f"""
SEASONAL PATTERNS SUMMARY
{'='*40}

Average Monthly Expense: ${avg_expenses:>12,.2f}
Standard Deviation:      ${std_expenses:>12,.2f}
Lowest Month:           ${min_expenses:>12,.2f}
Highest Month:          ${max_expenses:>12,.2f}

MOST EXPENSIVE MONTHS:
  1. {top_3_months[0]}
  2. {top_3_months[1]}
  3. {top_3_months[2]}

LEAST EXPENSIVE MONTHS:
  1. {bottom_3_months[0]}
  2. {bottom_3_months[1]}
  3. {bottom_3_months[2]}

Data spans {len(self.monthly_data)} months
From {self.monthly_data['date'].min().strftime('%b %Y')}
To {self.monthly_data['date'].max().strftime('%b %Y')}
        """

        ax6.text(0.1, 0.9, summary_text, transform=ax6.transAxes,
                fontsize=10, verticalalignment='top', family='monospace',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        plt.suptitle('YNAB Seasonal Spending Analysis',
                    fontsize=16, fontweight='bold', y=0.995)

        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"\nVisualization saved to: {save_path}")

        return fig

    def print_detailed_report(self):
        """Print comprehensive seasonal analysis report"""

        print("\n" + "="*100)
        print("SEASONAL SPENDING ANALYSIS REPORT")
        print("="*100)

        # Overall statistics
        print("\n--- OVERALL STATISTICS ---")
        print(f"  Data Period:           {self.monthly_data['date'].min().strftime('%B %Y')} to {self.monthly_data['date'].max().strftime('%B %Y')}")
        print(f"  Total Months:          {len(self.monthly_data)}")
        print(f"  Average Expenses:      ${self.monthly_data['expenses'].mean():>12,.2f}")
        print(f"  Average Income:        ${self.monthly_data['income'].mean():>12,.2f}")
        print(f"  Average Cash Flow:     ${self.monthly_data['cash_flow'].mean():>12,.2f}")
        print(f"  Expense Volatility:    ${self.monthly_data['expenses'].std():>12,.2f} (std dev)")

        # Monthly patterns
        print("\n--- SEASONAL PATTERNS BY MONTH ---")
        monthly_stats = self.monthly_data.groupby('month_num').agg({
            'expenses': ['mean', 'std', 'count']
        }).round(2)

        print(f"{'Month':<12} {'Avg Expenses':>15} {'Std Dev':>12} {'Samples':>10} {'vs Average':>15}")
        print("-" * 100)

        overall_avg = self.monthly_data['expenses'].mean()
        for month_num in sorted(monthly_stats.index):
            month_name = calendar.month_name[month_num]
            avg = monthly_stats.loc[month_num, ('expenses', 'mean')]
            std = monthly_stats.loc[month_num, ('expenses', 'std')]
            count = int(monthly_stats.loc[month_num, ('expenses', 'count')])
            diff_pct = ((avg - overall_avg) / overall_avg * 100)

            diff_str = f"{'+' if diff_pct > 0 else ''}{diff_pct:.1f}%"
            print(f"{month_name:<12} ${avg:>13,.2f} ${std:>10,.2f} {count:>10} {diff_str:>15}")

        # Year-over-year trends
        print("\n--- YEAR-OVER-YEAR TRENDS ---")
        yearly_stats = self.monthly_data.groupby('year').agg({
            'expenses': ['sum', 'mean'],
            'income': ['sum', 'mean'],
            'cash_flow': 'sum'
        }).round(2)

        print(f"{'Year':<8} {'Total Expenses':>18} {'Avg/Month':>15} {'Total Income':>18} {'Net Cash Flow':>18}")
        print("-" * 100)

        for year in yearly_stats.index:
            total_exp = yearly_stats.loc[year, ('expenses', 'sum')]
            avg_exp = yearly_stats.loc[year, ('expenses', 'mean')]
            total_inc = yearly_stats.loc[year, ('income', 'sum')]
            net_cf = yearly_stats.loc[year, ('cash_flow', 'sum')]

            print(f"{year:<8} ${total_exp:>16,.2f} ${avg_exp:>13,.2f} ${total_inc:>16,.2f} ${net_cf:>16,.2f}")

        # High expense months
        print("\n--- TOP 10 HIGHEST EXPENSE MONTHS ---")
        high_months = self.identify_high_expense_months(threshold_percentile=0)

        print(f"{'Date':<12} {'Expenses':>15} {'Income':>15} {'Cash Flow':>15} {'% Above Avg':>15}")
        print("-" * 100)

        for idx, row in high_months.head(10).iterrows():
            date_str = row['date'].strftime('%b %Y')
            print(f"{date_str:<12} ${row['expenses']:>13,.2f} ${row['income']:>13,.2f} ${row['cash_flow']:>13,.2f} {row['pct_above_avg']:>13.1f}%")

        # Anomalies
        print("\n--- SPENDING ANOMALIES (>2 Std Dev from Mean) ---")
        anomalies = self.detect_anomalies()

        if len(anomalies) > 0:
            print(f"{'Date':<12} {'Type':<8} {'Expenses':>15} {'Z-Score':>12} {'Note':>40}")
            print("-" * 100)

            for idx, row in anomalies.iterrows():
                date_str = row['date'].strftime('%b %Y')
                note = "Unusually high spending" if row['type'] == 'High' else "Unusually low spending"
                print(f"{date_str:<12} {row['type']:<8} ${row['expenses']:>13,.2f} {row['z_score']:>11.2f} {note:>40}")
        else:
            print("  No significant anomalies detected")

        # Predictions
        print("\n--- PREDICTED EXPENSES FOR UPCOMING MONTHS ---")
        predictions = self.predict_upcoming_months()

        print(f"{'Month':<12} {'Predicted Expenses':>20} {'Predicted Income':>20} {'Predicted Cash Flow':>20}")
        print("-" * 100)

        for idx, row in predictions.iterrows():
            print(f"{row['month']:<12} ${row['predicted_expenses']:>18,.2f} ${row['predicted_income']:>18,.2f} ${row['predicted_cash_flow']:>18,.2f}")

        # Key insights
        print("\n" + "="*100)
        print("KEY INSIGHTS & RECOMMENDATIONS")
        print("="*100)

        # Find most and least expensive months
        monthly_avg = self.monthly_data.groupby('month_num')['expenses'].mean().sort_values()
        cheapest_month = calendar.month_name[monthly_avg.index[0]]
        most_expensive_month = calendar.month_name[monthly_avg.index[-1]]

        print(f"\n1. SEASONAL SPENDING PATTERN")
        print(f"   - Most expensive month: {most_expensive_month} (${monthly_avg.iloc[-1]:,.2f} avg)")
        print(f"   - Least expensive month: {cheapest_month} (${monthly_avg.iloc[0]:,.2f} avg)")
        print(f"   - Difference: ${monthly_avg.iloc[-1] - monthly_avg.iloc[0]:,.2f} ({(monthly_avg.iloc[-1] / monthly_avg.iloc[0] - 1) * 100:.1f}% higher)")

        # Volatility
        print(f"\n2. SPENDING VOLATILITY")
        volatility_pct = (self.monthly_data['expenses'].std() / self.monthly_data['expenses'].mean()) * 100
        print(f"   - Coefficient of variation: {volatility_pct:.1f}%")
        if volatility_pct > 30:
            print(f"   - Your spending varies significantly month-to-month")
            print(f"   - Consider building a buffer for high-expense months")
        else:
            print(f"   - Your spending is relatively consistent")

        # Recent trends
        print(f"\n3. RECENT TRENDS (Last 6 Months)")
        recent_data = self.monthly_data.tail(6)
        recent_avg = recent_data['expenses'].mean()
        overall_avg = self.monthly_data['expenses'].mean()
        trend_pct = ((recent_avg - overall_avg) / overall_avg) * 100

        print(f"   - Recent 6-month average: ${recent_avg:,.2f}")
        print(f"   - Overall average: ${overall_avg:,.2f}")
        print(f"   - Trend: {'+' if trend_pct > 0 else ''}{trend_pct:.1f}%")
        if trend_pct > 10:
            print(f"   ⚠ Spending is trending upward - review categories for increases")
        elif trend_pct < -10:
            print(f"   ✓ Spending is trending downward - good progress!")

        print("\n" + "="*100)

def main():
    """Main entry point"""
    print("="*100)
    print("YNAB SEASONAL SPENDING ANALYZER")
    print("="*100)

    analyzer = SeasonalSpendingAnalyzer()

    # Load data
    if not analyzer.load_all_data():
        return

    # Print detailed report
    analyzer.print_detailed_report()

    # Create visualizations
    print("\nGenerating visualizations...")
    analyzer.visualize_seasonal_patterns()

    print("\n" + "="*100)
    print("Analysis complete!")
    print("="*100)

if __name__ == "__main__":
    main()
