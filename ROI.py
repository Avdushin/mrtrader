from decimal import Decimal, getcontext

# Установка точности для вычислений с Decimal
getcontext().prec = 28

def calculate_roi(entry_point, take_profit, stop_loss, current_rate):
    # Преобразование всех входных данных в Decimal
    entry_point = Decimal(entry_point)
    take_profit = Decimal(take_profit)
    stop_loss = Decimal(stop_loss)
    current_rate = Decimal(current_rate)
    
    # Вычисление ROI
    if current_rate >= take_profit:
        roi = (take_profit - entry_point) / entry_point * Decimal(100)
        return round(roi, 2)
    elif current_rate <= stop_loss:
        roi = (stop_loss - entry_point) / entry_point * Decimal(100)
        return round(roi, 2)
    return Decimal(0)
