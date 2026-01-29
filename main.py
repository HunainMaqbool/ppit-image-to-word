import sys
from pathlib import Path

import numpy as np
import pytesseract
from PIL import Image


def run_ocr(image_path):
    image_path = Path(image_path)
    if not image_path.is_file():
        raise FileNotFoundError(f"Image not found: {image_path}")

    pil_image = Image.open(image_path)

    gray = pil_image.convert("L")
    gray_np = np.array(gray)
    threshold = gray_np.mean()
    binary_np = (gray_np > threshold) * 255
    binary = Image.fromarray(binary_np.astype("uint8"))

    text = pytesseract.image_to_string(binary, lang="eng")
    return text


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <image_path>")
        print("Example: python main.py imgs/sample4.jpg")
        sys.exit(1)

    image_path = sys.argv[1]
    text = run_ocr(image_path)

    output_path = Path("output.txt")
    output_path.write_text(text, encoding="utf-8")

    print(f"OCR complete. Text saved to {output_path}")


if __name__ == "__main__":
    main()
