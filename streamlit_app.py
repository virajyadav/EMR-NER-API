import json
from typing import Any

import requests
import streamlit as st


st.set_page_config(page_title="EMR NER API Client", page_icon="🩺", layout="wide")


def build_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def show_response(response: requests.Response) -> None:
    st.caption(f"Status: {response.status_code}")
    try:
        payload: Any = response.json()
        st.json(payload)
    except ValueError:
        st.code(response.text)


def safe_post(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> None:
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        show_response(response)
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        st.error(f"Request failed: {exc}")


st.title("EMR NER API Browser Client")
st.write("Use this Streamlit app to call the Django endpoints for register, login, predict, mask, and health.")

if "last_predict_text" not in st.session_state:
    st.session_state.last_predict_text = ""
if "last_predict_entities" not in st.session_state:
    st.session_state.last_predict_entities = []

with st.sidebar:
    st.header("Connection")
    base_url = st.text_input("API base URL", value="http://localhost:8000/api")

    st.divider()
    if st.button("Check Health", use_container_width=True):
        try:
            response = requests.get(build_url(base_url, "health/"), timeout=30)
            st.caption(f"Status: {response.status_code}")
            st.code(response.text)
        except requests.exceptions.RequestException as exc:
            st.error(f"Health check failed: {exc}")


tab_register, tab_login, tab_predict, tab_mask = st.tabs(["Register", "Login", "Predict", "Mask PII"])

with tab_register:
    st.subheader("Register User")
    with st.form("register_form"):
        username = st.text_input("Username", key="register_username")
        password = st.text_input("Password", type="password", key="register_password")
        submitted = st.form_submit_button("Register")

    if submitted:
        safe_post(
            build_url(base_url, "register/"),
            {"username": username, "password": password},
        )

with tab_login:
    st.subheader("Login User")
    with st.form("login_form"):
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        submitted = st.form_submit_button("Login")

    if submitted:
        try:
            response = requests.post(
                build_url(base_url, "login/"),
                json={"username": username, "password": password},
                timeout=60,
            )
            show_response(response)
        except requests.exceptions.RequestException as exc:
            st.error(f"Request failed: {exc}")

with tab_predict:
    st.subheader("NER Prediction")
    st.caption("Provide input text and labels. Labels can be comma-separated or one label per line.")
    with st.form("predict_form"):
        text = st.text_area(
            "Input Text",
            value="Mrs. Aruna Gupta, age 60, was admitted on 01/11/2024 for chest pain and treated with 325 mg of Aspirin.",
            height=160,
        )
        labels_raw = st.text_area(
            "Labels",
            value="patient name,age,disease,dosage,symptoms",
            height=100,
        )
        submitted = st.form_submit_button("Predict")

    if submitted:
        labels = [
            label.strip()
            for part in labels_raw.splitlines()
            for label in part.split(",")
            if label.strip()
        ]
        if not text.strip() or not labels:
            st.error("Both text and at least one label are required.")
        else:
            try:
                response = requests.post(
                    build_url(base_url, "predict/"),
                    json={"text": text, "labels": labels},
                    timeout=60,
                )
                show_response(response)
                if response.ok:
                    payload = response.json()
                    st.session_state.last_predict_text = text
                    st.session_state.last_predict_entities = payload.get("entities", [])
                    st.success("Prediction saved. Open 'Mask PII' tab to mask this output.")
            except requests.exceptions.RequestException as exc:
                st.error(f"Request failed: {exc}")

with tab_mask:
    st.subheader("Mask PII")
    if st.button("Use Last Prediction Output", key="use_last_prediction_output"):
        if st.session_state.last_predict_text and st.session_state.last_predict_entities:
            st.session_state.mask_text = st.session_state.last_predict_text
            st.session_state.mask_labels = ",".join(
                sorted(
                    {entity.get("label", "").strip() for entity in st.session_state.last_predict_entities if entity.get("label")}
                )
            )
            st.success("Loaded latest prediction text/entities.")
        else:
            st.warning("No saved prediction output found.")

    with st.form("mask_form"):
        text = st.text_area(
            "Input Text",
            key="mask_text",
            height=160,
            value=st.session_state.last_predict_text
            or "Mrs. Aruna Gupta, age 60, was treated with 325 mg of Aspirin.",
        )
        labels_raw = st.text_area(
            "PII Labels",
            key="mask_labels",
            height=100,
            value="patient name,age,disease,dosage,symptoms",
        )
        submitted = st.form_submit_button("Mask Text")

    if submitted:
        labels = [
            label.strip()
            for part in labels_raw.splitlines()
            for label in part.split(",")
            if label.strip()
        ]
        if not text.strip() or not labels:
            st.error("Both text and at least one label are required.")
        else:
            safe_post(
                build_url(base_url, "mask/"),
                {"text": text, "labels": labels},
            )


with st.expander("cURL examples"):
    st.code(
        f"""curl -X POST {build_url(base_url, "register/")} \\
  -H "Content-Type: application/json" \\
  -d '{{"username":"demo","password":"demo123"}}'

curl -X POST {build_url(base_url, "login/")} \\
  -H "Content-Type: application/json" \\
  -d '{{"username":"demo","password":"demo123"}}'

curl -X POST {build_url(base_url, "predict/")} \\
  -H "Content-Type: application/json" \\
  -d {json.dumps({"text": "Patient has fever and was given paracetamol 500mg.", "labels": ["disease", "dosage"]})}

curl -X POST {build_url(base_url, "mask/")} \\
  -H "Content-Type: application/json" \\
  -d {json.dumps({"text": "Mrs. Aruna Gupta, age 60, was treated with 325 mg of Aspirin.", "labels": ["patient name", "age", "dosage"]})}
""",
        language="bash",
    )
