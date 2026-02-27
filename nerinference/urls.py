from django.urls import path
from .views import PredictView
from .views import RegisterView
from .views import LoginView 
from .views import HealthCheckView
from .views import ApiRootView
from .views import MaskPIIView


urlpatterns = [
    path("", ApiRootView.as_view(), name="api-root"),
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("predict/", PredictView.as_view(), name="predict"),
    path("mask/", MaskPIIView.as_view(), name="mask"),
    path("health/",HealthCheckView.as_view(),name="health")
]
