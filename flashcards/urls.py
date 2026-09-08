from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("entrar/", views.IdiomasLoginView.as_view(), name="login"),
    path("sair/", views.IdiomasLogoutView.as_view(), name="logout"),
    path("criar-conta/", views.signup, name="signup"),
    # Aliases pra rotas que a auditoria apontou como esperadas por
    # convenção (bookmarks antigos, links em outros lugares).
    path("login/", RedirectView.as_view(pattern_name="login", permanent=False)),
    path("conta/criar/", RedirectView.as_view(pattern_name="signup", permanent=False)),
    path("cadastro/", RedirectView.as_view(pattern_name="signup", permanent=False)),
    path("topico/<slug:slug>/", views.topic_detail, name="topic_detail"),
    path("estudar/<slug:slug>/", views.study, name="study"),
    path("desafio/", views.challenge, name="challenge"),
    path("misturar/", views.mixed, name="mixed"),
    path("travadas/", views.leech_list, name="leech_list"),
    path("ajuda/", views.help_page, name="help"),
    path("sobre/", views.about_page, name="about"),
    path("termos/", views.terms_page, name="terms"),
    path("privacidade/", views.privacy_page, name="privacy"),
    path("configuracoes/", views.settings_page, name="settings"),
    path("healthz", views.healthz, name="healthz"),
    path("api/progresso/<int:word_id>/", views.api_mark_progress, name="api_mark_progress"),
    path("api/imagem/", views.api_image, name="api_image"),
    path("api/coach/sessao/", views.api_session_coach, name="api_session_coach"),

    path(
        "senha/esqueci/",
        views.IdiomasPasswordResetView.as_view(success_url=reverse_lazy("password_reset_done")),
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
