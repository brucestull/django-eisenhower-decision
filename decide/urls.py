# urls.py
from django.urls import path

from . import views

app_name = "decide"
urlpatterns = [
    path("", views.create_decision, name="create_decision"),
    path("decisions/", views.DecisionListView.as_view(), name="decision_list"),
    path("responses/", views.ResponseListView.as_view(), name="response_list"),
    path("flow/<int:decision_id>/", views.decision_flow, name="decision_flow"),
    path(
        "flow/<int:decision_id>/json/",
        views.decision_flow_json,
        name="decision_flow_json",
    ),
    path("result/<int:decision_id>/", views.decision_result, name="decision_result"),
]
