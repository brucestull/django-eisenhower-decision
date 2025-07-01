# Django Eisenhower Matrix App

- [Django Eisenhower Matrix App](https://chatgpt.com/c/685e8571-2a98-8002-8aab-452e446eb1a5)

```python
# models.py
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Decision(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    QUADRANT_CHOICES = [
        ('Q1', 'Urgent & Important'),
        ('Q2', 'Not Urgent & Important'),
        ('Q3', 'Urgent & Not Important'),
        ('Q4', 'Not Urgent & Not Important'),
    ]
    quadrant = models.CharField(max_length=2, choices=QUADRANT_CHOICES, null=True, blank=True)

    def __str__(self):
        return self.title

class Prompt(models.Model):
    slug = models.SlugField(unique=True)
    order = models.PositiveIntegerField()
    text = models.CharField(max_length=255)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.order}. {self.text}"

class DecisionResponse(models.Model):
    decision = models.ForeignKey(Decision, on_delete=models.CASCADE, related_name='responses')
    prompt = models.ForeignKey(Prompt, on_delete=models.CASCADE)
    answer = models.BooleanField()
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('decision', 'prompt')

    def __str__(self):
        return f"{self.decision.title} → {self.prompt.slug} = {self.answer}"
```

```json
// fixtures/prompts.json (to seed your two matrix questions)
[
  {
    "model": "yourapp.prompt",
    "pk": 1,
    "fields": {
      "slug": "is_urgent",
      "order": 1,
      "text": "Is this task urgent?"
    }
  },
  {
    "model": "yourapp.prompt",
    "pk": 2,
    "fields": {
      "slug": "is_important",
      "order": 2,
      "text": "Is this task important?"
    }
  }
]
```

```python
# forms.py
from django import forms
from .models import Decision

class DecisionForm(forms.ModelForm):
    class Meta:
        model = Decision
        fields = ['title', 'description']

class DecisionResponseForm(forms.Form):
    answer = forms.TypedChoiceField(
        coerce=lambda x: x == 'True',
        choices=[('True', 'Yes'), ('False', 'No')],
        widget=forms.RadioSelect(attrs={
            'class': 'sr-only'
        }),
        label=""
    )
```

```python
# views.py
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import Decision, Prompt, DecisionResponse
from .forms import DecisionForm

@login_required
def create_decision(request):
    if request.method == 'POST':
        form = DecisionForm(request.POST)
        if form.is_valid():
            decision = form.save(commit=False)
            decision.user = request.user
            decision.save()
            return redirect('decision_flow', decision_id=decision.id)
    else:
        form = DecisionForm()
    return render(request, 'yourapp/decision_create.html', {'form': form})

@login_required
def decision_flow(request, decision_id):
    decision = get_object_or_404(Decision, id=decision_id, user=request.user)
    first_prompt = Prompt.objects.first()
    total = Prompt.objects.count()
    return render(request, 'yourapp/decision_flow.html', {
        'decision': decision,
        'prompt': first_prompt,
        'total_prompts': total
    })

@login_required
@require_POST
def decision_flow_json(request, decision_id):
    """
    AJAX endpoint: Accepts JSON {prompt_id, answer} and returns next prompt or final quadrant.
    """
    decision = get_object_or_404(Decision, id=decision_id, user=request.user)
    try:
        payload = json.loads(request.body)
        prompt_id = payload['prompt_id']
        answer = payload['answer']
    except (KeyError, json.JSONDecodeError):
        return HttpResponseBadRequest('Invalid JSON payload')

    prompt = get_object_or_404(Prompt, id=prompt_id)
    DecisionResponse.objects.create(decision=decision, prompt=prompt, answer=answer)

    # Fetch next prompt
    answered_ids = decision.responses.values_list('prompt_id', flat=True)
    remaining = Prompt.objects.exclude(id__in=answered_ids)
    if remaining.exists():
        nxt = remaining.first()
        return JsonResponse({'prompt_id': nxt.id, 'text': nxt.text})

    # Compute quadrant
    resp = {r.prompt.slug: r.answer for r in decision.responses.all()}
    urgent = resp.get('is_urgent')
    important = resp.get('is_important')
    if urgent and important:
        decision.quadrant = 'Q1'
    elif not urgent and important:
        decision.quadrant = 'Q2'
    elif urgent and not important:
        decision.quadrant = 'Q3'
    else:
        decision.quadrant = 'Q4'
    decision.save()

    return JsonResponse({'quadrant': decision.get_quadrant_display()})

@login_required
def decision_result(request, decision_id):
    decision = get_object_or_404(Decision, id=decision_id, user=request.user)
    return render(request, 'yourapp/decision_result.html', {'decision': decision})
```

```python
# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('decisions/new/', views.create_decision, name='create_decision'),
    path('decisions/<int:decision_id>/flow/', views.decision_flow, name='decision_flow'),
    path('decisions/<int:decision_id>/flow/json/', views.decision_flow_json, name='decision_flow_json'),
    path('decisions/<int:decision_id>/result/', views.decision_result, name='decision_result'),
]
```

```html
# templates/yourapp/decision_flow.html
{% extends 'base.html' %}
{% block content %}
<div class="max-w-md mx-auto mt-12 p-8 bg-white rounded-2xl shadow-lg">
  <h2 class="text-2xl font-bold mb-4 text-center">{{ decision.title }}</h2>

  <!-- Progress bar -->
  <div class="w-full bg-gray-200 rounded-full h-2 mb-6">
    <div id="progress-bar" class="h-2 rounded-full bg-indigo-600" style="width: 0%;"></div>
  </div>

  <div id="prompt-container" data-total="{{ total_prompts }}" data-answered="0">
    <p id="prompt-text" class="text-lg text-center font-medium mb-6">{{ prompt.text }}</p>
  </div>

  <div class="flex justify-around mb-6">
    <button data-value="True" class="answer-btn py-2 px-6 bg-green-100 hover:bg-green-200 rounded-lg font-semibold focus:outline-none">Yes</button>
    <button data-value="False" class="answer-btn py-2 px-6 bg-red-100 hover:bg-red-200 rounded-lg font-semibold focus:outline-none">No</button>
  </div>

  <div id="result-container" class="hidden text-center"></div>
</div>

<script>
(function() {
  const decisionId = {{ decision.id }};
  const flowUrl = `{% url 'decision_flow_json' decision.id %}`;
  const promptContainer = document.getElementById('prompt-container');
  const promptText = document.getElementById('prompt-text');
  const progressBar = document.getElementById('progress-bar');
  const total = parseInt(promptContainer.dataset.total, 10);
  let answered = 0;

  document.querySelectorAll('.answer-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const answer = btn.dataset.value === 'True';
      const currentId = promptContainer.dataset.current || {{ prompt.id }};

      // disable buttons
      document.querySelectorAll('.answer-btn').forEach(b => b.disabled = true);

      fetch(flowUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': '{{ csrf_token }}'
        },
        body: JSON.stringify({ prompt_id: currentId, answer })
      })
      .then(resp => resp.json())
      .then(data => {
        answered++;
        const percent = Math.round((answered / total) * 100);
        progressBar.style.width = percent + '%';

        if (data.text) {
          promptText.textContent = data.text;
          promptContainer.dataset.current = data.prompt_id;
          document.querySelectorAll('.answer-btn').forEach(b => b.disabled = false);
        } else if (data.quadrant) {
          document.querySelector('.max-w-md').innerHTML =
            `<h2 class="text-2xl font-bold mb-4 text-center">Result: ${data.quadrant}</h2>` +
            `<div class="text-center mt-4">` +
            `<a href="{% url 'create_decision' %}" class="py-2 px-4 bg-indigo-600 text-white rounded-lg">New Decision</a>` +
            `</div>`;
        }
      })
      .catch(err => {
        console.error(err);
        alert('Something went wrong.');
      });
    });
  });
})();
</script>
{% endblock %}
```
