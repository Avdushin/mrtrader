# PnL.py
from PIL import Image, ImageDraw, ImageFont
import os

def create_pnl_image(entry_point, result_point, current_rate, image_path, output_path):
    try:
        # Загрузка базового изображения
        base_image = Image.open(image_path).convert("RGBA")
        # Применение эффекта размытия к изображению
        blurred_image = base_image.filter(ImageFilter.GaussianBlur(5))

        # Создание объекта для рисования
        draw = ImageDraw.Draw(blurred_image)
        # Загрузка шрифта
        font = ImageFont.truetype("arial.ttf", 24)  # Укажите путь к файлу шрифта

        # Текст для нанесения на изображение
        text = f"Entry Point: {entry_point}\nResult: {result_point}\nCurrent Rate: {current_rate}"
        text_position = (10, 10)  # Начальная позиция текста

        # Нанесение текста на изображение
        draw.multiline_text(text_position, text, font=font, fill=(255,255,255,255))

        # Сохранение результата в новый файл
        blurred_image.save(output_path, "PNG")
        return output_path
    except Exception as e:
        print(f"Error in create_pnl_image: {str(e)}")
        return None