from django.urls import path
from .views import LinkView, CreateLinkView

urlpatterns = [
    path('<str:id>', LinkView.as_view()),
    path('', CreateLinkView.as_view())
]