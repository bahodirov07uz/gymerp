from django.urls import path

from . import views

app_name = "sales"

urlpatterns = [
    path("<int:pk>/add-product/", views.AddProductSaleView.as_view(), name="add_product"),
]
