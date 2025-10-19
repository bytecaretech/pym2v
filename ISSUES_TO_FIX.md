# Immediate Issues to Fix (v1.x Stability Improvements)

This document lists issues that should be fixed in the current version (v1.x) for stability and correctness, independent of the v2 migration.

## Critical Issues (Should fix immediately)

### 1. Missing error handling - Inconsistent `raise_for_status()`

**Location:** `api.py`
**Lines:** 86, 126, 166

**Issue:**
Some methods call `response.raise_for_status()` while others don't, leading to inconsistent error handling.

```python
# Has error handling:
def get_routers(self, ...):
    response = self._session.get(...)
    response.raise_for_status()  # Line 124
    return response.json()

# Missing error handling:
def get_user_info(self) -> dict[str, Any]:
    response = self._session.get(...)
    return response.json()  # Line 86 - No raise_for_status()!

def get_machines(self, ...):
    response = self._session.get(...)
    return response.json()  # Line 166 - No raise_for_status()!
```

**Impact:** HTTP errors may be silently ignored, leading to confusing behavior and error messages.

**Fix:**
```python
def get_user_info(self) -> dict[str, Any]:
    response = self._session.get(...)
    response.raise_for_status()
    return response.json()

def get_machines(self, ...):
    response = self._session.get(...)
    response.raise_for_status()
    return response.json()
```

### 2. No timeout on HTTP requests

**Location:** `api.py`
**All HTTP methods**

**Issue:**
No timeout configured for HTTP requests, which can cause the application to hang indefinitely if the server is unresponsive.

**Impact:** Application can hang indefinitely, no way to recover from slow/dead servers.

**Fix:**
Add timeout to settings and use it in all requests:

```python
# settings.py
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="eurogard_", env_file=".env")
    base_url: str
    username: str
    password: str
    client_id: str
    client_secret: str
    timeout: int = 30  # Default 30 seconds
```

```python
# api.py
response = self._session.get(
    url,
    params=params,
    timeout=self._settings.timeout
)
```

### 3. Double progress bar

**Location:** `api.py`, line 395
**Method:** `get_long_frame_from_names`

**Issue:**
The progress bar always wraps `batches` even when `show_progress=False`:

```python
batches = list(batch_interval(start, end, max_frame_length))
if show_progress:
    batches = tqdm(batches)
dfs = []

for left, right in tqdm(batches):  # Line 395 - ALWAYS wraps, ignores show_progress!
```

**Impact:** Progress bar always shows when iterating, making `show_progress` parameter useless.

**Fix:**
```python
batches = list(batch_interval(start, end, max_frame_length))
if show_progress:
    batches = tqdm(batches)
dfs = []

for left, right in batches:  # Remove tqdm here
    data = self.get_frame_from_names(...)
```

## High Priority Issues

### 4. Module-level semaphore

**Location:** `api.py`, line 19

**Issue:**
Semaphore is at module level, shared across all API instances:

```python
_limit = asyncio.Semaphore(5)
```

**Impact:** 
- Concurrency limit shared across all API instances
- No way to configure per instance
- Can cause unexpected behavior with multiple instances

**Fix:**
```python
class EurogardAPI:
    def __init__(self, settings: Settings | None = None, max_concurrent: int = 5):
        if settings is None:
            settings = Settings()
        self._settings = settings
        self._token_url = settings.base_url + TOKEN_ROUTE
        self._session = self.create_session()
        self._limit = asyncio.Semaphore(max_concurrent)
```

### 5. Token updater does nothing

**Location:** `api.py`, line 58

**Issue:**
The token updater callback does nothing:

```python
oauth = OAuth2Session(
    client=client,
    auto_refresh_url=self._token_url,
    auto_refresh_kwargs=extras,
    token_updater=lambda x: x,  # Does nothing!
)
```

**Impact:** Unclear if token refresh works correctly, potential for token expiration issues.

**Fix:** Either implement proper token updater or document why it's not needed:

```python
# Option 1: Implement token storage
def token_updater(self, token):
    self._token = token
    # Could also save to file/database if needed

oauth = OAuth2Session(
    client=client,
    auto_refresh_url=self._token_url,
    auto_refresh_kwargs=extras,
    token_updater=self.token_updater,
)

# Option 2: Document why it's not needed
# If auto-refresh works without storing, add comment explaining
token_updater=lambda x: x,  # No-op: OAuth2Session handles token internally
```

## Medium Priority Issues

### 6. Large response logging

**Location:** `api.py`, lines 299-304

**Issue:**
Logs entire response text on JSON decode error:

```python
except JSONDecodeError:
    logger.error(f"Error decoding JSON: {response.text}")
    raise
```

**Impact:** Could log huge amounts of data, filling up logs.

**Fix:**
```python
except JSONDecodeError:
    max_log_size = 500
    response_preview = response.text[:max_log_size]
    if len(response.text) > max_log_size:
        response_preview += "... (truncated)"
    logger.error(
        f"Error decoding JSON. Status: {response.status_code}, "
        f"Size: {len(response.text)} bytes, "
        f"Preview: {response_preview}"
    )
    raise
```

### 7. Missing validation in batch_interval

**Location:** `utils.py`, function `batch_interval`

**Issue:**
No validation that start < end or that max_interval > 0:

```python
def batch_interval(start: TsInput, end: TsInput, max_interval: IntInput = "1D"):
    start = pd.Timestamp(start)
    end = pd.Timestamp(end)
    max_interval = pd.Timedelta(max_interval)
    left = start
    
    while left < end:  # What if start >= end? Infinite loop!
        right = min(left + max_interval, end)
        yield left, right
        left = right
```

**Impact:** Potential infinite loop or unexpected behavior.

**Fix:**
```python
def batch_interval(start: TsInput, end: TsInput, max_interval: IntInput = "1D"):
    start = pd.Timestamp(start)
    end = pd.Timestamp(end)
    max_interval = pd.Timedelta(max_interval)
    
    if start >= end:
        raise ValueError(f"start must be less than end: {start} >= {end}")
    if max_interval <= pd.Timedelta(0):
        raise ValueError(f"max_interval must be positive: {max_interval}")
    
    left = start
    while left < end:
        right = min(left + max_interval, end)
        yield left, right
        left = right
```

### 8. No custom exceptions

**Location:** Throughout codebase

**Issue:**
No custom exception types, making it hard for users to handle specific errors:

```python
# Current - all errors are generic
try:
    api.get_machines()
except Exception as e:
    # Can't distinguish between network error, auth error, etc.
    pass
```

**Impact:** Hard to write robust error handling in user code.

**Fix:** Add custom exceptions:

```python
# exceptions.py (new file)
class Pym2vError(Exception):
    """Base exception for pym2v."""
    pass

class AuthenticationError(Pym2vError):
    """Authentication failed."""
    pass

class APIError(Pym2vError):
    """API request failed."""
    def __init__(self, message, status_code=None, response=None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response

class RateLimitError(APIError):
    """Rate limit exceeded."""
    pass
```

Then use in api.py:

```python
def get_machines(self, ...):
    try:
        response = self._session.get(...)
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as e:
        if e.response.status_code == 401:
            raise AuthenticationError("Authentication failed") from e
        elif e.response.status_code == 429:
            raise RateLimitError("Rate limit exceeded") from e
        else:
            raise APIError(f"API request failed: {e}", e.response.status_code, e.response) from e
```

## Low Priority Issues

### 9. Type hints could be more specific

**Location:** Various

**Issue:**
Some return types are generic `dict[str, Any]` when they could be more specific using Pydantic models.

**Impact:** Less type safety, harder to use with type checkers.

**Fix:** Define Pydantic models for API responses (can be done in v2).

### 10. No logging configuration

**Issue:**
No way to configure logging level for the library.

**Impact:** Users can't control verbosity of library logging.

**Fix:** Document how to configure logging, or add to settings:

```python
# settings.py
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="eurogard_", env_file=".env")
    base_url: str
    username: str
    password: str
    client_id: str
    client_secret: str
    log_level: str = "INFO"  # Add logging level
```

## Testing Gaps

### Missing tests for:
1. Error handling (HTTP errors, network errors, timeouts)
2. Retry logic (tenacity integration)
3. Async methods (`asmart_get_frame_from_names`)
4. Edge cases (empty data, large datasets)
5. OAuth token refresh
6. Progress bar behavior

## Summary of Fixes Needed

| Issue | Priority | Effort | Risk |
|-------|----------|--------|------|
| Inconsistent error handling | Critical | Low | Low |
| No timeout on requests | Critical | Low | Low |
| Double progress bar | Critical | Low | Low |
| Module-level semaphore | High | Low | Low |
| Token updater no-op | High | Medium | Medium |
| Large response logging | Medium | Low | Low |
| Missing validation | Medium | Low | Low |
| No custom exceptions | Medium | Medium | Low |
| Generic type hints | Low | Medium | Low |
| No logging config | Low | Low | Low |

**Total estimated effort for all critical + high priority issues:** 2-3 hours
**Recommended:** Fix critical issues immediately, high priority in next patch release
