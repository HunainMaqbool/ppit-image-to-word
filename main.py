import sys
from pathlib import Path

import cv2
import pytesseract
from PIL import Image


def run_ocr(image_path):
    image_path = Path(image_path)
    if not image_path.is_file():
        raise FileNotFoundError(f"Image not found: {image_path}")

    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"Could not read image: {image_path}")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    pil_image = Image.fromarray(gray)
    text = pytesseract.image_to_string(pil_image, lang="eng")
    return text


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <image_path>")
        print("Example: python main.py imgs/sample1.jpeg")
        sys.exit(1)

    image_path = sys.argv[1]
    text = run_ocr(image_path)

    output_path = Path("output.txt")
    output_path.write_text(text, encoding="utf-8")

    print(f"OCR complete. Text saved to {output_path}")


if __name__ == "__main__":
    main()
