# admin.py
from django.contrib import admin

from .models import Decision, DecisionResponse, Prompt


class DecisionResponseInline(admin.TabularInline):
    model = DecisionResponse
    extra = 0
    readonly_fields = ("prompt", "answer", "answered_at")
    can_delete = False


@admin.register(Decision)
class DecisionAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "quadrant", "created_at")
    list_filter = ("quadrant", "created_at", "user")
    search_fields = ("title", "description", "user__username", "user__email")
    readonly_fields = ("created_at",)
    inlines = (DecisionResponseInline,)


@admin.register(Prompt)
class PromptAdmin(admin.ModelAdmin):
    list_display = ("order", "slug", "text")
    list_editable = ("order", "text")
    # add this so the “slug” column (second in list_display) is the edit link
    list_display_links = ("slug",)

    prepopulated_fields = {"slug": ("text",)}
    ordering = ("order",)
    search_fields = ("slug", "text")


@admin.register(DecisionResponse)
class DecisionResponseAdmin(admin.ModelAdmin):
    list_display = ("decision", "prompt", "answer", "answered_at")
    list_filter = ("answer", "prompt", "answered_at")
    search_fields = ("decision__title", "prompt__slug")
    readonly_fields = ("answered_at",)
