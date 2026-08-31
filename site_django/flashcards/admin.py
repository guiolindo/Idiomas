from django.contrib import admin

from .models import Topic, Word, Progress, Profile


class WordInline(admin.TabularInline):
    model = Word
    extra = 1
    fields = ("order", "pt", "en", "emoji")


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("name", "emoji", "slug", "word_count", "order")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [WordInline]
    ordering = ("order",)


@admin.register(Word)
class WordAdmin(admin.ModelAdmin):
    list_display = ("pt", "en", "topic", "emoji")
    list_filter = ("topic",)
    search_fields = ("pt", "en")


@admin.register(Progress)
class ProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "word", "known", "updated_at")
    list_filter = ("known", "word__topic")
    search_fields = ("user__username", "user__email", "word__pt", "word__en")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "streak_count", "last_study_date")
