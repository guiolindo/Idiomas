import csv

from django.contrib import admin
from django.http import HttpResponse

from .models import Topic, Word, Progress, Profile


class WordInline(admin.TabularInline):
    model = Word
    extra = 1
    fields = ("order", "pt", "en", "has_photo")


def export_words_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="palavras.csv"'
    response.write("﻿")  # BOM, pra abrir certinho no Excel
    writer = csv.writer(response)
    writer.writerow(["topic_id", "topic_name", "topic_emoji", "pt", "en", "has_photo"])
    for word in queryset.select_related("topic").order_by("topic__order", "order"):
        writer.writerow([
            word.topic.slug, word.topic.name, word.topic.emoji,
            word.pt, word.en, "sim" if word.has_photo else "nao",
        ])
    return response


export_words_csv.short_description = "Exportar selecionadas para CSV"


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("name", "emoji", "slug", "word_count", "order")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [WordInline]
    ordering = ("order",)


@admin.register(Word)
class WordAdmin(admin.ModelAdmin):
    list_display = ("pt", "en", "topic", "has_photo")
    list_filter = ("topic", "has_photo")
    search_fields = ("pt", "en")
    actions = [export_words_csv]


@admin.register(Progress)
class ProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "word", "known", "updated_at")
    list_filter = ("known", "word__topic")
    search_fields = ("user__username", "user__email", "word__pt", "word__en")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "streak_count", "last_study_date")
