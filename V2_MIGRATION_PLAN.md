# pym2v v2 Migration Plan

## Overview
This document outlines the migration plan for pym2v v2, focusing on stability, performance, and dependency reduction as requested.

## Key Changes

### 1. Replace pandas with polars
**Rationale:**
- Better performance (10-100x faster for many operations)
- Lower memory footprint
- Better API consistency
- Built-in lazy evaluation for query optimization
- Native arrow support (we already use pyarrow)

**Impact:**
- `api.py`: All DataFrame return types and pandas operations need conversion
- `utils.py`: `batch_interval` function uses pandas Timestamp/Timedelta
- `types.py`: Type hints need updating
- All DataFrame-returning methods need conversion

**Migration Tasks:**
- Update `get_frame_from_names()` to return `pl.DataFrame`
- Update `get_long_frame_from_names()` to return `pl.DataFrame`
- Update `asmart_get_frame_from_names()` to return `pl.DataFrame`
- Replace `pd.Timestamp` with `datetime` or polars native types
- Replace `pd.Timedelta` with `timedelta` or polars native types
- Update `batch_interval()` to use standard library or polars types

### 2. Replace requests with httpx
**Rationale:**
- Async-first design (better for existing async methods)
- Modern API with better defaults
- Better connection pooling
- HTTP/2 support
- Smaller dependency tree
- Still supports OAuth2

**Impact:**
- `api.py`: Complete rewrite of OAuth2 session handling
- Need to implement OAuth2 flow with httpx (can use httpx-auth or authlib)
- All `self._session.get()` and `self._session.post()` calls need updating
- Async methods can use native httpx async support (no executor needed)

**Migration Tasks:**
- Replace OAuth2Session with httpx client + OAuth2 token handling
- Update all HTTP methods to use httpx
- Leverage native async support in `asmart_get_frame_from_names`
- Add proper connection pooling with httpx.Client

### 3. Remove loguru, use standard logging
**Rationale:**
- Reduces dependencies
- Standard library is sufficient for logging needs
- Better integration with other Python tools
- No performance impact

**Impact:**
- `api.py`: Replace `logger.debug()`, `logger.info()`, `logger.warning()`, `logger.error()`
- `utils.py`: Replace logger in retry callback
- Users can configure logging as needed using standard Python logging

**Migration Tasks:**
- Replace all `loguru.logger` imports with `logging.getLogger(__name__)`
- Update log calls to use standard logging methods
- Remove loguru from dependencies

## Code Quality Improvements

### Issues Found:
1. **Unused import in api.py**: `asyncio` imported but semaphore not properly scoped
2. **Inconsistent error handling**: Some methods raise_for_status(), others don't
3. **Missing type hints**: Some return types could be more specific
4. **Double progress bar**: Line 395 in `get_long_frame_from_names` wraps already wrapped batches
5. **Inefficient JSON handling**: No streaming for large payloads
6. **Hardcoded semaphore**: `_limit = asyncio.Semaphore(5)` is module-level, should be instance-level

### Improvements:
1. Make semaphore an instance variable for better control
2. Add consistent error handling across all methods
3. Use httpx streaming for large responses
4. Fix double progress bar issue
5. Add more specific type hints
6. Better async patterns with native httpx

## Performance Optimizations

1. **Polars benefits:**
   - Lazy evaluation for complex queries
   - Parallel processing built-in
   - Better memory management
   - Optimized for columnar data

2. **httpx benefits:**
   - Connection pooling
   - HTTP/2 support
   - Better async performance
   - Efficient request/response handling

3. **Reduced dependencies:**
   - Fewer transitive dependencies
   - Smaller install size
   - Faster import times

## Dependency Changes

### Remove:
- `loguru>=0.7.3`
- `pandas[excel]>=2.2.3` (keep pyarrow)
- `requests-oauthlib>=2.0.0`

### Add:
- `polars>=1.0.0`
- `httpx>=0.28.0`
- `authlib>=1.3.0` (for OAuth2 with httpx)

### Keep:
- `pyarrow>=21.0.0` (works well with polars)
- `pydantic-settings>=2.6.1`
- `tenacity>=9.0.0`
- `tqdm>=4.67.1`

## Migration Strategy

### Phase 1: Preparation
1. Create branch for v2 development
2. Update pyproject.toml with new dependencies
3. Add deprecation warnings to v1

### Phase 2: Core Migration
1. Replace logging (least risky)
2. Migrate HTTP client to httpx
3. Migrate pandas to polars (most risky, most beneficial)

### Phase 3: Testing & Validation
1. Update all tests
2. Run performance benchmarks
3. Test with real API
4. Update documentation

### Phase 4: Release
1. Update README with migration guide
2. Publish v2.0.0
3. Maintain v1.x for critical fixes only

## Compatibility Considerations

### Breaking Changes:
- Return type changes (pandas → polars DataFrames)
- Different DataFrame API (methods like `.to_list()` vs `.to_pandas()`)
- Logging configuration (users need to configure standard logging)

### Migration Guide for Users:
```python
# v1
import pandas as pd
from pym2v.api import EurogardAPI

api = EurogardAPI()
df = api.get_frame_from_names(...)  # Returns pd.DataFrame
values = df['column'].to_list()

# v2
import polars as pl
from pym2v.api import EurogardAPI

api = EurogardAPI()
df = api.get_frame_from_names(...)  # Returns pl.DataFrame
values = df['column'].to_list()

# Or convert to pandas if needed
df_pandas = df.to_pandas()
```

## Testing Plan

1. Unit tests for all modified methods
2. Integration tests with mocked API
3. Performance benchmarks:
   - Data processing speed (pandas vs polars)
   - Memory usage
   - API call performance
4. Compatibility tests with real API endpoints

## Documentation Updates

1. Update README with v2 features and migration guide
2. Update docstrings with new return types
3. Add performance comparison section
4. Update examples to use polars DataFrames
5. Document logging configuration

## Timeline

- **Phase 1**: 1-2 days
- **Phase 2**: 3-5 days
- **Phase 3**: 2-3 days
- **Phase 4**: 1 day

Total: ~7-11 days for complete migration

## Risks & Mitigation

### Risks:
1. **API compatibility**: Polars DataFrames have different API than pandas
2. **OAuth2 complexity**: httpx doesn't have built-in OAuth2 session
3. **User migration**: Breaking changes require user code updates

### Mitigation:
1. Provide clear migration guide and helper methods
2. Use well-tested OAuth2 library (authlib)
3. Consider providing compatibility layer for smooth transition
4. Extensive testing before release
5. Clear documentation of breaking changes

## Open Questions

1. Should we provide a compatibility mode that returns pandas DataFrames?
2. What's the minimum Python version for v2? (polars requires 3.8+)
3. Should we version the API to allow v1 and v2 to coexist?
4. Do we need to maintain v1.x branch for bug fixes?

## Success Criteria

- [ ] All dependencies migrated successfully
- [ ] All tests passing
- [ ] Performance improvements measured and documented
- [ ] Zero security vulnerabilities
- [ ] Documentation complete
- [ ] Migration guide available
- [ ] Backward compatibility strategy defined
