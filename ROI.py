# Calculate ROI
def calculate_roi(entry_point, take_profit, stop_loss, current_rate):
    if current_rate >= take_profit:
        return round((take_profit - entry_point) / entry_point * 100, 2)
    elif current_rate <= stop_loss:
        return round((stop_loss - entry_point) / entry_point * 100, 2)
    return 0
