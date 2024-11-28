from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

type TsInput = np.integer | pd.Timestamp | float | str | date | datetime | np.datetime64
type IntInput = str | int | pd.Timedelta | timedelta | np.timedelta64
