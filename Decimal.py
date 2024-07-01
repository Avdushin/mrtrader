from decimal import Decimal, ROUND_DOWN

# Функция для форматирования значений Decimal
def format_decimal(value, decimal_places='0.00000000'):
    # Указываем желаемое количество десятичных разрядов
    formatter = Decimal('1.' + '0' * decimal_places.count('0'))
    return value.quantize(formatter, rounding=ROUND_DOWN)

# Использование функции в логике обработки цен
current_rate = Decimal("0.000012109999999999999250829309238586262154058204032480716705322265625")
formatted_rate = format_decimal(current_rate)
print(f"Форматированная текущая цена: {formatted_rate}")


# from decimal import Decimal, getcontext

# # Устанавливаем точность Decimal, достаточную для ваших нужд
# getcontext().prec = 28

# def format_decimal(value):
#     # Создаем Decimal из строки для точного представления
#     dec = Decimal(value)
#     # Преобразуем Decimal обратно в строку с динамическим количеством знаков после запятой
#     # Убираем лишние нули и точку, если она не нужна
#     formatted = f"{dec.normalize():f}".rstrip('0').rstrip('.')
#     return formatted

# # Примеры чисел с разным количеством знаков после запятой
# examples = ['0.0000121314', '0.0000121', '0.000012', '1.20000', '2.34']

# for example in examples:
#     print(f"Original: {example}, Formatted: {format_decimal(example)}")
