from statistics import fmean


def sma(values: list[float], period: int) -> float | None:
    if len(values) < period or period <= 0:
        return None
    return fmean(values[-period:])


def ema(values: list[float], period: int) -> float | None:
    if len(values) < period or period <= 0:
        return None
    result = fmean(values[:period])
    multiplier = 2 / (period + 1)
    for value in values[period:]:
        result = (value - result) * multiplier + result
    return result


def macd(values: list[float]) -> dict[str, float | None]:
    """Return the latest MACD values without requiring a third-party library."""
    fast = ema(values, 12)
    slow = ema(values, 26)
    if fast is None or slow is None:
        return {"dif": None, "dea": None, "histogram": None}
    diffs = []
    for index in range(25, len(values)):
        fast_value = ema(values[: index + 1], 12)
        slow_value = ema(values[: index + 1], 26)
        if fast_value is not None and slow_value is not None:
            diffs.append(fast_value - slow_value)
    dea = ema(diffs, 9)
    histogram = (diffs[-1] - dea) * 2 if diffs and dea is not None else None
    return {"dif": diffs[-1] if diffs else None, "dea": dea, "histogram": histogram}


def rsi(values: list[float], period: int = 14) -> float | None:
    if len(values) <= period or period <= 0:
        return None
    changes = [values[index] - values[index - 1] for index in range(1, len(values))]
    gains = [max(change, 0) for change in changes]
    losses = [max(-change, 0) for change in changes]
    average_gain = fmean(gains[-period:])
    average_loss = fmean(losses[-period:])
    if average_loss == 0:
        return 100.0
    return 100 - (100 / (1 + average_gain / average_loss))


def volume_ratio(bars: list[dict], period: int = 20) -> float | None:
    volumes = [float(bar.get("volume") or 0) for bar in bars]
    if len(volumes) <= period:
        return None
    baseline = fmean(volumes[-period - 1:-1])
    return volumes[-1] / baseline if baseline > 0 else None


def summarize_bars(bars: list[dict]) -> dict[str, float | int | None]:
    """Compute deliberately small, explainable metrics from stored minute bars."""
    if not bars:
        return {"samples": 0, "last_price": None, "sma_5": None, "sma_20": None, "amount_ratio": None}
    prices = [float(bar["price"]) for bar in bars]
    amounts = [float(bar["amount"]) for bar in bars]
    sma_5 = fmean(prices[-5:]) if len(prices) >= 5 else None
    sma_20 = fmean(prices[-20:]) if len(prices) >= 20 else None
    amount_ratio = None
    if len(amounts) >= 6:
        baseline = fmean(amounts[-6:-1])
        amount_ratio = round(amounts[-1] / baseline, 2) if baseline > 0 else None
    return {
        "samples": len(bars),
        "last_price": prices[-1],
        "sma_5": round(sma_5, 2) if sma_5 is not None else None,
        "sma_20": round(sma_20, 2) if sma_20 is not None else None,
        "amount_ratio": amount_ratio,
    }


def summarize_daily_bars(bars: list[dict]) -> dict[str, float | int | None | str]:
    if not bars:
        return {"samples": 0, "last_close": None, "sma_5": None, "sma_20": None, "sma_60": None, "trend": "insufficient"}
    closes = [float(bar["close"]) for bar in bars]
    sma_5 = fmean(closes[-5:]) if len(closes) >= 5 else None
    sma_20 = fmean(closes[-20:]) if len(closes) >= 20 else None
    sma_60 = fmean(closes[-60:]) if len(closes) >= 60 else None
    trend = "insufficient"
    if sma_5 is not None and sma_20 is not None:
        trend = "up" if closes[-1] > sma_5 > sma_20 else "down" if closes[-1] < sma_5 < sma_20 else "neutral"
    return {
        "samples": len(bars),
        "last_close": closes[-1],
        "sma_5": round(sma_5, 2) if sma_5 is not None else None,
        "sma_20": round(sma_20, 2) if sma_20 is not None else None,
        "sma_60": round(sma_60, 2) if sma_60 is not None else None,
        "trend": trend,
    }
