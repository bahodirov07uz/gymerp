from django.urls import path

from . import views

app_name = "attendance"

urlpatterns = [
    path("<int:pk>/check-in/", views.CheckInView.as_view(), name="check_in"),
    path("<int:pk>/check-out/", views.CheckOutView.as_view(), name="check_out"),
    path("<int:pk>/add-daily-plan/", views.AddDailyPlanView.as_view(), name="add_daily_plan"),
    path("in-gym/", views.InGymListView.as_view(), name="in_gym_list"),
]
