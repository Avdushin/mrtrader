# from tradingview_ta import TA_Handler, Interval, Exchange

# def get_current_price(ticker_name):
#     handler = TA_Handler(
#         symbol=ticker_name,
#         screener="crypto",  # Может быть изменено в зависимости от рынка: "crypto", "forex", "america"
#         exchange="BINANCE",  # BYBIT, BINANCE
#         interval=Interval.INTERVAL_1_MINUTE
#     )
#     try:
#         analysis = handler.get_analysis()
#         return analysis.indicators["close"]  # Получаем последнюю цену закрытия
#     except Exception as e:
#         print("Ошибка при получении данных с TradingView:", str(e))
#         return None