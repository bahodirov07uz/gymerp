from django.urls import path

from . import views

app_name = "members"

urlpatterns = [
    path("reception/", views.reception_home, name="reception"),
    path("", views.MemberListView.as_view(), name="list"),
    path("new/", views.MemberCreateView.as_view(), name="create"),
    path("<int:pk>/", views.MemberProfileView.as_view(), name="profile"),
    path("<int:pk>/add-membership/", views.AddMembershipFromProfileView.as_view(), name="add_membership"),
    path("<int:pk>/add-payment/", views.AddPaymentFromProfileView.as_view(), name="add_payment"),
    path("<int:pk>/add-manual-charge/", views.AddManualChargeFromProfileView.as_view(), name="add_manual_charge"),
]
