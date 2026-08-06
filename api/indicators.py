from statistics import fmean


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
