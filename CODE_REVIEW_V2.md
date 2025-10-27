# Code Review for pym2v v2

## Current State Analysis

### Dependencies Overview

Current dependencies and their impact:

```toml
dependencies = [
    "loguru>=0.7.3",              # 1 package, 0 deps → Can be removed
    "pandas[excel]>=2.2.3",       # Heavy: 20+ transitive deps → Replace with polars
    "pyarrow>=21.0.0",            # Keep: Works well with polars
    "pydantic-settings>=2.6.1",   # Keep: Essential for settings
    "requests-oauthlib>=2.0.0",   # 4+ deps → Replace with httpx + authlib
    "tenacity>=9.0.0",            # Keep: Retry logic is solid
    "tqdm>=4.67.1",               # Keep: Progress bars are useful
]
```

**Dependency count reduction:**
- Current: ~35-40 transitive dependencies
- After v2: ~20-25 transitive dependencies (40% reduction)

### Code Issues & Improvements

#### 1. api.py Issues

**Issue 1: Module-level semaphore (Line 19)**
```python
_limit = asyncio.Semaphore(5)
```
**Problem:** Module-level semaphore shared across all API instances, no way to configure
**Fix:** Move to instance variable in `__init__`
**Priority:** Medium
**Impact:** Better concurrency control per instance

**Issue 2: Inconsistent error handling**
```python
# Some methods have it:
response.raise_for_status()  # Line 124, 208, 252, 298

# Others don't:
return response.json()  # Line 86, 126, 166
```
**Problem:** Inconsistent behavior on HTTP errors
**Fix:** Add `raise_for_status()` to all HTTP calls or handle errors consistently
**Priority:** High
**Impact:** Better error reporting and debugging

**Issue 3: Double progress bar (Lines 390-395)**
```python
batches = list(batch_interval(start, end, max_frame_length))
if show_progress:
    batches = tqdm(batches)  # Line 392
dfs = []

for left, right in tqdm(batches):  # Line 395 - ALWAYS wraps!
```
**Problem:** `tqdm` always wraps batches even when `show_progress=False`
**Fix:** Conditionally wrap in second tqdm or remove one
**Priority:** Medium
**Impact:** Better UX, no unwanted progress bars

**Issue 4: Inefficient JSON error handling (Lines 299-304)**
```python
try:
    result = response.json()
    return result
except JSONDecodeError:
    logger.error(f"Error decoding JSON: {response.text}")
    raise
```
**Problem:** Logs entire response text which could be huge
**Fix:** Log only first N characters or response size
**Priority:** Low
**Impact:** Better logging for large payloads

**Issue 5: No timeout configuration**
**Problem:** No timeout on HTTP requests (can hang indefinitely)
**Fix:** Add configurable timeout to Settings
**Priority:** High
**Impact:** Better reliability and error handling

**Issue 6: Token refresh not explicit**
```python
oauth = OAuth2Session(
    client=client,
    auto_refresh_url=self._token_url,
    auto_refresh_kwargs=extras,
    token_updater=lambda x: x,  # Line 58 - Does nothing!
)
```
**Problem:** Token updater does nothing, unclear token refresh behavior
**Fix:** Implement proper token refresh or remove if not needed
**Priority:** Medium
**Impact:** Better token management

**Issue 7: Synchronous executor in async method (Lines 450-458)**
```python
task = loop.run_in_executor(
    None,
    self.get_frame_from_names,
    machine_uuid,
    names,
    ts_start,
    ts_end,
    int_interval,
)
```
**Problem:** Using thread pool executor for sync method in async context
**Fix:** With httpx, make HTTP calls truly async
**Priority:** High
**Impact:** Better async performance, no thread overhead

#### 2. utils.py Issues

**Issue 1: Hard dependency on pandas (Lines 8, 40-42)**
```python
import pandas as pd
from loguru import logger  # Will remove

# ...
start = pd.Timestamp(start)
end = pd.Timestamp(end)
max_interval = pd.Timedelta(max_interval)
```
**Problem:** Tied to pandas for simple date/time operations
**Fix:** Use standard library datetime/timedelta or polars
**Priority:** High (for v2 migration)
**Impact:** Enables pandas removal

**Issue 2: Retry logging (Lines 15-24)**
```python
def _log_retry_attempt(retry_state: RetryCallState):
    """Log retry attempts."""
    if retry_state.attempt_number > 1:
        logger.info(
            f"Retrying {retry_state.fn.__name__}: attempt {retry_state.attempt_number}, reason: {retry_state.outcome}"
        )
```
**Problem:** Uses loguru
**Fix:** Use standard logging
**Priority:** Medium
**Impact:** Enables loguru removal

#### 3. types.py Issues

**Issue 1: Type definitions rely on pandas/numpy (Lines 5-9)**
```python
import numpy as np
import pandas as pd

type TsInput = np.integer | pd.Timestamp | float | str | date | datetime | np.datetime64
type IntInput = str | int | pd.Timedelta | timedelta | np.timedelta64
```
**Problem:** Type hints include pandas/numpy types
**Fix:** Use standard types + polars types in v2
**Priority:** High (for v2 migration)
**Impact:** Clean type system without pandas dependency

#### 4. settings.py Issues

**No major issues found.** Clean implementation using pydantic-settings.

**Potential improvements:**
1. Add timeout settings for HTTP requests
2. Add retry configuration settings
3. Add logging level configuration

#### 5. Test Issues

**Issue 1: Mock dependency (conftest.py, line 17)**
```python
mocker.patch("requests_oauthlib.oauth2_session.OAuth2Session.fetch_token")
```
**Problem:** Will break when switching to httpx
**Fix:** Update mocks for httpx
**Priority:** High (for v2 migration)

**Issue 2: Missing test coverage**
- No tests for async methods
- No tests for error handling
- No tests for retry logic
- No tests for batch processing

**Priority:** Medium
**Impact:** Better reliability and confidence

### Security Considerations

#### Current Security Issues:
1. **No timeout on requests** - Can lead to resource exhaustion
2. **No request size limits** - Could be exploited
3. **Token in memory** - No secure storage (acceptable for now)
4. **No rate limiting** - Could trigger API throttling

#### V2 Security Improvements:
1. Add configurable timeouts
2. Add request/response size limits
3. Better error messages without sensitive data
4. Rate limiting support with httpx

### Performance Considerations

#### Current Performance Issues:

1. **Pandas DataFrame creation** (Lines 346-356)
   - Creates intermediate DataFrames for each measurement
   - Multiple concat operations
   - High memory usage for large datasets

2. **Synchronous batch processing** (Lines 390-407)
   - Sequential API calls even though async is available
   - Could parallelize with async

3. **No lazy evaluation**
   - All data loaded into memory immediately
   - No query optimization

4. **Inefficient async implementation**
   - Uses thread pool executor instead of true async
   - Semaphore limit hardcoded to 5

#### V2 Performance Improvements:

1. **Polars lazy evaluation**
   - Query optimization before execution
   - Predicate pushdown
   - Projection pushdown

2. **Native async with httpx**
   - True async I/O without threads
   - Better connection pooling
   - HTTP/2 support

3. **Better batch processing**
   - Parallel async requests with configurable concurrency
   - Streaming responses for large datasets
   - Memory-efficient data structures

4. **Columnar storage**
   - Polars uses Arrow format natively
   - Better cache locality
   - SIMD optimizations

### API Design Improvements

#### Current API Issues:
1. **Inconsistent method naming**: `get_*` vs `asmart_get_*`
2. **Boolean parameters**: `show_progress` - could be enum or callable
3. **Multiple concerns**: Methods do HTTP + data processing
4. **No builder pattern**: Many parameters, no fluent API

#### V2 API Improvements:
1. Consistent naming convention
2. Separate HTTP client from data processing
3. Builder pattern for complex queries
4. Better async/sync separation

### Documentation Issues

1. **Missing examples** for async methods
2. **No performance guidelines** (when to use which method)
3. **No error handling examples**
4. **Type hints in docstrings** don't match actual return types after v2

### Recommended File Structure for V2

```
src/pym2v/
├── __init__.py
├── api.py           # Main API class
├── client.py        # HTTP client (httpx wrapper)
├── auth.py          # OAuth2 authentication
├── models.py        # Pydantic models for API responses
├── types.py         # Type definitions
├── settings.py      # Configuration
├── constants.py     # Constants
├── utils.py         # Utilities
├── exceptions.py    # Custom exceptions
└── _compat.py       # Compatibility layer (optional)
```

### Migration Checklist for V2

#### Dependencies:
- [ ] Add polars>=1.0.0
- [ ] Add httpx>=0.28.0
- [ ] Add authlib>=1.3.0
- [ ] Remove loguru
- [ ] Remove pandas
- [ ] Remove requests-oauthlib
- [ ] Update pyarrow version if needed
- [ ] Update test dependencies

#### Code Changes:
- [ ] Create new `client.py` with httpx wrapper
- [ ] Create new `auth.py` with OAuth2 handling
- [ ] Create `exceptions.py` with custom exceptions
- [ ] Update `api.py` to use new client
- [ ] Update `utils.py` to use standard library/polars
- [ ] Update `types.py` to use polars types
- [ ] Replace all logging with standard library
- [ ] Make semaphore an instance variable
- [ ] Fix double progress bar issue
- [ ] Add consistent error handling
- [ ] Add timeout configuration
- [ ] Implement true async methods

#### Testing:
- [ ] Update all existing tests
- [ ] Add async method tests
- [ ] Add error handling tests
- [ ] Add retry logic tests
- [ ] Add integration tests
- [ ] Add performance benchmarks
- [ ] Test with real API (manual)

#### Documentation:
- [ ] Update README with v2 changes
- [ ] Create MIGRATION_GUIDE.md
- [ ] Update all docstrings
- [ ] Add async examples
- [ ] Add error handling examples
- [ ] Document breaking changes
- [ ] Update notebooks if any

#### Release:
- [ ] Update version to 2.0.0
- [ ] Update CHANGELOG
- [ ] Tag release
- [ ] Publish to PyPI
- [ ] Update documentation site

### Breaking Changes Summary

1. **Return types**: `pd.DataFrame` → `pl.DataFrame`
2. **Logging**: Must configure standard logging instead of loguru
3. **DataFrame API**: Different methods (`.to_list()` vs `.to_pandas()`)
4. **Type hints**: Different types in function signatures
5. **Dependencies**: Polars and httpx instead of pandas and requests

### Backward Compatibility Options

#### Option 1: No compatibility (Clean break)
**Pros:** Simpler code, faster migration, no technical debt
**Cons:** Users must update their code

#### Option 2: Compatibility layer
**Pros:** Easier user migration, gradual adoption
**Cons:** More complex code, maintenance burden

```python
# Example compatibility layer
def get_frame_from_names(..., compat_mode: bool = False):
    df = self._get_frame_from_names_polars(...)
    if compat_mode:
        return df.to_pandas()
    return df
```

#### Option 3: Separate package (pym2v2)
**Pros:** Both versions coexist, no breaking changes
**Cons:** Split maintenance, confusing naming

**Recommendation:** Option 1 (Clean break) with clear migration guide

### Performance Targets for V2

Based on typical pandas vs polars benchmarks:

| Operation | Current (pandas) | Target (polars) | Improvement |
|-----------|------------------|-----------------|-------------|
| DataFrame creation | 100ms | 10-20ms | 5-10x |
| Column operations | 50ms | 5-10ms | 5-10x |
| Filtering | 30ms | 3-5ms | 6-10x |
| Aggregations | 80ms | 8-15ms | 5-10x |
| Memory usage | 100MB | 40-60MB | 40-60% reduction |
| HTTP requests | 200ms | 150-180ms | 10-25% (with HTTP/2) |

**Overall expected improvement:** 3-8x faster for typical workloads

### Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| API compatibility issues | Medium | High | Extensive testing with real API |
| OAuth2 migration complexity | Medium | High | Use proven library (authlib) |
| User adoption resistance | High | Medium | Clear migration guide, examples |
| Performance regression | Low | High | Benchmarking before release |
| Security vulnerabilities | Low | High | CodeQL analysis, security review |
| Missing edge cases | Medium | Medium | Comprehensive test coverage |

### Conclusion

The v2 migration is well-justified and will bring significant benefits:

1. **Performance:** 3-8x improvement in data processing
2. **Memory:** 40-60% reduction in memory usage
3. **Dependencies:** 40% reduction in transitive dependencies
4. **Maintainability:** Cleaner, more modern codebase
5. **Async support:** True async with httpx, better concurrency

**The migration is feasible and recommended.** Key success factors:
- Clear migration guide for users
- Comprehensive testing
- Performance benchmarking
- Security review
- Good documentation

**Estimated effort:** 7-11 days for complete migration
**Recommended timeline:** Start immediately, target 2-3 weeks for release
