# decide/views.py
import json

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Case, IntegerField, Value, When
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.generic import ListView

from .forms import DecisionForm
from .models import Decision, DecisionResponse, Prompt


@login_required
def create_decision(request):
    if request.method == "POST":
        form = DecisionForm(request.POST)
        if form.is_valid():
            decision = form.save(commit=False)
            decision.user = request.user
            decision.save()
            return redirect("decide:decision_flow", decision_id=decision.id)
    else:
        form = DecisionForm()
    return render(request, "decide/decision_create.html", {"form": form})


@login_required
def decision_flow(request, decision_id):
    decision = get_object_or_404(Decision, id=decision_id, user=request.user)
    first_prompt = Prompt.objects.first()
    total = Prompt.objects.count()
    return render(
        request,
        "decide/decision_flow.html",
        {"decision": decision, "prompt": first_prompt, "total_prompts": total},
    )


@login_required
@require_POST
def decision_flow_json(request, decision_id):
    """
    AJAX endpoint: Accepts JSON {prompt_id, answer} and returns next prompt or final quadrant. # noqa: E501
    """
    decision = get_object_or_404(Decision, id=decision_id, user=request.user)
    try:
        payload = json.loads(request.body)
        prompt_id = payload["prompt_id"]
        answer = payload["answer"]
    except (KeyError, json.JSONDecodeError):
        return HttpResponseBadRequest("Invalid JSON payload")

    prompt = get_object_or_404(Prompt, id=prompt_id)
    DecisionResponse.objects.create(decision=decision, prompt=prompt, answer=answer)

    # Fetch next prompt
    answered_ids = decision.responses.values_list("prompt_id", flat=True)
    remaining = Prompt.objects.exclude(id__in=answered_ids)
    if remaining.exists():
        nxt = remaining.first()
        return JsonResponse({"prompt_id": nxt.id, "text": nxt.text})

    # Compute quadrant
    resp = {r.prompt.slug: r.answer for r in decision.responses.all()}
    urgent = resp.get("is_urgent")
    important = resp.get("is_important")
    if urgent and important:
        decision.quadrant = "Q1"
    elif not urgent and important:
        decision.quadrant = "Q2"
    elif urgent and not important:
        decision.quadrant = "Q3"
    else:
        decision.quadrant = "Q4"
    decision.save()

    return JsonResponse({"quadrant": decision.get_quadrant_display()})


@login_required
def decision_result(request, decision_id):
    decision = get_object_or_404(Decision, id=decision_id, user=request.user)
    return render(request, "decide/decision_result.html", {"decision": decision})


class DecisionListView(LoginRequiredMixin, ListView):
    model = Decision
    template_name = "decide/decision_list.html"
    context_object_name = "decisions"
    paginate_by = 20

    def get_sort(self):
        # ?sort=quadrant or ?sort=date
        return self.request.GET.get("sort", "quadrant")

    def get_queryset(self):
        qs = Decision.objects.filter(user=self.request.user)
        sort = self.get_sort()

        if sort == "quadrant":
            # Annotate a numeric order for Q1→Q4, default last
            qs = qs.annotate(
                quadrant_order=Case(
                    When(quadrant="Q1", then=Value(1)),
                    When(quadrant="Q2", then=Value(2)),
                    When(quadrant="Q3", then=Value(3)),
                    When(quadrant="Q4", then=Value(4)),
                    default=Value(5),
                    output_field=IntegerField(),
                )
            ).order_by("quadrant_order", "-created_at")
        else:
            # Date created, newest first
            qs = qs.order_by("-created_at")

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["current_sort"] = self.get_sort()
        return ctx


class ResponseListView(LoginRequiredMixin, ListView):
    model = DecisionResponse
    template_name = "decide/response_list.html"
    context_object_name = "responses"
    paginate_by = 20

    def get_queryset(self):
        return (
            DecisionResponse.objects.filter(decision__user=self.request.user)
            .select_related("decision", "prompt")
            .order_by("-answered_at")
        )
