# decide/models.py
from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Decision(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    QUADRANT_CHOICES = [
        ("Q1", "Urgent & Important"),
        ("Q2", "Not Urgent & Important"),
        ("Q3", "Urgent & Not Important"),
        ("Q4", "Not Urgent & Not Important"),
    ]
    quadrant = models.CharField(
        max_length=2, choices=QUADRANT_CHOICES, null=True, blank=True
    )

    def __str__(self):
        return self.title


class Prompt(models.Model):
    slug = models.SlugField(unique=True)
    order = models.PositiveIntegerField()
    text = models.CharField(max_length=255)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.order}. {self.text}"


class DecisionResponse(models.Model):
    decision = models.ForeignKey(
        Decision, on_delete=models.CASCADE, related_name="responses"
    )
    prompt = models.ForeignKey(Prompt, on_delete=models.CASCADE)
    answer = models.BooleanField()
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("decision", "prompt")

    def __str__(self):
        return f"{self.decision.title} → {self.prompt.slug} = {self.answer}"
