from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from gliner import GLiNER
from .serializers import TextInputSerializer, MaskPIIInputSerializer
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from prometheus_client import Histogram, Counter
from rest_framework.decorators import permission_classes
import logging
import time
import re

logger = logging.getLogger('nerinference')

inference_latency = Histogram('inference_latency_milliseconds', 'Time taken for a single inference in milliseconds')
inference_throughput = Counter('inference_throughput_total', 'Total number of inferences processed')
entity_frequency = Counter('entity_frequency', 'Frequency of detected entities', ['entity_type'])

model = None


def get_model():
    """
    Lazily load GLiNER once and keep a module-level singleton.
    Passing proxies/resume_download keeps compatibility with newer
    huggingface_hub + current gliner versions.
    """
    global model
    if model is None:
        model = GLiNER.from_pretrained(
            "urchade/gliner_medium-v2.1",
            proxies=None,
            resume_download=False,
        )
    return model


def mask_entities_in_text(text, entities):
    masked_text = text
    sorted_entities = sorted(
        entities,
        key=lambda item: len(item.get("text", "")),
        reverse=True,
    )
    for entity in sorted_entities:
        entity_text = entity.get("text", "").strip()
        entity_label = entity.get("label", "PII").strip()
        if not entity_text:
            continue
        replacement = f"[{entity_label}]"
        masked_text = re.sub(re.escape(entity_text), replacement, masked_text)
    return masked_text

# Registration endpoint

@permission_classes([AllowAny]) 
class RegisterView(APIView):
    """
    View to handle user registration.

    This view allows users to register by providing a username and password.
    It requires the following fields in the request body:
    - username: The desired username for the new user.
    - password: The desired password for the new user.

    Upon a successful registration, the view returns a success message.
    If the username or password is missing, a 400 Bad Request response is returned.
    Any other exceptions are logged and result in a 500 Internal Server Error response.

    Permissions:
        AllowAny: This view is accessible to any user.
    """
    #permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        username = request.data.get("username")
        try:
            password = request.data.get("password")

            if not username or not password:
                return Response({"error": "Username and password are required"}, 
                                status=status.HTTP_400_BAD_REQUEST)

            # Check if the user already exists
            if User.objects.filter(username=username).exists():
                return Response({"error": "User already registered"}, 
                                status=status.HTTP_400_BAD_REQUEST)
            # Create user
            user = User.objects.create_user(
                username=username, password=password)
            user.save()
            return Response({"message": "User registered successfully"}, \
                            status=status.HTTP_201_CREATED)
        except Exception as error:
            logger.error(
                "Error occurred while registering username %s: %s", username, error
            )
            return Response(
                {"error": "An error occurred during registration"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

# Login endpoint

@permission_classes([AllowAny]) 
class LoginView(APIView):
    """
    View to handle user login.

    This view allows users to log in by providing their username and password.
    It requires the following fields in the request body:
    - username: The username of the user.
    - password: The password of the user.

    Upon a successful login, the view generates and returns an authentication token.
    If the credentials are invalid, a 400 Bad Request response is returned.
    Any other exceptions are logged, and the error is captured in the logs.

    Permissions:
        AllowAny: This view is accessible to any user.
    """
    def post(self, request, *args, **kwargs):
        try:
            username = request.data.get("username")
            password = request.data.get("password")

            user = authenticate(username=username, password=password)
            if user:
                # Generate token if user exists and password is correct
                token, _ = Token.objects.get_or_create(user=user)
                return Response({"token": token.key}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Invalid credentials"}, \
                                status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            logger.error("Error occurred while login for username %s: %s", username, error)
            return Response(
                {"error": "An error occurred during login"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PredictView(APIView):
    """
    View to handle predictions based on input text.

    This view accepts a POST request with the following fields in the request body:
    - text: The input text for prediction.
    - labels: A list of labels for which the prediction will be made.

    The view validates the input using the TextInputSerializer. If the input is valid, it runs the inference 
    and captures the latency of the prediction. It returns a list of entities detected in the input text 
    along with their labels. If the input is invalid, it returns a 400 Bad Request response with 
    the validation errors. Any unexpected errors are logged, and a 500 Internal Server Error response is returned.

    Permissions:
        AllowAny: This view is accessible to any user.
    """
    def post(self, request, *args, **kwargs):
        serializer = TextInputSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning("Invalid input: %s", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            text = serializer.validated_data["text"]
            labels = serializer.validated_data["labels"]

            start_time = time.time()
            entities = get_model().predict_entities(text, labels)
            end_time = time.time()

            inference_time = (end_time - start_time) * 1000
            inference_latency.observe(inference_time)
            inference_throughput.inc()

            logger.info(
                "Prediction successful with entities and inference time %.2f ms",
                inference_time,
            )
            for entity in entities:
                entity_frequency.labels(entity["label"]).inc()

            response_data = [
                {"text": entity["text"], "label": entity["label"]}
                for entity in entities
            ]
            return Response({"entities": response_data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error("Prediction failed: %s", error)
            return Response(
                {"error": "Prediction failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@permission_classes([AllowAny])
class MaskPIIView(APIView):
    """
    Mask PII in raw text using the same input shape as /api/predict/.
    """

    def post(self, request, *args, **kwargs):
        serializer = MaskPIIInputSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning("Invalid mask input: %s", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            text = serializer.validated_data["text"]
            labels = serializer.validated_data["labels"]
            entities = get_model().predict_entities(text, labels)
            response_entities = [
                {"text": entity["text"], "label": entity["label"]}
                for entity in entities
            ]
            masked_text = mask_entities_in_text(text, response_entities)

            return Response(
                {
                    "entities": response_entities,
                    "masked_text": masked_text,
                    "masked_entities_count": len(response_entities),
                },
                status=status.HTTP_200_OK,
            )
        except Exception as error:
            logger.error("Masking failed: %s", error)
            return Response(
                {"error": "Masking failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@permission_classes([AllowAny])           
class HealthCheckView(APIView):
    def get(self, request, *args, **kwargs):
        #return JsonResponse({"status": "ok"}, status=200)
        response = "emr_ner_health_status 1\n"  # 1 indicates healthy, 0 for unhealthy
        return HttpResponse(response, content_type="text/plain")


@permission_classes([AllowAny])
class ApiRootView(APIView):
    def get(self, request, *args, **kwargs):
        return Response(
            {
                "message": "EMR NER API",
                "endpoints": {
                    "register": "/api/register/",
                    "login": "/api/login/",
                    "predict": "/api/predict/",
                    "mask": "/api/mask/",
                    "health": "/api/health/",
                },
            },
            status=status.HTTP_200_OK,
        )
