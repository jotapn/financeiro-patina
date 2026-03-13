import re
from datetime import datetime
from decimal import Decimal

import pytesseract
from PIL import Image, ImageEnhance, ImageOps


def extract_receipt_data(image_path: str) -> dict:
    image = Image.open(image_path)
    image = ImageOps.grayscale(image)
    image = ImageEnhance.Contrast(image).enhance(1.8)
    raw_text = pytesseract.image_to_string(image, lang='por')
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

    amount_match = re.search(r'(?:R\$\s*|TOTAL[:\s]*)?(\d{1,3}(?:\.\d{3})*,\d{2})', raw_text, re.IGNORECASE)
    date_match = re.search(r'(\d{2}/\d{2}/\d{2,4})', raw_text)
    description = next((line for line in lines if not re.fullmatch(r'[\d\W]+', line)), '')

    amount = None
    if amount_match:
        amount = Decimal(amount_match.group(1).replace('.', '').replace(',', '.'))

    parsed_date = None
    if date_match:
        raw_date = date_match.group(1)
        for fmt in ('%d/%m/%Y', '%d/%m/%y'):
            try:
                parsed_date = datetime.strptime(raw_date, fmt).date()
                break
            except ValueError:
                continue

    return {'amount': float(amount) if amount is not None else None, 'date': parsed_date.isoformat() if parsed_date else None, 'description': description, 'raw_text': raw_text}
