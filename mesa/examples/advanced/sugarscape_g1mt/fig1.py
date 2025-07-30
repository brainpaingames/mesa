import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path

# --- Configuration ---
DB_PATH = Path("sugarscape_g1mt/simulation_results.db")
TARGET_RUN_ID = 50
ROLLING_WINDOW = 1  # The window size for the moving average (e.g., 50 steps)
OUTPUT_FILENAME = "figure_1.png"

# --- Plot Styling ---
plt.style.use('seaborn-v0_8-whitegrid')
FIG_WIDTH = 10
FIG_HEIGHT = 6
DPI = 300

# --- Data Loading Function (CORRECTED based on your schema) ---
def get_model_data_for_run(db_path, run_id):
    """
    Fetches and pivots model-level reporter data for a single run_id
    from the database, respecting the actual schema.
    """
    print(f"Connecting to database at: {db_path}")
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found at the specified path: {db_path}")

    with sqlite3.connect(db_path) as con:
        # Query the data in its normalized (long) format
        query = f"""
        SELECT
            step,
            reporter_name,
            reporter_value
        FROM model_results
        WHERE run_id = {run_id}
        AND reporter_name IN ('Avg Deposit Rate (Per-Step)', 'Avg Loan Rate (Per-Step)')
        """
        try:
            long_df = pd.read_sql_query(query, con)
            if long_df.empty:
                print(f"No data found for the specified reporters for run_id {run_id}.")
                return pd.DataFrame()

            # Pivot the table to create a "wide" DataFrame suitable for time-series analysis
            # with 'step' as the index and columns for each reporter.
            wide_df = long_df.pivot(index='step', columns='reporter_name', values='reporter_value')
            
            # Rename columns for easier access
            wide_df.rename(columns={
                'Avg Deposit Rate (Per-Step)': 'deposit_rate',
                'Avg Loan Rate (Per-Step)': 'loan_rate'
            }, inplace=True)
            
            print(f"Successfully loaded and pivoted {len(wide_df)} steps for run_id {run_id}.")
            return wide_df.reset_index() # Use reset_index to turn 'step' back into a column

        except Exception as e:
            print(f"An error occurred while querying or pivoting the database: {e}")
            return pd.DataFrame()

# --- Main Script ---
def create_publication_plot():
    """
    Generates and saves the publication-quality plot for the emergent interest rate spread.
    """
    # 1. Load the data using the corrected function
    data = get_model_data_for_run(DB_PATH, TARGET_RUN_ID)
    if data.empty:
        print("Exiting.")
        return

    # 2. Process the data
    # Calculate the smoothed moving average for both rates
    data['loan_rate_smoothed'] = data['loan_rate'].rolling(window=ROLLING_WINDOW, min_periods=1).mean()
    data['deposit_rate_smoothed'] = data['deposit_rate'].rolling(window=ROLLING_WINDOW, min_periods=1).mean()
    
    # 3. Create the plot
    fig, ax = plt.subplots(figsize=(FIG_WIDTH, FIG_HEIGHT))

    # Plot the smoothed lines
    ax.plot(data['step'], data['loan_rate_smoothed'], label='Loan Rate (Smoothed)', color='#1f77b4', linewidth=2)
    ax.plot(data['step'], data['deposit_rate_smoothed'], label='Deposit Rate (Smoothed)', color='#ff7f0e', linewidth=2)

    # Add the shaded area for the spread
    ax.fill_between(
        data['step'],
        data['loan_rate_smoothed'],
        data['deposit_rate_smoothed'],
        where=(data['loan_rate_smoothed'] >= data['deposit_rate_smoothed']),
        color='gray',
        alpha=0.2,
        interpolate=True,
        label='Interest Rate Spread'
    )

    # 4. Format the plot for publication quality
    ax.set_title('Figure 1: Emergent Interest Rate Spread in the Simulated Economy', fontsize=14, weight='bold')
    ax.set_xlabel('Model Step', fontsize=12)
    ax.set_ylabel('Average Interest Rate', fontsize=12)
    
    ax.set_xlim(0, data['step'].max())
    ax.set_ylim(0)

    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.2f'))
    ax.legend(loc='upper right', frameon=True, fontsize=10)
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)

    # 5. Save the figure
    plt.savefig(OUTPUT_FILENAME, dpi=DPI, bbox_inches='tight')
    
    print(f"\nPlot successfully saved as '{OUTPUT_FILENAME}'")
    
if __name__ == '__main__':
    create_publication_plot()