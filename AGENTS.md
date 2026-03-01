# Repository Guidelines

## Project Structure & Module Organization
- `nermlops/`: Django project configuration (`settings.py`, `urls.py`, `wsgi.py`, `asgi.py`).
- `nerinference/`: Core API app (views, serializers, routes). Main endpoints live in `views.py`.
- `pii_dataset/`: Evaluation dataset (`ai_data.csv`) used by the PII benchmark script.
- `streamlit_app.py`: Local UI client for register/login/predict/mask flows.
- `evaluate_pii_model.py`: Offline evaluation script for GLiNER PII performance.
- `requirements.txt`: Python dependencies.

## Build, Test, and Development Commands
- Create environment:
  - `python3 -m venv .venv && source .venv/bin/activate`
- Install deps:
  - `pip install -r requirements.txt`
- Run API locally:
  - `python manage.py runserver`
- Django sanity checks:
  - `python manage.py check`
- Run Streamlit client:
  - `streamlit run streamlit_app.py`
- Evaluate PII model:
  - `python evaluate_pii_model.py --csv pii_dataset/ai_data.csv --max-rows 100`

## Coding Style & Naming Conventions
- Use Python 3.10+ and follow PEP 8 (4-space indentation, readable line lengths).
- Keep API serializers in `nerinference/serializers.py` and route wiring in `nerinference/urls.py`.
- Use descriptive names for endpoints and helpers (`MaskPIIView`, `mask_entities_in_text`).
- Prefer explicit error responses (`400` for validation, `500` for unexpected failures).

## Testing Guidelines
- Current baseline uses Django checks and script-based validation.
- Before submitting changes, run:
  - `python manage.py check`
  - `python -m py_compile streamlit_app.py evaluate_pii_model.py`
- Add focused tests in `nerinference/tests.py` for new endpoint behavior.
- Test names should reflect behavior (e.g., `test_mask_returns_label_placeholders`).

## Commit & Pull Request Guidelines
- Follow Conventional Commits:
  - `feat(api): add mask endpoint`
  - `fix(api): correct predict validation status`
  - `docs(readme): update mask usage`
- Keep commits scoped by concern/file group.
- PRs should include:
  - change summary,
  - API contract impact (request/response changes),
  - test/validation evidence (commands + outputs),
  - sample payloads for new endpoints.

## Security & Configuration Tips
- Do not commit secrets/tokens.
- `.gitignore` excludes local artifacts (`.venv/`, `db.sqlite3`, `__pycache__/`, logs).
- Model downloads require network access; cache behavior can affect first-run latency.
