# PPIT - Image to Word Converter

Basic Image-to-Word Converter (MVP) that extracts text from images using OCR and generates Word documents (.docx). Available as both a CLI tool and a web application.

## Prerequisites

- Python >= 3.13
- [uv](https://github.com/astral-sh/uv) package manager
- Tesseract OCR (system-level installation)

### Installing Tesseract

**macOS (Homebrew):**
```bash
brew install tesseract
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install tesseract-ocr
```

**Windows:**
Download installer from [GitHub Tesseract releases](https://github.com/UB-Mannheim/tesseract/wiki)

## Setup

1. Install project dependencies:
```bash
uv sync
```

2. (Optional) Create virtual environment:
```bash
uv venv
source .venv/bin/activate
```

## Usage

### Web Application (Recommended)

Run the Streamlit web app:

```bash
uv run streamlit run app.py
```

Then open your browser to `http://localhost:8501` and:
1. Upload an image (JPG/PNG)
2. Click "Convert to Word Document"
3. Download the generated .docx file

### Command Line Interface

Run OCR on an image:
```bash
uv run python main.py imgs/sample4.jpg
```

The extracted text will be saved to `output.txt` in the project root.

### Example:
```bash
uv run python main.py imgs/sample4.jpg
cat output.txt
```

## Project Structure

```
PPIT/
├── app.py              # Streamlit web application
├── main.py             # CLI OCR pipeline implementation
├── pyproject.toml      # Project dependencies
├── requirements.txt    # Deployment dependencies (for Streamlit Cloud)
├── uv.lock             # Dependency lock file (auto-generated)
├── PRD.txt             # Project requirements document
├── todolist.txt        # Development task checklist
├── .streamlit/         # Streamlit configuration
│   └── config.toml
├── imgs/               # Sample input images
│   └── sample4.jpg
├── output.txt          # OCR output (generated, overwritten on each run)
└── README.md
```

## Deployment

### Streamlit Cloud (Recommended)

1. **Push your code to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

2. **Deploy on Streamlit Cloud:**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Sign in with GitHub
   - Click "New app"
   - Select your repository and branch
   - Set main file path to `app.py`
   - Click "Deploy"

3. **Note:** Streamlit Cloud will automatically install dependencies from `requirements.txt`. Tesseract OCR needs to be available in the cloud environment (Streamlit Cloud supports system packages via `packages.txt`).

### Local Testing

Before deploying, test locally:
```bash
uv sync
uv run streamlit run app.py
```

## Current Status

- ✅ Basic OCR text extraction working
- ✅ Image preprocessing (grayscale, thresholding)
- ✅ .docx generation implemented
- ✅ Web application (Streamlit) implemented
- ⏳ Formatting detection (bold, italic, alignment, paragraphs) - future enhancement
