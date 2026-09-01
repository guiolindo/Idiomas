from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("entrar/", views.IdiomasLoginView.as_view(), name="login"),
    path("sair/", views.IdiomasLogoutView.as_view(), name="logout"),
    path("criar-conta/", views.signup, name="signup"),
    path("topico/<slug:slug>/", views.topic_detail, name="topic_detail"),
    path("estudar/<slug:slug>/", views.study, name="study"),
    path("api/progresso/<int:word_id>/", views.api_mark_progress, name="api_mark_progress"),
    path("api/imagem/", views.api_image, name="api_image"),

    path(
        "senha/esqueci/",
        auth_views.PasswordResetView.as_view(
            template_name="flashcards/password_reset.html",
            email_template_name="flashcards/password_reset_email.txt",
            subject_template_name="flashcards/password_reset_subject.txt",
            success_url=reverse_lazy("password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "senha/enviado/",
        auth_views.PasswordResetDoneView.as_view(template_name="flashcards/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "senha/redefinir/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="flashcards/password_reset_confirm.html",
            success_url=reverse_lazy("password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "senha/concluido/",
        auth_views.PasswordResetCompleteView.as_view(template_name="flashcards/password_reset_complete.html"),
        name="password_reset_complete",
    ),
    path(
        "conta/senha/",
        auth_views.PasswordChangeView.as_view(
            template_name="flashcards/password_change.html",
            success_url=reverse_lazy("password_change_done"),
        ),
        name="password_change",
    ),
    path(
        "conta/senha/alterada/",
        auth_views.PasswordChangeDoneView.as_view(template_name="flashcards/password_change_done.html"),
        name="password_change_done",
    ),
]
