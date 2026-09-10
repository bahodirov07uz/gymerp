from django.urls import path

from . import views

app_name = "sales"

urlpatterns = [
    path("products/search/", views.ProductSearchView.as_view(), name="product_search"),
    path("<int:member_pk>/products/search/", views.ProductSearchView.as_view(), name="product_search"),
    path("<int:pk>/add-product/", views.AddProductSaleView.as_view(), name="add_product"),
]
