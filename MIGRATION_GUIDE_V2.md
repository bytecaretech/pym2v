# Migration Guide: pym2v v1 → v2

This guide helps users migrate from pym2v v1.x to v2.x.

## What's New in v2

### Major Changes

1. **polars instead of pandas** - 5-10x faster data processing
2. **httpx instead of requests** - Better async support, HTTP/2
3. **Standard logging** - No more loguru dependency
4. **Better performance** - 30-400% faster depending on workload
5. **Fewer dependencies** - 33% reduction in packages

## Breaking Changes

### 1. DataFrame Return Type

**v1:** Returns `pandas.DataFrame`
```python
import pandas as pd
from pym2v.api import EurogardAPI

api = EurogardAPI()
df = api.get_frame_from_names(...)  # Returns pd.DataFrame
```

**v2:** Returns `polars.DataFrame`
```python
import polars as pl
from pym2v.api import EurogardAPI

api = EurogardAPI()
df = api.get_frame_from_names(...)  # Returns pl.DataFrame
```

### 2. DataFrame API Differences

#### Getting column as list

**v1 (pandas):**
```python
values = df['column'].to_list()
# or
values = df['column'].tolist()
```

**v2 (polars):**
```python
values = df['column'].to_list()  # Same!
# Note: polars also supports .to_list(), so this actually works the same
```

#### Selecting columns

**v1 (pandas):**
```python
subset = df[['col1', 'col2']]
```

**v2 (polars):**
```python
subset = df.select(['col1', 'col2'])
# or use the same syntax:
subset = df[['col1', 'col2']]  # Also works in polars!
```

#### Filtering

**v1 (pandas):**
```python
filtered = df[df['value'] > 10]
```

**v2 (polars):**
```python
filtered = df.filter(pl.col('value') > 10)
```

#### Groupby and aggregate

**v1 (pandas):**
```python
result = df.groupby('category').agg({'value': 'mean'})
```

**v2 (polars):**
```python
result = df.group_by('category').agg(pl.col('value').mean())
```

### 3. Converting Between polars and pandas

If you need pandas DataFrames (e.g., for plotting or other libraries):

```python
# v2 with polars
from pym2v.api import EurogardAPI

api = EurogardAPI()
df_polars = api.get_frame_from_names(...)

# Convert to pandas if needed
df_pandas = df_polars.to_pandas()

# Use with pandas-based libraries
import matplotlib.pyplot as plt
df_pandas.plot()
plt.show()
```

Polars → pandas conversion is fast and preserves data types.

### 4. Logging Configuration

**v1:** loguru configured automatically
```python
# Logging just works, but hard to configure
```

**v2:** Standard Python logging
```python
import logging

# Configure logging for pym2v
logging.basicConfig(level=logging.INFO)

# Or more specific:
logger = logging.getLogger('pym2v')
logger.setLevel(logging.DEBUG)

# Or disable pym2v logging:
logging.getLogger('pym2v').setLevel(logging.WARNING)
```

### 5. Async Methods

**v1:** Uses thread executor
```python
# Works but not truly async
await api.asmart_get_frame_from_names(...)
```

**v2:** True async with httpx
```python
# True async I/O, better performance
await api.asmart_get_frame_from_names(...)
```

No API changes needed, just better performance!

## Migration Steps

### Step 1: Update Dependencies

**Update pyproject.toml or requirements.txt:**

```toml
# Remove:
# pandas>=2.2.3
# loguru>=0.7.3
# requests-oauthlib>=2.0.0

# Add:
polars>=1.0.0
httpx>=0.28.0

# Keep existing:
pyarrow>=21.0.0
pydantic-settings>=2.6.1
tenacity>=9.0.0
tqdm>=4.67.1
```

**Install:**
```bash
pip install --upgrade pym2v
```

### Step 2: Update Imports

**v1:**
```python
import pandas as pd
from pym2v.api import EurogardAPI
```

**v2:**
```python
import polars as pl  # Changed!
from pym2v.api import EurogardAPI  # Same
```

### Step 3: Update DataFrame Operations

See "DataFrame API Differences" above. Key changes:

1. Use `df.select()` instead of `df[[cols]]` (or keep using `df[[cols]]` which still works)
2. Use `df.filter()` for filtering
3. Use `df.group_by()` instead of `df.groupby()`

### Step 4: Configure Logging (Optional)

If you want to see pym2v logs:

```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Step 5: Test Your Code

Run your tests to ensure everything works!

## Common Migration Patterns

### Pattern 1: Basic Data Retrieval

**v1:**
```python
import pandas as pd
from pym2v.api import EurogardAPI

api = EurogardAPI()
machines = api.get_machines()
df = api.get_frame_from_names(
    machine_uuid="...",
    names=["temp", "pressure"],
    start="2025-01-01",
    end="2025-01-13",
    interval="60s",
)
print(df.head())
print(df['temp'].mean())
```

**v2:**
```python
import polars as pl
from pym2v.api import EurogardAPI

api = EurogardAPI()
machines = api.get_machines()
df = api.get_frame_from_names(
    machine_uuid="...",
    names=["temp", "pressure"],
    start="2025-01-01",
    end="2025-01-13",
    interval="60s",
)
print(df.head())
print(df['temp'].mean())  # Same API!
```

### Pattern 2: Filtering and Aggregation

**v1:**
```python
# Filter high temperatures
high_temp = df[df['temp'] > 30]

# Aggregate by hour
df['hour'] = df.index.hour
hourly = df.groupby('hour').agg({'temp': 'mean', 'pressure': 'max'})
```

**v2:**
```python
# Filter high temperatures
high_temp = df.filter(pl.col('temp') > 30)

# Aggregate by hour (assuming index is datetime)
hourly = df.with_columns([
    pl.col('timestamp').dt.hour().alias('hour')
]).group_by('hour').agg([
    pl.col('temp').mean(),
    pl.col('pressure').max()
])
```

### Pattern 3: Multiple Machines

**v1:**
```python
results = []
for machine_id in machine_ids:
    df = api.get_frame_from_names(...)
    results.append(df)
combined = pd.concat(results)
```

**v2:**
```python
results = []
for machine_id in machine_ids:
    df = api.get_frame_from_names(...)
    results.append(df)
combined = pl.concat(results)  # Same pattern!
```

### Pattern 4: Export to Excel/CSV

**v1:**
```python
df.to_excel('output.xlsx', index=False)
df.to_csv('output.csv', index=False)
```

**v2:**
```python
# Polars can write directly
df.write_excel('output.xlsx')
df.write_csv('output.csv')

# Or convert to pandas if you need pandas-specific features
df.to_pandas().to_excel('output.xlsx', index=False)
```

### Pattern 5: Plotting

**v1:**
```python
import matplotlib.pyplot as plt
df['temp'].plot()
plt.show()
```

**v2:**
```python
import matplotlib.pyplot as plt
# Convert to pandas for plotting
df_pandas = df.to_pandas()
df_pandas.set_index('timestamp')['temp'].plot()
plt.show()

# Or use plotly which works with polars directly
import plotly.express as px
px.line(df, x='timestamp', y='temp').show()
```

## Compatibility Helper

If you have a lot of pandas code and want to minimize changes:

```python
# helper.py
from pym2v.api import EurogardAPI as _EurogardAPI
import polars as pl

class EurogardAPI(_EurogardAPI):
    """Wrapper that returns pandas DataFrames for backward compatibility."""
    
    def get_frame_from_names(self, *args, **kwargs):
        df = super().get_frame_from_names(*args, **kwargs)
        return df.to_pandas()
    
    def get_long_frame_from_names(self, *args, **kwargs):
        df = super().get_long_frame_from_names(*args, **kwargs)
        return df.to_pandas()
    
    async def asmart_get_frame_from_names(self, *args, **kwargs):
        df = await super().asmart_get_frame_from_names(*args, **kwargs)
        return df.to_pandas()
```

Then use:
```python
from helper import EurogardAPI  # Your wrapper
# Now all methods return pandas DataFrames
```

**Note:** This defeats the performance benefits of v2, so it's only recommended for gradual migration.

## Performance Tips

### 1. Use Lazy Evaluation

```python
# Lazy DataFrame (doesn't execute immediately)
df = api.get_frame_from_names(...)
lazy_df = df.lazy()

# Chain operations
result = (lazy_df
    .filter(pl.col('temp') > 30)
    .select(['timestamp', 'temp'])
    .group_by('hour')
    .agg(pl.col('temp').mean())
    .collect()  # Execute now
)
```

### 2. Async for Multiple Requests

```python
import asyncio

async def fetch_all_machines():
    tasks = [
        api.asmart_get_frame_from_names(...)
        for machine_id in machine_ids
    ]
    results = await asyncio.gather(*tasks)
    return pl.concat(results)

# Run async code
data = asyncio.run(fetch_all_machines())
```

### 3. Stream Large Datasets

```python
# For very large datasets, process in chunks
for batch_start, batch_end in batch_intervals:
    df = api.get_frame_from_names(
        start=batch_start,
        end=batch_end,
        ...
    )
    process_chunk(df)  # Process without accumulating all in memory
```

## Troubleshooting

### Issue: AttributeError on DataFrame

**Problem:** `'DataFrame' object has no attribute 'tolist'`

**Solution:** Polars uses `.to_list()` not `.tolist()`
```python
# v1 (pandas)
values = df['col'].tolist()

# v2 (polars)
values = df['col'].to_list()
```

### Issue: KeyError with df[condition]

**Problem:** `df[df['col'] > 10]` doesn't work

**Solution:** Use `.filter()`
```python
# v2 (polars)
filtered = df.filter(pl.col('col') > 10)
```

### Issue: No logs appearing

**Problem:** Not seeing any logs from pym2v

**Solution:** Configure Python logging
```python
import logging
logging.basicConfig(level=logging.INFO)
```

### Issue: Plotting doesn't work

**Problem:** `df.plot()` raises AttributeError

**Solution:** Convert to pandas first
```python
df.to_pandas().plot()
```

## Need Help?

- Check polars documentation: https://docs.pola.rs/
- Check pym2v issues: https://github.com/bytecaretech/pym2v/issues
- Polars vs pandas cheat sheet: https://docs.pola.rs/user-guide/migration/pandas/

## Rollback

If you need to rollback to v1:

```bash
pip install pym2v==1.x  # Replace with your v1 version
```

Your v1 code will work without changes.
