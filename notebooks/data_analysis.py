import os
import pandas as pd
import pandera as pa
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from prophet import Prophet
import logging
from pandera.typing import Series
from sklearn.metrics import mean_squared_error, mean_absolute_error

# set up logging
# TODO: include logging below
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# constants
DATA_PATH_LOCAL: str = "/Users/Vanilleeis/aixponic/aixponic/data_extracts"
LAST_EXTRACT_DATE: str = "2025_03_14"

TARGETS_4_CASES: dict = {
    "pump_degeneration": {"UNKNOWN": "5.12"},  # TODO: Where is this parameter located?
    "noise_induced_flushing": {
        "DO_Trommelfilter_Spülpumpe_QA4 ": "2.23",
        "spüldauer_trommelfilter": "3.35",
        "pause_der_spülung_trommelfilter": "3.36",
        "MW-Differenz_Sumpf_Becken": "1.4",
        "MW-LVL-Sumpf": "1.9",
        "MW-LVL-Becken": "1.1",
        "trigger_spülung": "3.37",
    },
    "tls_main_circuit_pump": {
        "trockenlaufschutz_sumpf": "3.31",
        "trockenlaufschutz_becken": "3.32",
    },
}
TARGET_COLS: list = [
    "DO_Trommelfilter_Spülpumpe_QA4",  # 2.23
    "MW-Differenz_Sumpf_Becken",  # 1.4
    "MW-LVL-Sumpf",  # 1.9
    "MW-LVL-Becken",  # 1.1
]

# flush pause
FLUSH_PAUSE_INTERVAL: dict = {"max_value": 400, "min_value": 20}

# flush duration
FLUSH_DURATION_INTERVAL: dict = {
    "max_value": 12,
    "min_value": 3,
}  # doc says 4 to 20 sec?
SETPOINT_3_35: int = 20

# flush trigger
SETPOINT_3_37: int = 20

# water levels
SETPOINT_3_31: int = 1015
SETPOINT_3_32: int = 1087

# rename mapping
MAPPING_COLUMNS = {
    "MW-Differenz_Sumpf_Becken": "MW_Differenz_Sumpf_Becken",
    "MW-LVL-Sumpf": "MW_LVL_Sumpf",
    "MW-LVL-Becken": "MW_LVL_Becken",
}

SAVE_PATH: str = "/Users/Vanilleeis/aixponic/aixponic/notebooks/figures"


# data schema
class target_schema(pa.DataFrameModel):
    DO_Trommelfilter_Spülpumpe_QA4: Series[float] = pa.Field(
        isin=[0, 1], nullable=False
    )
    # MW_Differenz_Sumpf_Becken: Series[float] = pa.Field(in_range=[], nullable=False)
    MW_LVL_Sumpf: Series[float] = pa.Field(
        in_range={"min_value": 1000, "max_value": 1500}, nullable=False
    )
    MW_LVL_Becken: Series[float] = pa.Field(
        in_range={"min_value": 1000, "max_value": 1500}, nullable=False
    )


# functions:
def slice_df(dataframe: pd.DataFrame, cols: list) -> pd.DataFrame:
    """
    Truncate the specified dataframe in a way that the time series starts with non missing
    values.

    Args:
        dataframe (pd.DataFrame): A pandas dataframe with timestamp index. Index must be in ascending order.
        cols (list): A list with column names that serves as a reference for truncation.

    Returns:
        Truncated dataframe with all columns originally supplied.
    """

    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError(
            f"dataframe must be of class pandas dataframe, got {type(dataframe)}"
        )
    if not isinstance(cols, list):
        raise TypeError(f"cols must be of class list, got {type(dataframe)}")
    if len(cols) == 0:
        raise Exception("cols cannot be empty.")
    if dataframe.empty:
        raise Exception("dataframe cannot be empty.")

    # check if col names are in dataframe
    valid_names_indicators = [col in dataframe.columns for col in cols]
    if not all(valid_names_indicators):
        raise Exception("At least one column is not in dataframe")

    # find first non-missing values in data
    mask = dataframe[cols].notna().reset_index(drop=True)

    # find index of first non-missing values
    idx = mask.any(axis=1).idxmax()

    return dataframe.iloc[idx:]


def fill_missing_data(dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    Wrapper for pandas forefill method.

    Args:
        dataframe (pd.DataFrame): A pandas dataframe whose missing values are to be forward filled
        with the latest observed value.

    Returns:
        Pandas dataframe with forward filled valued for all columns. Note That there
        can still be missing values at the beginning of the time series data since all
        values before the first non-missing values remains untouched.
    """
    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError(
            f"dataframe must be of class pandas dataframe, got {type(dataframe)}"
        )

    return dataframe.ffill(axis=0)


def plot_timeseries_with_nans(df: pd.DataFrame, save_path: str, dpi: int = 100) -> None:
    """
    Creates a plot for each column in the DataFrame, highlights NaN values,
    and saves the plots to the specified path.

    Args:
        df (pd.DatFrame): Dataframe with datetime index and time series data.
        save_path (str): Path to the directory where plots will be saved.
        dpi (int): Dots per inch for saved figures (default 100).
    """
    # Ensure the index is datetime
    if not pd.api.types.is_datetime64_any_dtype(df.index):
        raise ValueError("DataFrame index must be datetime type.")

    # Create the save directory if it doesn't exist
    os.makedirs(save_path, exist_ok=True)

    for column in df.columns:
        plt.figure(figsize=(16, 6))  # Widescreen aspect ratio
        # plt.plot(df.index, df[column], label=column, color="blue")

        series = df[column]

        # Normal values (non-NaN)
        valid_mask = series.notna()
        plt.scatter(
            df.index[valid_mask],
            series[valid_mask],
            color="blue",
            label="Value",
            s=10,
            zorder=1,
        )

        # NaN values (red circles at y=0)
        nan_mask = series.isna()
        plt.scatter(
            df.index[nan_mask],
            [0] * nan_mask.sum(),
            color="red",
            label="NaN",
            s=20,
            zorder=3,
        )

        # Negative values (orange X marks)
        neg_mask = (series < 0) & series.notna()
        plt.scatter(
            df.index[neg_mask],
            series[neg_mask],
            color="orange",
            label="Negative",
            s=30,
            marker="x",
            zorder=2,
        )

        plt.title(f"Time Series Plot - {column}")
        plt.xlabel("Time")
        plt.ylabel("Value")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()

        filename = f"{column}_timeseries_plot.png"
        filepath = os.path.join(save_path, filename)
        plt.savefig(filepath, dpi=dpi)
        plt.close()


def drop_columns_with_missing(df: pd.DataFrame, threshold: float = 0.2) -> pd.DataFrame:
    """
    Remove columns from dataframe where more than a certain proportion
    of values are NaN or None.

    Args:
        df (pd.DataFrame): Input dataframe.
        threshold (float): Maximum allowed fraction of missing values (default 0.2).

    Returns:
        pd.DataFrame: Cleaned dataframe.
    """

    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be of type pd.DataFrame.")

    if not isinstance(threshold, float):
        raise TypeError("threshold must be of type float.")

    missing_fraction = df.isnull().mean()

    return df.loc[:, missing_fraction <= threshold]


def clean_dataframe(
    df: pd.DataFrame, value_ranges: dict[str, list[float]]
) -> pd.DataFrame:
    """
    Cleans a dataframe by clipping values in columns based on provided min/max ranges and nterpolating NaN values linearly.

    Args:
        df (pd.DataFrame): Input DataFrame.
        value_ranges (dict[str, list[float]]): Dict with column name as key and [min, max] as value.

    Returns:
        pd.DataFrame: Cleaned DataFrame.
    """

    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be of type pd.DataFrame.")

    if not isinstance(value_ranges, dict):
        raise TypeError("value_ranges must be of type dict.")

    df_cleaned = df.copy()

    for col, limits in value_ranges.items():
        if col in df_cleaned.columns and len(limits) == 2:
            min_val, max_val = limits
            df_cleaned[col] = df_cleaned[col].clip(lower=min_val, upper=max_val)

    df_cleaned = df_cleaned.interpolate(method="linear", limit_direction="both")

    return df_cleaned


def clip_binary_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """
    For specified columns, replace all values strictly between 0 and 1 with 1.

    Parameters:
        df (pd.DataFrame): Input DataFrame.
        columns (list[str]): List of columns to transform.

    Returns:
        pd.DataFrame: Updated DataFrame.
    """
    df_cleaned = df.copy()
    for col in columns:
        if col in df_cleaned.columns:
            df_cleaned[col] = np.where(
                (df_cleaned[col] > 0) & (df_cleaned[col] < 1),  # strictly between
                1,
                df_cleaned[col],
            )
    return df_cleaned


def drop_highly_imbalanced(df: pd.DataFrame, threshold: float = 0.99) -> pd.DataFrame:
    """
    Drop columns where a single value dominates more than a predefined fraction.

    Args:
        df (pd.Dataframe): Dataframe to be cleaned.
        threshold (float): Fraction of values to drop the column because of low variance.

    Returns:
        pd.DataFrame: Cleaned DataFrame.

    """

    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be of type pd.DataFrame.")

    if not isinstance(threshold, float):
        raise TypeError("threshold must be of type float.")

    to_drop = []
    for col in df.columns:
        top_freq = df[col].value_counts(normalize=True, dropna=False).values[0]
        if top_freq >= threshold:
            to_drop.append(col)

    return df.drop(columns=to_drop)


def scale_dataframe_by_ranges(
    df: pd.DataFrame, value_ranges: dict[str, list[float]]
) -> pd.DataFrame:
    """
    Scale dataframe columns to [0, 1] based on provided value ranges.
    Excludes columns without value ranges.

    Args:
        df (pd.DataFrame): Input time series dataframe.
        value_ranges (dict[str, list[float]]): Dict with column name as key and [min, max] as value.

    Returns:
        pd.DataFrame: Scaled dataframe with only columns that have ranges.
    """

    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be of type pd.DataFrame.")

    if not isinstance(value_ranges, dict):
        raise TypeError("value_ranges must be of type dict.")

    scaled_df = pd.DataFrame(index=df.index)

    for col, limits in value_ranges.items():
        if col in df.columns and len(limits) == 2:
            min_val, max_val = limits
            if max_val > min_val:
                scaled_df[col] = (df[col] - min_val) / (max_val - min_val)

    return scaled_df


def create_lagged_features(
    df: pd.DataFrame, lags: int = 3, sort_columns: bool = True
) -> pd.DataFrame:
    """
    Create lagged features for all columns in a time-series dataframe.

    Args:
        df (pd.DataFrame): Input dataframe with datetime index.
        lags (int): Number of lags to generate (default=3).
        sort_columns (bool): Whether to sort the columns alphabetically after adding lags.

    Returns:
        pd.DataFrame: Dataframe with original and lagged features.
    """

    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be of type pd.DataFrame.")

    if not isinstance(lags, int):
        raise TypeError("lags must be of type int.")

    df_lagged = df.copy()
    for lag in range(1, lags + 1):
        shifted = df.shift(lag)
        shifted.columns = [f"{col}_t-{lag}" for col in df.columns]
        df_lagged = pd.concat([df_lagged, shifted], axis=1)

    if sort_columns:
        df_lagged = df_lagged.reindex(sorted(df_lagged.columns), axis=1)

    return df_lagged.iloc[lags:]


def plot_corr_heatmap(df, figsize=(12, 10)):
    corr = df.corr()
    plt.figure(figsize=figsize)
    sns.heatmap(corr, annot=False, cmap="coolwarm", center=0)
    plt.title("Correlation Heatmap")
    plt.show()


def plot_predictions(
    test_df: pd.DataFrame,
    forecast: pd.DataFrame,
    target_col: str = "y",
    figsize: tuple = (12, 6),
):
    """
    Plot actual vs predicted values for the test set.

    Args:
        test_df (pd.DataFrame): Test set containing the true target values.
        forecast (pd.DataFrame): Forecast dataframe from Prophet (contains 'yhat').
        target_col (str): Column name of the target variable in test_df (default='y').
        figsize (tuple): Size of the figure.
    """

    plt.figure(figsize=figsize)

    plt.plot(
        test_df["ds"],
        test_df[target_col],
        label="Actual",
        color="blue",
        marker="o",
        linestyle="-",
    )

    plt.plot(
        forecast["ds"],
        forecast["yhat"],
        label="Predicted",
        color="red",
        marker="x",
        linestyle="--",
    )

    plt.xlabel("Datetime")
    plt.ylabel(target_col)
    plt.title(f"{target_col} - Actual vs Predicted")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def plot_actual_vs_predicted_original(
    test_df: pd.DataFrame,
    forecast: pd.DataFrame,
    value_ranges: dict,
    target_col: str = "y",
    prd_col: str = "yhat",
    figsize=(12, 6),
):
    """
    Plot actual vs predicted values of a target variable in original units.

    Parameters:
        test_df (pd.DataFrame): Test set containing scaled target values ('y') and 'ds'.
        forecast (pd.DataFrame): Forecast dataframe from Prophet (contains 'yhat' and 'ds').
        target_col (str): Target variable name (key in value_ranges dictionary).
        value_ranges (dict): Dictionary of min/max values used for scaling.
        figsize (tuple): Size of the figure.
    """
    # Get original min and max values for target
    min_val, max_val = value_ranges[target_col]

    # Inverse min-max scaling
    y_true_original = test_df["y"] * (max_val - min_val) + min_val
    y_pred_original = forecast[prd_col] * (max_val - min_val) + min_val

    # Plot
    plt.figure(figsize=figsize)
    plt.plot(
        test_df["ds"],
        y_true_original,
        label="Actual",
        color="blue",
        marker="o",
        linestyle="-",
    )
    plt.plot(
        forecast["ds"],
        y_pred_original,
        label="Predicted",
        color="red",
        marker="x",
        linestyle="--",
    )

    plt.xlabel("Datetime")
    plt.ylabel(target_col)
    plt.title(f"{target_col} - Actual vs Predicted (Original Units)")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    ########################################################################
    # data processing after data was extracted via API
    ########################################################################
    # read data
    # NOTE: data is not equi-distant, e.g.: 2024-01-26 - 11:51:00
    raw_data_df = pd.read_parquet(
        f"{DATA_PATH_LOCAL}/{LAST_EXTRACT_DATE}_data_df.parquet"
    )

    # extract indices where the first non-NaN value occurs
    idx_nonnan_df = raw_data_df.reset_index().apply(lambda x: x.first_valid_index())

    # remove all columns that have the highest index
    idx_max_filter = idx_nonnan_df.max()
    REMOVE_COLS = idx_nonnan_df.loc[idx_nonnan_df == idx_max_filter].index.to_list()
    raw_data_df_reduced = raw_data_df.drop(columns=REMOVE_COLS)

    # remove first missings from dataframe
    # NOTE: At this point columns with a lot of NaNs are removed and some rows
    # according to TARGET_COLS were truncated
    sliced_df = slice_df(dataframe=raw_data_df_reduced, cols=TARGET_COLS)
    sliced_df_sorted = sliced_df.sort_index(axis=1)

    # count NaNs and extract unique values for vars with D0 prefix
    counted_nans = sliced_df_sorted.isna().sum() / sliced_df_sorted.shape[0]
    uniq_val_dict = {
        col: sliced_df_sorted[col].unique().tolist()
        for col in sliced_df_sorted.columns
        if col.startswith("DO")
    }

    # extract value ranges for columns starting with MW
    val_ranges = {
        col: (sliced_df_sorted[col].min(), sliced_df_sorted[col].max())
        for col in sliced_df_sorted.columns
        if col.startswith("MW")
    }

    # create plots for SMEs to identify reasons for gaps in the data
    plot_timeseries_with_nans(df=sliced_df_sorted, save_path=SAVE_PATH)

    # NOTE: Data quality is poor, removing non valuable columns
    # remove all columns where 20% are NaN/ Nulls
    trunc_df = drop_columns_with_missing(sliced_df_sorted, threshold=0.20)

    # define meaningfull value ranges for trunc_df.columns.tolist() columns
    VALUE_RANGES: dict[str, list[float]] = {
        "DO_Abschaeumer_Außenspuelung_KF5": [0, 1],
        "DO_Trommelfilter_Spülpumpe_QA4": [0, 1],
        # "MW-Differenz_Sumpf_Becken": [], # no value ranges specified, but can be calculated, excluded
        # "MW-Drehzahl_Getriebemotor": [], # no value ranges specified, negative values present, excluded
        "MW-Drehzahl_Hauptkreislaufpumpe": [0, 100],
        "MW-LVL-Becken": [1000, 1500],
        "MW-LVL-Biofilter": [2000, 2500],
        "MW-LVL-Sumpf": [1000, 1500],
        "MW-PSU": [10, 25],
        "MW-Redox-Abschäumer": [150, 600],
        "MW-Redox-Denitrifikation": [-350, -290],
        "MW-Redox-Prozesswasser": [100, 400],
        "MW-SauerstoffProzent-1": [50, 150],
        "MW-SauerstoffProzent-2": [50, 150],
        # "MW-Temperatur-Außen": [], # no values, excluded
        "MW-Temperatur-Innen": [10, 40],
        "MW-Temperatur_Wasser": [10, 40],
        # "MW-Wasservolumen_Becken": [], # no values, excluded
        "MW-pH": [5.5, 8.5],
    }

    # replace all values with min and max from VALUE_RANGES, interpolate misisng values
    cleaned_ranges_df = clean_dataframe(df=trunc_df, value_ranges=VALUE_RANGES)

    # clip in between values for binary cols
    cleaned_bin_df = clip_binary_columns(
        df=cleaned_ranges_df,
        columns=["DO_Abschaeumer_Außenspuelung_KF5", "DO_Trommelfilter_Spülpumpe_QA4"],
    )

    # remove all columns that has almost no variance
    cleaned_df = drop_highly_imbalanced(df=cleaned_bin_df, threshold=0.9)

    cleaned_df.drop(
        columns=[
            "MW-Wasservolumen_Becken",
            "MW-Temperatur-Außen",
            "MW-Drehzahl_Getriebemotor",
            "MW-Differenz_Sumpf_Becken",
            "MW-Drehzahl_Getriebemotor",
        ],
        inplace=True,
    )  # see above

    if cleaned_df.isna().any().any():
        raise Exception("Abort analysis because there are still NaN's in the data.")

    ########################################################################
    # scale features and create heatmap/ correlation matrix
    ########################################################################

    # feature engineering target
    scaled_df = scale_dataframe_by_ranges(cleaned_df, value_ranges=VALUE_RANGES)

    # resample on 5 min freq
    # TODO: include in function
    resamp_df = scaled_df.resample("5T").first()
    resamp_filled_df = resamp_df.fillna(method="ffill")

    # lag features by t-3 (15 min.)
    lagged_df = create_lagged_features(resamp_filled_df, lags=3)

    # compute and correlation matrix
    plot_corr_heatmap(lagged_df)

    # resample data and removed non lagged features
    # NOTE: target is MW-LVL-Sumpf (1.9)
    lagged_df.drop(
        columns=[
            "MW-Drehzahl_Hauptkreislaufpumpe",
            "MW-LVL-Becken",
            "MW-LVL-Biofilter",
            "MW-PSU",
            "MW-Redox-Abschäumer",
            "MW-Redox-Denitrifikation",
            "MW-Redox-Prozesswasser",
            "MW-SauerstoffProzent-1",
            "MW-SauerstoffProzent-2",
            "MW-Temperatur-Innen",
            "MW-Temperatur_Wasser",
            "MW-pH",
        ],
        inplace=True,
    )

    # fill gaps with last available value
    # plot_timeseries_with_nans(df=lagged_df, save_path=SAVE_PATH+ "/resamp")
    if lagged_df.isna().any().any():
        raise Exception("NaN values found in resampled dataframe.")

    ########################################################################
    # fit simple model on data and evaluate performance metrics
    ########################################################################
    # create ds and y columns for prophet
    df = lagged_df.reset_index().rename(
        columns={"timestamp": "ds", "MW-LVL-Sumpf": "y"}
    )
    regressors = [col for col in df.columns if col not in ["ds", "y"]]

    # create model instance
    model = Prophet()
    for reg in regressors:
        model.add_regressor(reg)

    # simple train test split
    train_size = int(len(df) * 0.8)
    train_df = df.iloc[:train_size]
    test_df = df.iloc[train_size:]

    # fit model
    model.fit(train_df)

    # evaluate metrics
    future = test_df[["ds"] + regressors]
    forecasts = model.predict(future)

    mse = mean_squared_error(test_df["y"], forecasts["yhat"])
    mae = mean_absolute_error(test_df["y"], forecasts["yhat"])

    # plot y vs. y_hat
    plot_predictions(test_df, forecasts, target_col="y")
    plot_predictions(test_df.iloc[29600:,], forecasts.iloc[29600:,], target_col="y")

    print(f"MSE: {mse:.6f}, MAE: {mae:.2f}")

    # plot of re-scaled vars
    plot_actual_vs_predicted_original(
        test_df=test_df,
        forecast=forecasts,
        target_col="MW-LVL-Sumpf",
        value_ranges=VALUE_RANGES,
    )

    plot_actual_vs_predicted_original(
        test_df=test_df.iloc[29400:,],
        forecast=forecasts.iloc[29400:,],
        target_col="MW-LVL-Sumpf",
        value_ranges=VALUE_RANGES,
    )

    # 
    min_val, max_val = VALUE_RANGES["MW-LVL-Sumpf"]

    print(
        f"MAE in mm: {mean_absolute_error(test_df['y'] * (max_val - min_val) + min_val, forecasts['yhat'] * (max_val - min_val) + min_val):.2f}"
    )
