def compare_metric(value1, value2, higher_is_better=True):
    if value1 == value2:
        return "Tie"

    if higher_is_better:
        return "Primary Venue" if value1 > value2 else "Comparison Venue"
    else:
        return "Primary Venue" if value1 < value2 else "Comparison Venue"