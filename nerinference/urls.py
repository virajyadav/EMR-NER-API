from django.urls import path
from .views import PredictView
from .views import RegisterView
from .views import LoginView 
from .views import HealthCheckView


urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("predict/", PredictView.as_view(), name="predict"),
    path("health/",HealthCheckView.as_view(),name="health")
]
