# Deployment Guide

## Quick Deployment Checklist

### 1. GitHub Setup
- [ ] Initialize git repository: `git init`
- [ ] Create `.gitignore` file (see below)
- [ ] Add all files: `git add .`
- [ ] Commit: `git commit -m "Initial commit"`
- [ ] Create GitHub repository
- [ ] Push code: `git push -u origin main`

### 2. Streamlit Cloud Deployment

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with your GitHub account
3. Click "New app"
4. Fill in:
   - **Repository**: Select your GitHub repo
   - **Branch**: `main` (or `master`)
   - **Main file path**: `app.py`
5. Click "Deploy"
6. Wait for deployment (usually 2-3 minutes)
7. Get your shareable link (e.g., `https://your-app-name.streamlit.app`)

### 3. Important Notes

**Tesseract OCR on Streamlit Cloud:**
- Streamlit Cloud supports system packages via `packages.txt`
- The `packages.txt` file is already created with `tesseract-ocr`
- If Tesseract is not available, you may need to use an alternative OCR service or deploy elsewhere

**Alternative Deployment Options:**

1. **Hugging Face Spaces:**
   - Create a new Space
   - Select "Streamlit" as SDK
   - Upload your code
   - Add `requirements.txt` in the root

2. **Gradio (Alternative UI):**
   - Can convert `app.py` to use Gradio instead
   - Deploy on Hugging Face Spaces with Gradio

3. **Heroku/Railway:**
   - More complex setup
   - Requires `Procfile` and additional configuration

### 4. Testing After Deployment

- [ ] Upload a test image
- [ ] Verify OCR extraction works
- [ ] Download and verify .docx file opens correctly
- [ ] Test with different image formats (JPG, PNG)
- [ ] Share link with team/instructor

### 5. Submission

- [ ] Working app link (share via WhatsApp)
- [ ] GitHub repository link
- [ ] Project report (submit on GCR)
