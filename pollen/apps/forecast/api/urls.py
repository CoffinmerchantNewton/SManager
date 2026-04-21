from django.urls import path

from pollen.apps.forecast.api.views import (
    HomeSummaryAPIView,
    PointProfileSeriesAPIView,
    ProductCollectionAPIView,
)

urlpatterns = [
    path("home/summary/", HomeSummaryAPIView.as_view(), name="api-home-summary"),
    path("home/products/", ProductCollectionAPIView.as_view(), name="api-products"),
    path("home/point-profiles/<int:pk>/series/", PointProfileSeriesAPIView.as_view(), name="api-profile-series"),
]
