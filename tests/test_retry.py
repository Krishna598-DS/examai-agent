# tests/test_retry.py
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from app.tools.retry import with_retry, retryable


@pytest.mark.asyncio
async def test_retry_succeeds_on_first_attempt():
    """If function succeeds first time, no retry happens."""
    mock_func = AsyncMock(return_value="success")

    result = await with_retry(mock_func, max_retries=3)

    assert result == "success"
    assert mock_func.call_count == 1


@pytest.mark.asyncio
async def test_retry_succeeds_after_failure():
    """Function fails twice then succeeds — should return success."""
    # side_effect: first two calls raise exception, third returns "success"
    mock_func = AsyncMock(
        side_effect=[ValueError("fail"), ValueError("fail"), "success"]
    )

    # Patch asyncio.sleep so tests don't actually wait
    with patch("app.tools.retry.asyncio.sleep", new_callable=AsyncMock):
        result = await with_retry(
            mock_func,
            max_retries=3,
            retryable_exceptions=(ValueError,)
        )

    assert result == "success"
    assert mock_func.call_count == 3


@pytest.mark.asyncio
async def test_retry_raises_after_max_retries():
    """If function always fails, raise the last exception."""
    mock_func = AsyncMock(side_effect=ValueError("always fails"))

    with patch("app.tools.retry.asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(ValueError, match="always fails"):
            await with_retry(
                mock_func,
                max_retries=2,
                retryable_exceptions=(ValueError,)
            )

    # Called once initially + 2 retries = 3 total
    assert mock_func.call_count == 3


@pytest.mark.asyncio
async def test_retry_does_not_retry_non_retryable_exception():
    """Non-retryable exceptions should raise immediately without retry."""
    mock_func = AsyncMock(side_effect=KeyError("bad key"))

    with pytest.raises(KeyError):
        await with_retry(
            mock_func,
            max_retries=3,
            retryable_exceptions=(ValueError,)  # KeyError not in this list
        )

    # Should only be called once — no retries
    assert mock_func.call_count == 1
