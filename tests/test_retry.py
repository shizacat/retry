import time
import asyncio
from unittest.mock import MagicMock, create_autospec

import pytest

from retry.api import retry, retry_call, retry_call_async


def get_event_loop():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    except AttributeError:
        # For py3.6
        loop = get_event_loop()
    return loop


def test_retry(monkeypatch):
    mock_sleep_time = [0]

    def mock_sleep(seconds):
        mock_sleep_time[0] += seconds

    monkeypatch.setattr(time, 'sleep', mock_sleep)

    hit = [0]

    tries = 5
    delay = 1
    backoff = 2

    @retry(tries=tries, delay=delay, backoff=backoff)
    def f():
        hit[0] += 1
        1 / 0

    with pytest.raises(ZeroDivisionError):
        f()
    assert hit[0] == tries
    assert mock_sleep_time[0] == sum(
        delay * backoff ** i for i in range(tries - 1))


def test_tries_inf():
    hit = [0]
    target = 10

    @retry(tries=float('inf'))
    def f():
        hit[0] += 1
        if hit[0] == target:
            return target
        else:
            raise ValueError
    assert f() == target


def test_tries_minus1():
    hit = [0]
    target = 10

    @retry(tries=-1)
    def f():
        hit[0] += 1
        if hit[0] == target:
            return target
        else:
            raise ValueError
    assert f() == target


def test_max_delay(monkeypatch):
    mock_sleep_time = [0]

    def mock_sleep(seconds):
        mock_sleep_time[0] += seconds

    monkeypatch.setattr(time, 'sleep', mock_sleep)

    hit = [0]

    tries = 5
    delay = 1
    backoff = 2
    max_delay = delay  # Never increase delay

    @retry(tries=tries, delay=delay, max_delay=max_delay, backoff=backoff)
    def f():
        hit[0] += 1
        1 / 0

    with pytest.raises(ZeroDivisionError):
        f()
    assert hit[0] == tries
    assert mock_sleep_time[0] == delay * (tries - 1)


def test_fixed_jitter(monkeypatch):
    mock_sleep_time = [0]

    def mock_sleep(seconds):
        mock_sleep_time[0] += seconds

    monkeypatch.setattr(time, 'sleep', mock_sleep)

    hit = [0]

    tries = 10
    jitter = 1

    @retry(tries=tries, jitter=jitter)
    def f():
        hit[0] += 1
        1 / 0

    with pytest.raises(ZeroDivisionError):
        f()
    assert hit[0] == tries
    assert mock_sleep_time[0] == sum(range(tries - 1))


def test_retry_call():
    f_mock = MagicMock(side_effect=RuntimeError)
    tries = 2
    try:
        retry_call(f_mock, exceptions=RuntimeError, tries=tries)
    except RuntimeError:
        pass

    assert f_mock.call_count == tries

def test_retry_call_async_01():
    """Call a function"""
    # Definition
    hit = [0]
    async def testf(value=0):
        hit[0] += 1
        if value < 0:
            await asyncio.sleep(0.1)
            return value
        raise RuntimeError
    
    # Run
    loop = get_event_loop()
    result = loop.run_until_complete(
        retry_call_async(testf, fkwargs={"value": -1}, tries=4, delay=0.01)
    )
    assert result == -1
    assert hit[0] == 1


def test_retry_call_2():
    side_effect = [RuntimeError, RuntimeError, 3]
    f_mock = MagicMock(side_effect=side_effect)
    tries = 5
    result = None
    try:
        result = retry_call(f_mock, exceptions=RuntimeError, tries=tries)
    except RuntimeError:
        pass

    assert result == 3
    assert f_mock.call_count == len(side_effect)


def test_retry_call_with_args():

    def f(value=0):
        if value < 0:
            return value
        else:
            raise RuntimeError

    return_value = -1
    result = None
    f_mock = MagicMock(spec=f, return_value=return_value)
    try:
        result = retry_call(f_mock, fargs=[return_value])
    except RuntimeError:
        pass

    assert result == return_value
    assert f_mock.call_count == 1


def test_retry_call_with_kwargs():

    def f(value=0):
        if value < 0:
            return value
        else:
            raise RuntimeError

    kwargs = {'value': -1}
    result = None
    f_mock = MagicMock(spec=f, return_value=kwargs['value'])
    try:
        result = retry_call(f_mock, fkwargs=kwargs)
    except RuntimeError:
        pass

    assert result == kwargs['value']
    assert f_mock.call_count == 1


def test_call_on_async_def():
    hit = [0]

    @retry(tries=4, delay=1)
    async def testf(value=0):
        hit[0] += 1
        if value < 0:
            await asyncio.sleep(0.1)
            return value
        raise RuntimeError

    loop = get_event_loop()

    # === 1
    result = loop.run_until_complete(testf(-1))
    assert result == -1
    assert hit[0] == 1

    # === 2
    try:
        hit = [0]
        result = loop.run_until_complete(testf(1))
    except RuntimeError:
        pass
    assert hit[0] == 4
