# AutoTestDesign (Demo)

AI-driven AutoTestDesign demo tool for requirements structuring, risk analysis, black-box test design, interactive review, and export (JSON/Excel).

## 1) Setup

```bash
python -m venv venv
# Windows
venv\Scripts\activate

pip install -r requirements.txt
```

## 2) Configure (Real LLM)

Copy `.env.example` to `.env` and fill in your LLM config:

```bash
copy .env.example .env
```

Environment variables:

- `OPENAI_API_KEY` (required): API key for the OpenAI-SDK-compatible endpoint.
- `OPENAI_BASE_URL` (optional): defaults to `https://ai.dianhuomao.shop/v1`.
- `OPENAI_MODEL` (required): use the exact model string provided by your endpoint.

## 3) Run

```bash
streamlit run app.py
```

## 4) Demo Data

- `data/sample_requirements.csv`
