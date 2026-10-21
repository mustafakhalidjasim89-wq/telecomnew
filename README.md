# Telecom AI Inspector

Streamlit app for telecom site image/PDF inspection using an OpenAI-compatible Qwen vision API.

## Deploy to Streamlit Cloud
1. Create a **private** GitHub repository named `telecom-ai-inspector`.
2. Upload `app.py`, `requirements.txt`, `.gitignore`, `README.md` and `.streamlit/secrets.toml.example` (preserve the folder).
3. Open https://share.streamlit.io/ and create an app from your GitHub repository, branch `main`, entrypoint `app.py`.
4. In the Streamlit deployment advanced settings, add secrets:

```toml
QWEN_API_KEY = "YOUR_KEY"
QWEN_BASE_URL = "https://YOUR_PROVIDER_OPENAI_COMPATIBLE_BASE_URL/v1"
QWEN_MODEL = "YOUR_VISION_MODEL_ID"
```

Use the **exact base URL and model ID** supplied by your Qwen API provider. For some providers the base URL does not end in `/v1`. A text-only Qwen model will not work for images.

## Local run
```bash
pip install -r requirements.txt
streamlit run app.py
```

Create `.streamlit/secrets.toml` locally (never commit it) using the same TOML format.

## Notes
- Each uploaded PDF page is rendered as an image, up to the configured cap.
- Every image/page incurs an API request and may incur provider charges.
- Do not upload confidential site data to third-party services without authorization.
- Human verification is required before acting on any observation.
