from django.http import JsonResponse
from django.http import HttpResponse
from rest_framework.views import APIView ,View
from rest_framework.response import Response
from rest_framework import status
from gliner import GLiNER
from .serializers import TextInputSerializer
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from prometheus_client import Histogram, Counter, Gauge, Summary
from rest_framework.decorators import permission_classes
from rest_framework.permissions import AllowAny
import logging
import time

logger = logging.getLogger('nerinference')

inference_latency = Histogram('inference_latency_milliseconds', 'Time taken for a single inference in milliseconds')
inference_throughput = Counter('inference_throughput', 'Total number of inferences processed')
entity_frequency = Counter('entity_frequency', 'Frequency of detected entities', ['entity_type'])

# Load the GLiNER model once during initialization
model = GLiNER.from_pretrained("urchade/gliner_medium-v2.1")

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
        try:
            username = request.data.get("username")
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
                "{} Ocuured while registering the username {}".format(error, username))

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
    try:
        #permission_classes = [AllowAny]

        def post(self, request, *args, **kwargs):
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
    except Exception as e:
        logger.error("error Ocuured while loging {}".format(e))


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
        # Validate the input data with the serializer
            serializer = TextInputSerializer(data=request.data)
            if serializer.is_valid():
                try:
                    text = serializer.validated_data["text"]
                    labels = serializer.validated_data["labels"]

                    # Run inference and capture latency
                    start_time = time.time()
                      # Automatically tracks latency
                    entities = model.predict_entities(text, labels)
                    end_time = time.time()
                    inference_time = (end_time - start_time) * 1000  # in milliseconds
                    inference_latency.observe(inference_time) 
                    logger.info(f"Prediction successful with entities and inference time {inference_time:.2f} ms")
                    # Update entity frequency
                    for entity in entities:
                        entity_type = entity["label"]
                        entity_frequency.labels(entity_type).inc()  # Increment count for each entity type
                    response_data = [{"text": entity["text"],
                                    "label": entity["label"]} for entity in entities]

                    return Response({"entities": response_data}, status=status.HTTP_200_OK)
                except Exception as e:
                    logger.error(f"Prediction failed: {str(e)}")
                    return Response({"error": "Prediction failed"}, 
                                    status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                logger.warning(f"Invalid input: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_500_BAD_REQUEST)


@permission_classes([AllowAny])           
class HealthCheckView(APIView):
    def get(self, request, *args, **kwargs):
        #return JsonResponse({"status": "ok"}, status=200)
        response = "emr_ner_health_status 1\n"  # 1 indicates healthy, 0 for unhealthy
        return HttpResponse(response, content_type="text/plain")
