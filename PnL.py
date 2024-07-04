# PnL.py
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from ROI import calculate_roi
import os
from datetime import datetime

def create_pnl_image(ticker_name, entry_point, result_point, current_rate, image_path, output_path, direction, leverage='10x'):
    # light_green = (152, 251, 152)  # Pale Green
    light_green = (54, 209, 116)
    vivid_red = (209, 54, 83)

    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        base_image = Image.open(image_path).convert("RGBA")
        blurred_image = base_image.filter(ImageFilter.GaussianBlur(10))
        draw = ImageDraw.Draw(blurred_image)

        font_size = 30
        font = ImageFont.truetype("arialbd.ttf", font_size)
        roi = calculate_roi(entry_point, result_point, result_point, current_rate)
        # roi_color = "green" if roi >= 0 else "red"
        roi_color = light_green if roi >= 0 else vivid_red
        direction_color = "green" if direction.upper() == "LONG" else "red"
        current_time = datetime.now().strftime("%d/%m/%Y - %H:%M MSK")

        margin_left = 30  # Margin from the left side for text alignment
        initial_y_offset = blurred_image.height * 0.68  # Position text towards the bottom
        text_y = initial_y_offset
        spacing = 40  # Space between lines

        # Apply a tint based on ROI
        tint_alpha = 6  # Approximately 30% transparency (255 * 0.3)
        tint_color = (0, 255, 0, tint_alpha) if roi >= 0 else (255, 0, 0, tint_alpha)
        overlay = Image.new('RGBA', blurred_image.size, tint_color)
        blended_image = Image.alpha_composite(blurred_image, overlay)

        draw = ImageDraw.Draw(blended_image)  # Update draw to draw on the tinted image

        # Draw the header with directional color as parts
        header_parts = [
            (f"{ticker_name} | ", "white"),
            (f"{direction.upper()}", direction_color),
            (f" | {leverage}", "white")
        ]

        # Iterate through header parts to draw them in sequence, left-aligned
        header_x = margin_left
        for part, color in header_parts:
            draw.text((header_x, text_y), part, font=font, fill=color)
            header_x += font.getbbox(part)[2]  # Advance text position to end of current part

        text_y += spacing  # Increment y for the next detail

        # Draw ROI with label in white and value in specific color
        roi_label = "ROI: "
        roi_value = f"{roi:.2f}%"
        draw.text((margin_left, text_y), roi_label, font=font, fill="white")
        roi_label_width = font.getbbox(roi_label)[2]
        draw.text((margin_left + roi_label_width, text_y), roi_value, font=font, fill=roi_color)

        text_y += spacing  # Increment y for next detail

        # Draw other details left-aligned
        details = [
            (f"Текущая стоимость: {current_rate:.4f}", "white"),
            (f"Точка входа: {entry_point:.4f}", "white"),
            (current_time, "white")
        ]

        for detail, color in details:
            draw.text((margin_left, text_y), detail, font=font, fill=color)
            text_y += spacing  # Increment y for next detail

        blended_image.save(output_path, "PNG")
        return output_path
    except Exception as e:
        print(f"Error in create_pnl_image: {str(e)}")
        return None
