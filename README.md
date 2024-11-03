
# EMR NER Inference API Documentation for User Management and Prediction Service

This project provides a RESTful API for user registration, login, and entity prediction. The API is designed to manage user accounts and perform predictions for EMR (Electronic Medical Records) on input text based on specified labels.

## Table of Contents

- [Installation](#installation)
- [API Endpoints](#api-endpoints)
  - [User Registration API](#user-registration-api)
  - [User Login API](#user-login-api)
  - [Prediction API](#prediction-api)
- [Error Handling](#error-handling)
- [Logging](#logging)

## Installation

To set up the project, follow these steps:


1. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the development server:
   ```bash
   python manage.py runserver
   ```

The API will be available at `http://localhost:8000/api/`.

## API Endpoints

### User Registration API

**Endpoint:**  
`POST /api/register/`

**Description:**  
This endpoint allows users to register by providing a username and password.

**Request Parameters:**

| Parameter | Type   | Required | Description                          |
|-----------|--------|----------|--------------------------------------|
| username  | string | Yes      | The desired username for the new user. |
| password  | string | Yes      | The desired password for the new user. |

**Responses:**

- **201 Created**  
  ```json
  {
      "message": "User registered successfully"
  }
  ```

- **400 Bad Request**  
  ```json
  {
      "error": "Username and password are required"
  }
  ```

- **400 Bad Request**  
  ```json
  {
      "error": "User already registered"
  }
  ```

- **500 Internal Server Error**  
  ```json
  {
      "error": "An error occurred during registration"
  }
  ```

---

### User Login API

**Endpoint:**  
`POST /api/login/`

**Description:**  
This endpoint allows users to log in by providing their username and password.

**Request Parameters:**

| Parameter | Type   | Required | Description                        |
|-----------|--------|----------|------------------------------------|
| username  | string | Yes      | The username of the user.         |
| password  | string | Yes      | The password of the user.         |

**Responses:**

- **200 OK**  
  ```json
  {
      "token": "generated_token_here"
  }
  ```

- **400 Bad Request**  
  ```json
  {
      "error": "Invalid credentials"
  }
  ```

- **500 Internal Server Error**  
  ```json
  {
      "error": "An error occurred during login"
  }
  ```

---

### Prediction API

**Endpoint:**  
`POST /api/predict/`

**Description:**  
This endpoint accepts input text and labels to perform entity prediction.

**Request Parameters:**

| Parameter | Type   | Required | Description                         |
|-----------|--------|----------|-------------------------------------|
| text      | string | Yes      | The input text for prediction.      |
| labels    | array  | Yes      | A list of labels for prediction.    |

  ```json

  "text": "Mrs. Aruna Gupta, age 60, was admitted on 01/11/2024 for chest pain and was treated with 325 mg of Aspirin. Further testing confirmed mild myocardial infarction.",

  "labels": ["patient name","age","disease","Dosage","Symtoms"]

  ```

**Responses:**

- **200 OK**  
  ```json
    "entities": [
        {
            "text": "Mrs. Aruna Gupta",
            "label": "patient name"
        },
        {
            "text": "age 60",
            "label": "age"
        },
        {
            "text": "325 mg",
            "label": "Dosage"
        },
        {
            "text": "mild myocardial infarction",
            "label": "disease"
        }
    ]
  ```

- **400 Bad Request**  
  ```json
  {
      "error": "Validation errors"
  }
  ```

- **500 Internal Server Error**  
  ```json
  {
      "error": "Prediction failed"
  }
  ```

## Error Handling

The API provides meaningful error messages to help clients understand what went wrong during requests. Standard HTTP status codes are used to indicate the outcome of the requests.

## Logging

The API includes logging functionality that tracks significant events and errors. Logs are written to a file (`ner_model.log`) and include timestamps, log levels, and the source module for better traceability.


---

**Author:** Viraj Yadav

