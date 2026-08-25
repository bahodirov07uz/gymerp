from django.urls import path
from . import views

app_name = "memberships"

urlpatterns = [
    path("<int:pk>/create/", views.CreateMembershipView.as_view(), name="create_for_member"),
]
