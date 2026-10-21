import base64
import io
import json
import re

import fitz
import pandas as pd
import streamlit as st
from openai import OpenAI
from PIL import Image, ImageOps

st.set_page_config(page_title="Telecom AI Inspector", page_icon="📡", layout="wide")
st.title("📡 Telecom AI Inspector")
st.caption("Photo and PDF inspection using your Qwen-compatible vision API")

PROMPT = '''You are a cautious telecom site inspection assistant. Examine the image only for visibly supported findings related to RAN, Transmission, Power, DG, Batteries, Tower, Civil, Safety, Housekeeping. Never invent missing parts or faults that cannot be seen. If an image is distant or unclear, say Needs Verification. Do not assume torque, voltage, grounding continuity or internal equipment condition from appearance. Separate no-impact housekeeping observations from actionable defects. Return ONLY a JSON object with a 'findings' array; each finding has category, observation, severity (Critical/Major/Minor/No Impact/Needs Verification), corrective_action, confidence (High/Medium/Low). Critical is reserved for clearly visible imminent danger. If no reliable finding, return {"findings": []}.'''

def secret(name, default=""):
    return st.secrets.get(name, default)

with st.sidebar:
    st.header("API Configuration")
    base_url = st.text_input("OpenAI-compatible API base URL", value=secret("QWEN_BASE_URL"))
    model = st.text_input("Vision model ID", value=secret("QWEN_MODEL", "qwen-vl-max"))
    api_key = secret("QWEN_API_KEY")
    if not api_key:
        api_key = st.text_input("API key (session only)", type="password")
    st.info("Configure permanent credentials in Streamlit Cloud Secrets, not in GitHub.")

site_id = st.text_input("Site ID", placeholder="BAG0906")
files = st.file_uploader("Upload images or PDF reports", type=["jpg", "jpeg", "png", "webp", "pdf"], accept_multiple_files=True)
max_pages = st.number_input("Maximum PDF pages per file", 1, 30, 10)


def as_jpeg(image):
    image = ImageOps.exif_transpose(image).convert("RGB")
    image.thumbnail((1600, 1600))
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()


def extract_images(upload):
    data = upload.getvalue()
    if upload.name.lower().endswith(".pdf"):
        doc = fitz.open(stream=data, filetype="pdf")
        try:
            for page_num in range(min(len(doc), int(max_pages))):
                pix = doc[page_num].get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
                yield f"{upload.name} page {page_num + 1}", Image.open(io.BytesIO(pix.tobytes("png")))
        finally:
            doc.close()
    else:
        yield upload.name, Image.open(io.BytesIO(data))


def parse_result(raw):
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.I)
    data = json.loads(raw)
    if not isinstance(data, dict) or not isinstance(data.get("findings"), list):
        raise ValueError("Model response is not a findings JSON object")
    return data["findings"]

if st.button("Analyze site", type="primary"):
    if not (base_url and model and api_key and files):
        st.error("Provide the API configuration and at least one file.")
    elif not base_url.startswith("https://"):
        st.error("Use an HTTPS API base URL.")
    else:
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=120.0, max_retries=1)
        rows = []
        for upload in files:
            try:
                for source, image in extract_images(upload):
                    with st.spinner(f"Analyzing {source}..."):
                        b64 = as_jpeg(image)
                        response = client.chat.completions.create(
                            model=model,
                            messages=[{"role": "user", "content": [
                                {"type": "text", "text": PROMPT},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                            ]}],
                            temperature=0,
                        )
                        raw = response.choices[0].message.content or ""
                        for finding in parse_result(raw):
                            if not isinstance(finding, dict):
                                continue
                            rows.append({"Site ID": site_id, "Source": source,
                                         **{key: str(finding.get(key, "")) for key in
                                            ("category", "observation", "severity", "corrective_action", "confidence")}})
            except Exception as exc:
                st.error(f"Could not process {upload.name}: {exc}")
        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="Inspection", index=False)
            st.download_button("Download Excel report", buffer.getvalue(), file_name=f"{site_id or 'site'}_inspection.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.info("No findings returned. Check any errors above and verify images manually.")

st.warning("AI observations are preliminary. A qualified technician must verify defects and safety-critical conclusions on site.")
