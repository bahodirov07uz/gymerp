from django.urls import path

from . import views

app_name = "billing"

urlpatterns = [
    path("<int:pk>/receive-payment/", views.ReceivePaymentView.as_view(), name="receive_payment"),
    path("debtors/", views.DebtorsListView.as_view(), name="debtors"),
    path("ledger/<int:pk>/reverse/", views.ReverseLedgerEntryView.as_view(), name="reverse_entry"),
]
