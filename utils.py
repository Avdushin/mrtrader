import mplfinance as mpf
import pandas as pd
import numpy as np
import os
import matplotlib
matplotlib.use('Agg')

def create_financial_chart(ticker_symbol, data):
    # Ensure the 'charts' directory exists
    charts_dir = 'charts'
    if not os.path.exists(charts_dir):
        os.makedirs(charts_dir)

    # Define the path for saving the chart
    save_path = os.path.join(charts_dir, f"{ticker_symbol}_2hr_chart.png")

    # Filter data for the last two hours
    now = pd.Timestamp.now()
    two_hours_ago = now - pd.Timedelta(hours=2)
    last_two_hours = data.loc[two_hours_ago:now]

    # Configure plot style
    mc = mpf.make_marketcolors(up='r', down='g', inherit=True)
    s = mpf.make_mpf_style(base_mpl_style='ggplot', marketcolors=mc)
    
    # Add Bollinger Bands as an additional indicator
    bollinger = mpf.make_addplot(last_two_hours[['upper', 'middle', 'lower']], type='line')
    
    # Plot and save the financial chart
    mpf.plot(last_two_hours, type='candle', mav=(3, 6, 9), volume=True, addplot=bollinger,
             style=s, title=f"{ticker_symbol} - Last 2 Hours",
             ylabel='Price ($)', ylabel_lower='Volume', show_nontrading=True,
             savefig=save_path)

    return save_path

def fetch_financial_data(ticker_symbol, exchange):
    # Creating a sample time series data
    rng = pd.date_range(end=pd.Timestamp.now(), periods=240, freq='min')
    df = pd.DataFrame({
        'Open': np.random.uniform(900, 905, size=240),
        'Close': np.random.uniform(900, 905, size=240),
    }, index=rng)

    # Adjusted calculation for High and Low
    price_range = np.abs(df['Close'] - df['Open'])
    spread = np.random.uniform(0.1, 1.0, size=240) * price_range  # Scale spread relative to price range
    spread = np.minimum(spread, 3)  # Cap the spread to a maximum of 3 to prevent very long wicks
    df['High'] = np.maximum(df['Open'], df['Close']) + spread  # Slightly higher than max(Open, Close)
    df['Low'] = np.minimum(df['Open'], df['Close']) - spread   # Slightly lower than min(Open, Close)
    df['Volume'] = np.random.randint(500, 1500, size=240)

    # Bollinger Bands calculation
    df['middle'] = df['Close'].rolling(window=20).mean()
    df['std'] = df['Close'].rolling(window=20).std()
    df['upper'] = df['middle'] + (df['std'] * 2)
    df['lower'] = df['middle'] - (df['std'] * 2)

    return df



# def fetch_financial_data(ticker_symbol, exchange):
#     # Генерация временного диапазона для последних 4 часов с интервалом в 1 минуту
#     rng = pd.date_range(end=pd.Timestamp.now(), periods=240, freq='min')
#     # Генерация тестовых данных
#     df = pd.DataFrame({
#         'Open': np.random.uniform(100, 105, size=240),
#         'High': np.random.uniform(105, 110, size=240),
#         'Low': np.random.uniform(95, 100, size=240),
#         'Close': np.random.uniform(100, 105, size=240),
#         'Volume': np.random.randint(100, 1000, size=240)
#     }, index=rng)
#     return df

# import mplfinance as mpf
# import pandas as pd

# def create_chart(ticker_symbol, data):
#     # Фильтрация данных до последних двух часов, предполагаем что данные уже включают этот интервал
#     last_two_hours = data.last('2H')
    
#     # Настройка стилей для имитации TradingView
#     mc = mpf.make_marketcolors(
#         up='#53b987',  # цвет для роста, светло-зеленый
#         down='#eb4d5c',  # цвет для падения, светло-красный
#         wick={'up':'#53b987', 'down':'#eb4d5c'},
#         volume='gray',
#         ohlc='i'
#     )
#     s = mpf.make_mpf_style(
#         base_mpl_style='seaborn', 
#         marketcolors=mc,
#         mavcolors=["#e0e0e0", "#c0c0c0", "#a0a0a0"],
#         y_on_right=True
#     )
    
#     # Добавление скользящих средних
#     mav = (7, 14, 21)
    
#     # Создание и сохранение графика
#     save_path = f"{ticker_symbol}_2hr_chart.png"
#     mpf.plot(
#         last_two_hours,
#         type='candle', 
#         mav=mav,
#         volume=True,
#         style=s,
#         title=f"{ticker_symbol} Last 2 Hours",
#         savefig=save_path
#     )
#     return save_path


# import requests


# def fetch_data(ticker_symbol, exchange):
#     # Example API endpoint (this is a placeholder, replace with actual API details)
#     url = f"https://api.exchange.com/data?symbol={ticker_symbol}&interval=1m&limit=120"
#     response = requests.get(url)
#     data = response.json()

#     # Converting data to DataFrame
#     df = pd.DataFrame(data, columns=['open', 'high', 'low', 'close', 'volume'])
#     df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
#     df.set_index('datetime', inplace=True)

#     # Convert column data types
#     df = df.astype({'open': 'float', 'high': 'float', 'low': 'float', 'close': 'float', 'volume': 'float'})

#     return df


# import mplfinance as mpf
# import pandas as pd

# def fetch_financial_data(ticker_symbol, exchange):
#     # Placeholder function to demonstrate concept
#     # Fetch real-time financial data from API
#     # This should return a DataFrame with DateTime index and 'Open', 'High', 'Low', 'Close', 'Volume'
#     # Example:
#     data = {
#         'Open': [100, 101, 102],
#         'High': [103, 104, 105],
#         'Low': [99, 98, 97],
#         'Close': [102, 103, 101],
#         'Volume': [1000, 1500, 1200]
#     }
#     dates = pd.date_range(end=pd.Timestamp.now(), periods=3, freq='H')
#     df = pd.DataFrame(data, index=dates)
#     return df

# def create_chart(ticker_symbol, data):
#     # Generate a candlestick chart for the last 2 hours
#     last_two_hours = data.last('2H')  # Assuming data frequency covers this range
#     mc = mpf.make_marketcolors(up='#00ff00', down='#ff0000', inherit=True)
#     s = mpf.make_mpf_style(base_mpf_style='nightclouds', marketcolors=mc)
#     output_path = f"{ticker_symbol}_chart.png"
#     mpf.plot(last_two_hours, type='candle', style=s, title=f'{ticker_symbol} Last 2 Hours',
#              volume=True, savefig=output_path)
#     return output_path

# import mplfinance as mpf
# import numpy as np
# import pandas as pd

# def create_chart(ticker_symbol, data):
#     # Assuming 'data' is a DataFrame with 'Datetime' as the index and OHLCV columns
#     # Here you need to filter the last 2 hours of data
#     last_two_hours = data.last('2H')  # This works if your index is datetime and data is frequent

#     # Define market colors and style
#     mc = mpf.make_marketcolors(up='#00ff00', down='#ff0000', inherit=True)
#     s = mpf.make_mpf_style(base_mpf_style='nightclouds', marketcolors=mc)

#     # Plotting the candlestick chart
#     mpf.plot(last_two_hours, type='candle', style=s, title=f'{ticker_symbol} Last 2 Hours',
#              volume=True, savefig=f'{ticker_symbol}_chart.png')

#     return f'{ticker_symbol}_chart.png'


# import matplotlib.pyplot as plt
# import matplotlib.dates as mdates
# import numpy as np

# def create_chart(ticker_symbol):
#     # Example setup for plotting; replace np.random.randn with actual data fetching
#     np.random.seed(0)
#     dates = np.array([np.datetime64('2020-01-01') + np.timedelta64(i, 'D') for i in range(100)])
#     data = np.random.randn(100).cumsum()

#     plt.figure(figsize=(10, 5))
#     ax = plt.gca()  # Get current axis

#     # Setting the background color
#     ax.set_facecolor('#131722')  # Dark theme background similar to TradingView
#     plt.grid(color='gray', linestyle='--', linewidth=0.5, alpha=0.5)  # Grid lines

#     # Plotting the data
#     plt.plot(dates, data, label=f'Data for {ticker_symbol}', color='#1f77b4')  # Blue line

#     # Setting title and labels with increased font sizes
#     plt.title(f'Stock Data for {ticker_symbol}', color='white', fontsize=14)
#     plt.xlabel('Time', color='white', fontsize=12)
#     plt.ylabel('Price', color='white', fontsize=12)

#     # Setting the tick labels color
#     plt.xticks(color='white', fontsize=10)
#     plt.yticks(color='white', fontsize=10)

#     # Date formatting
#     plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=10))  # Show a tick every 10 days
#     plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
#     plt.gcf().autofmt_xdate()  # Rotate date labels

#     plt.legend()

#     output_path = f"{ticker_symbol}_chart.png"
#     plt.savefig(output_path, facecolor=ax.get_facecolor())  # Save with the figure's background color
#     plt.close()
#     return output_path


# import imgkit
# import os

# def capture_trading_view_chart(ticker_symbol):
#     url = f"https://www.tradingview.com/symbols/{ticker_symbol}/"
#     output_path = f"{ticker_symbol}_chart.jpg"
#     options = {
#         'format': 'jpg',
#         'crop-h': '700',
#         'crop-w': '700',
#         'crop-x': '3',
#         'crop-y': '3',
#         'encoding': "UTF-8",
#         'quality': '94'  # Ensure this is within the valid range if modified
#     }

#     # Specify the full path to the wkhtmltoimage executable
#     config = imgkit.config(wkhtmltoimage=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltoimage.exe')

#     # Use the custom config when calling imgkit
#     imgkit.from_url(url, output_path, options=options, config=config)
#     return output_path



# import imgkit
# import os

# def capture_trading_view_chart(ticker_symbol):
#     url = f"https://www.tradingview.com/symbols/{ticker_symbol}/"
#     output_path = f"{ticker_symbol}_chart.jpg"
#     options = {
#         'format': 'jpg',
#         'crop-h': '700',
#         'crop-w': '700',
#         'crop-x': '3',
#         'crop-y': '3',
#         'encoding': "UTF-8",
#         'custom-header': [
#             ('Accept-Encoding', 'gzip')
#         ],
#         'no-outline': None
#     }
#     # Генерация скриншота с TradingView
#     imgkit.from_url(url, output_path, options=options)
#     return output_path


# Selebium editioin
# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.common.by import By
# import time

# def capture_trading_view_chart(ticker_symbol):
#     chrome_options = Options()
#     chrome_options.add_argument("--headless")
#     chrome_options.add_argument("--window-size=1920x1080")
#     driver_path = '/path/to/your/chromedriver'  # Путь к драйверу
#     driver = webdriver.Chrome(options=chrome_options, executable_path=driver_path)
#     url = f"https://www.tradingview.com/chart/?symbol={ticker_symbol}"

#     try:
#         driver.get(url)
#         time.sleep(10)  # Подождите, чтобы график полностью загрузился
#         chart = driver.find_element(By.CLASS_NAME, "chart-container")
#         screenshot_path = f"{ticker_symbol}_chart.png"
#         chart.screenshot(screenshot_path)
#         return screenshot_path
#     finally:
#         driver.quit()
