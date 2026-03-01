# EMR NER API

Django REST API for:
- user registration/login
- entity extraction from EMR text (`/api/predict/`)
- PII masking with label placeholders (`/api/mask/`)

## Installation

1. Create and activate virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Start server:
```bash
python manage.py runserver
```

Base URL: `http://localhost:8000/api/`

## Quick Browser Test

Open:
- `http://localhost:8000/api/`
- `http://localhost:8000/api/health/`
- `http://localhost:8000/api/register/`
- `http://localhost:8000/api/login/`
- `http://localhost:8000/api/predict/`
- `http://localhost:8000/api/mask/`

Authentication is currently disabled globally, so predict and mask can be called directly.

## Streamlit Client

Run:
```bash
source .venv/bin/activate
streamlit run streamlit_app.py
```

Open `http://localhost:8501` and use the app tabs for register/login/predict/mask.

## PII Model Evaluation

Use `evaluate_pii_model.py` to benchmark `urchade/gliner_multi_pii-v1` on the dataset at `pii_dataset/ai_data.csv`.

Run on a sample:
```bash
source .venv/bin/activate
python evaluate_pii_model.py --csv pii_dataset/ai_data.csv --max-rows 100 --threshold 0.5
```

Run full evaluation and save report:
```bash
python evaluate_pii_model.py --csv pii_dataset/ai_data.csv --threshold 0.5 --output-json pii_eval_metrics.json
```

Important output fields:
- `overall_micro`: global precision/recall/F1 across all labels.
- `per_label`: TP/FP/FN and precision/recall/F1 for each entity type.
- `canonical_label_map`: dataset-label to model-label mapping used during inference.

## API Endpoints

### `POST /api/register/`
Create user account.

Request:
```json
{
  "username": "demo",
  "password": "demo123"
}
```

Success:
```json
{
  "message": "User registered successfully"
}
```

### `POST /api/login/`
Login and get token (token is optional currently because auth is disabled).

Request:
```json
{
  "username": "demo",
  "password": "demo123"
}
```

Success:
```json
{
  "token": "generated_token_here"
}
```

### `POST /api/predict/`
Extract entities from text for provided labels.

Request:
```json
{
  "text": "Mrs. Aruna Gupta, age 60, was admitted on 01/11/2024 for chest pain and was treated with 325 mg of Aspirin. Further testing confirmed mild myocardial infarction.",
  "labels": ["patient name", "age", "disease", "dosage", "symptoms"]
}
```

Success:
```json
{
  "entities": [
    {"text": "Mrs. Aruna Gupta", "label": "patient name"},
    {"text": "60", "label": "age"},
    {"text": "325 mg", "label": "dosage"},
    {"text": "mild myocardial infarction", "label": "disease"}
  ]
}
```

### `POST /api/mask/`
Uses the same input format as `/api/predict/`. It runs prediction internally and returns redacted text where detected entities are replaced by placeholders using label names.

Request:
```json
{
  "text": "Mrs. Aruna Gupta, age 60, was admitted on 01/11/2024 for chest pain and was treated with 325 mg of Aspirin.",
  "labels": ["patient name", "age", "dosage", "symptoms"]
}
```

Success:
```json
{
  "entities": [
    {"text": "Mrs. Aruna Gupta", "label": "patient name"},
    {"text": "60", "label": "age"},
    {"text": "325 mg", "label": "dosage"}
  ],
  "masked_text": "[patient name], age [age], was admitted on 01/11/2024 for chest pain and was treated with [dosage] of Aspirin.",
  "masked_entities_count": 3
}
```

### `GET /api/health/`
Health probe endpoint.

## Error Handling

- `400 Bad Request`: invalid payload/validation errors.
- `500 Internal Server Error`: inference or unexpected server failures.

## Logging

Application logs are written to `ner_model.log`.
