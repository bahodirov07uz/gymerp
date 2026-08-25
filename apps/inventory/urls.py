from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.InventoryListView.as_view(), name="list"),
    path("<int:pk>/restock/", views.RestockView.as_view(), name="restock"),
]
