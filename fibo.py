def fib_levels(high: float, low: float):
    diff = high - low
    return {
        "0.236": low + 0.236*diff,
        "0.382": low + 0.382*diff,
        "0.5": low + 0.5*diff,
        "0.618": low + 0.618*diff,
        "0.786": low + 0.786*diff,
        "1.0": high
    }

def fib_extension(high: float, low: float):
    diff = high - low
    return {
        "1.272": high + 0.272*diff,
        "1.414": high + 0.414*diff,
        "1.618": high + 0.618*diff,
        "2.0": high + 1.0*diff
    }
