from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from apps.listings.models import Notification
from apps.listings.services import create_notification

from .forms import PartnerProfileForm, TaskApplicationForm, TaskCreateForm, TaskSubmissionForm
from .models import PartnerEarning, PartnerProfile, Task, TaskApplication
from apps.managed_services.models import ManagedRequest


class PartnerApplyView(LoginRequiredMixin, CreateView):
    model = PartnerProfile
    form_class = PartnerProfileForm
    template_name = "partners/apply.html"
    success_url = reverse_lazy("partners:dashboard")

    def dispatch(self, request, *args, **kwargs):
        if hasattr(request.user, "partner_profile"):
            return redirect("partners:profile_edit")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.user = self.request.user
        self.request.user.user_type = self.request.user.UserType.PARTNER
        self.request.user.save(update_fields=["user_type"])
        messages.success(self.request, "Görev ortağı başvurun alındı.")
        return super().form_valid(form)


class PartnerProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = PartnerProfile
    form_class = PartnerProfileForm
    template_name = "partners/apply.html"
    success_url = reverse_lazy("partners:dashboard")

    def get_object(self, queryset=None):
        return get_object_or_404(PartnerProfile, user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Görev ortağı profilin güncellendi.")
        return super().form_valid(form)


class PartnerDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "partners/dashboard.html"

    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request.user, "partner_profile"):
            return redirect("partners:apply")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.request.user.partner_profile
        context["profile"] = profile
        context["assigned_tasks"] = profile.tasks.exclude(status__in=[Task.Status.COMPLETED, Task.Status.CANCELLED]).select_related("managed_request__listing")[:20]
        context["applications"] = profile.task_applications.select_related("task")[:20]
        context["earnings"] = profile.earnings.select_related("task")[:20]
        return context


class OpenTaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = "partners/task_list.html"
    context_object_name = "tasks"
    paginate_by = 30

    def get_queryset(self):
        if not hasattr(self.request.user, "partner_profile"):
            return Task.objects.none()
        profile = self.request.user.partner_profile
        qs = Task.objects.filter(status=Task.Status.OPEN).select_related("managed_request__listing")
        if profile.service_cities:
            qs = qs.filter(city__in=profile.service_cities)
        task_type = self.request.GET.get("type")
        if task_type:
            qs = qs.filter(task_type=task_type)
        return qs


class TaskCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Task
    form_class = TaskCreateForm
    template_name = "partners/task_form.html"

    def test_func(self):
        return self.request.user.is_staff

    def dispatch(self, request, *args, **kwargs):
        self.managed_request = get_object_or_404(
            ManagedRequest.objects.select_related("listing", "customer"),
            pk=kwargs["managed_request_id"],
        )
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial.update(
            {
                "city": self.managed_request.listing.city,
                "district": self.managed_request.listing.district,
                "title": f"{self.managed_request.listing.title} için saha görevi",
            }
        )
        return initial

    def form_valid(self, form):
        form.instance.managed_request = self.managed_request
        response = super().form_valid(form)
        messages.success(self.request, "Görev Kazanç Ağı'na açıldı.")
        return response

    def get_success_url(self):
        return reverse("partners:task_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["managed_request"] = self.managed_request
        return context


class TaskDetailView(LoginRequiredMixin, DetailView):
    model = Task
    template_name = "partners/task_detail.html"
    context_object_name = "task"

    def get_queryset(self):
        qs = Task.objects.select_related("assigned_partner__user", "managed_request__listing").prefetch_related("applications__partner__user")
        if self.request.user.is_staff:
            return qs
        profile = getattr(self.request.user, "partner_profile", None)
        if not profile:
            return qs.none()
        return qs.filter(
            Q(status=Task.Status.OPEN)
            | Q(assigned_partner=profile)
            | Q(applications__partner=profile)
        ).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = getattr(self.request.user, "partner_profile", None)
        context["application_form"] = TaskApplicationForm()
        context["submission_form"] = TaskSubmissionForm(instance=self.object)
        context["my_application"] = self.object.applications.filter(partner=profile).first() if profile else None
        return context


@require_POST
def apply_task(request, pk):
    if not request.user.is_authenticated or not hasattr(request.user, "partner_profile"):
        return redirect("partners:apply")
    profile = request.user.partner_profile
    task = get_object_or_404(Task, pk=pk, status=Task.Status.OPEN)
    if profile.status != PartnerProfile.Status.ACTIVE:
        messages.warning(request, "Görev başvurusu için profilinin aktif olarak onaylanması gerekiyor.")
        return redirect("partners:task_detail", pk=task.pk)
    form = TaskApplicationForm(request.POST)
    if form.is_valid():
        application, created = TaskApplication.objects.get_or_create(
            task=task,
            partner=profile,
            defaults={"note": form.cleaned_data["note"]},
        )
        if created:
            messages.success(request, "Görev başvurun gönderildi.")
        else:
            messages.info(request, "Bu göreve daha önce başvurdun.")
    return redirect("partners:task_detail", pk=task.pk)


@require_POST
def task_action(request, pk, action):
    if not request.user.is_authenticated:
        return redirect("login")
    task = get_object_or_404(Task.objects.select_related("assigned_partner__user", "managed_request__customer", "managed_request__listing"), pk=pk)
    profile = getattr(request.user, "partner_profile", None)
    if action in {"start", "submit"} and (not profile or task.assigned_partner_id != profile.pk):
        return redirect("partners:task_detail", pk=task.pk)
    if action == "start" and task.status == Task.Status.ASSIGNED:
        task.status = Task.Status.IN_PROGRESS
        task.save(update_fields=["status"])
        messages.success(request, "Görev başlatıldı.")
    elif action == "submit" and task.status in {Task.Status.ASSIGNED, Task.Status.IN_PROGRESS}:
        form = TaskSubmissionForm(request.POST, request.FILES, instance=task)
        if form.is_valid():
            task = form.save(commit=False)
            task.status = Task.Status.REVIEW
            task.save()
            messages.success(request, "Görev kontrol için gönderildi.")
        else:
            messages.error(request, "Teslim bilgilerini kontrol et.")
    elif action in {"accept_application", "complete", "reject"} and request.user.is_staff:
        if action == "accept_application":
            application = get_object_or_404(TaskApplication, pk=request.POST.get("application_id"), task=task)
            with transaction.atomic():
                task.applications.filter(status=TaskApplication.Status.PENDING).exclude(pk=application.pk).update(status=TaskApplication.Status.REJECTED)
                application.status = TaskApplication.Status.ACCEPTED
                application.save(update_fields=["status"])
                task.assigned_partner = application.partner
                task.status = Task.Status.ASSIGNED
                task.save(update_fields=["assigned_partner", "status"])
            create_notification(
                user=application.partner.user,
                actor=request.user,
                notification_type=Notification.Type.TASK,
                title="Görev başvurun kabul edildi",
                body=task.title,
                link=reverse("partners:task_detail", kwargs={"pk": task.pk}),
            )
            messages.success(request, "Görev ortağı atandı.")
        elif action == "complete" and task.status == Task.Status.REVIEW:
            task.status = Task.Status.COMPLETED
            task.completed_at = timezone.now()
            task.save(update_fields=["status", "completed_at"])
            amount = task.reward + task.success_bonus
            earning, _ = PartnerEarning.objects.get_or_create(task=task, defaults={"partner": task.assigned_partner, "amount": amount})
            task.assigned_partner.completed_tasks += 1
            task.assigned_partner.total_earnings += amount
            task.assigned_partner.save(update_fields=["completed_tasks", "total_earnings"])
            create_notification(
                user=task.assigned_partner.user,
                actor=request.user,
                notification_type=Notification.Type.TASK,
                title="Görev tamamlandı",
                body=f"{amount} TL kazanç kaydı oluşturuldu.",
                link=reverse("partners:dashboard"),
            )
            messages.success(request, "Görev onaylandı ve kazanç kaydı oluşturuldu.")
        elif action == "reject":
            task.status = Task.Status.IN_PROGRESS
            task.save(update_fields=["status"])
            messages.warning(request, "Görev düzeltme için ortağa geri gönderildi.")
    else:
        messages.error(request, "Geçersiz görev işlemi.")
    return redirect("partners:task_detail", pk=task.pk)


@require_POST
def partner_profile_action(request, pk, action):
    if not request.user.is_authenticated or not request.user.is_staff:
        raise Http404
    profile = get_object_or_404(PartnerProfile.objects.select_related("user"), pk=pk)
    statuses = {
        "approve": PartnerProfile.Status.ACTIVE,
        "reject": PartnerProfile.Status.REJECTED,
        "suspend": PartnerProfile.Status.SUSPENDED,
    }
    if action not in statuses:
        messages.error(request, "Geçersiz görev ortağı işlemi.")
        return redirect("partners:staff_board")
    profile.status = statuses[action]
    if action == "approve" and profile.user.is_phone_verified:
        profile.level = PartnerProfile.Level.VERIFIED
    profile.save(update_fields=["status", "level", "updated_at"])
    create_notification(
        user=profile.user,
        actor=request.user,
        notification_type=Notification.Type.TASK,
        title="Görev ortağı başvurun güncellendi",
        body=f"Başvuru durumu: {profile.get_status_display()}",
        link=reverse("partners:dashboard"),
    )
    messages.success(request, f"{profile.user.display_name} için durum güncellendi.")
    return redirect("partners:staff_board")


class PartnerStaffBoardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "partners/staff_board.html"

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pending_profiles"] = PartnerProfile.objects.filter(status=PartnerProfile.Status.PENDING).select_related("user")[:50]
        context["task_applications"] = TaskApplication.objects.filter(status=TaskApplication.Status.PENDING).select_related("task", "partner__user")[:100]
        context["review_tasks"] = Task.objects.filter(status=Task.Status.REVIEW).select_related("assigned_partner__user", "managed_request__listing")[:100]
        return context
