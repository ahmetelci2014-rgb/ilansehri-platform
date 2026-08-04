from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView, TemplateView, UpdateView

from apps.listings.models import Notification
from apps.listings.services import create_notification

from .forms import ManagedActivityForm, ManagedRequestForm, ManagedStaffForm
from .models import ManagedActivity, ManagedRequest


class ManagedRequestListView(LoginRequiredMixin, ListView):
    model = ManagedRequest
    template_name = "managed_services/list.html"
    context_object_name = "requests"

    def get_queryset(self):
        return ManagedRequest.objects.filter(customer=self.request.user).select_related("listing", "assigned_staff")


class ManagedRequestDetailView(LoginRequiredMixin, DetailView):
    model = ManagedRequest
    template_name = "managed_services/detail.html"
    context_object_name = "managed_request"

    def get_queryset(self):
        qs = ManagedRequest.objects.select_related("listing", "customer", "assigned_staff").prefetch_related("activities__actor", "tasks")
        if self.request.user.is_staff:
            return qs
        return qs.filter(customer=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["activity_form"] = ManagedActivityForm()
        return context


class ManagedRequestUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = ManagedRequest
    form_class = ManagedRequestForm
    template_name = "managed_services/form.html"

    def test_func(self):
        return self.get_object().customer_id == self.request.user.pk

    def get_success_url(self):
        return reverse("managed_services:detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, "Tam yönetim tercihleriniz güncellendi.")
        return super().form_valid(form)


class ManagedStaffBoardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "managed_services/staff_board.html"

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["new_requests"] = ManagedRequest.objects.filter(status__in=[ManagedRequest.Status.NEW, ManagedRequest.Status.REVIEW]).select_related("listing", "customer")[:50]
        context["active_requests"] = ManagedRequest.objects.filter(status__in=[ManagedRequest.Status.QUOTED, ManagedRequest.Status.ACTIVE, ManagedRequest.Status.WAITING_CUSTOMER]).select_related("listing", "customer", "assigned_staff")[:100]
        return context


class ManagedStaffUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = ManagedRequest
    form_class = ManagedStaffForm
    template_name = "managed_services/staff_form.html"

    def test_func(self):
        return self.request.user.is_staff

    def get_success_url(self):
        return reverse("managed_services:detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        create_notification(
            user=self.object.customer,
            actor=self.request.user,
            listing=self.object.listing,
            notification_type=Notification.Type.MANAGED,
            title="Tam yönetim sürecin güncellendi",
            body=f"Durum: {self.object.get_status_display()} · İlerleme: %{self.object.progress}",
            link=reverse("managed_services:detail", kwargs={"pk": self.object.pk}),
        )
        messages.success(self.request, "Operasyon bilgileri güncellendi.")
        return response


@login_required
@require_POST
def add_activity(request, pk):
    managed_request = get_object_or_404(ManagedRequest, pk=pk)
    if not (request.user.is_staff or managed_request.customer_id == request.user.pk):
        return redirect("managed_services:list")
    form = ManagedActivityForm(request.POST)
    if form.is_valid():
        activity = form.save(commit=False)
        activity.managed_request = managed_request
        activity.actor = request.user
        if not request.user.is_staff:
            activity.visible_to_customer = True
        activity.save()
        if request.user.is_staff and activity.visible_to_customer:
            create_notification(
                user=managed_request.customer,
                actor=request.user,
                listing=managed_request.listing,
                notification_type=Notification.Type.MANAGED,
                title="Tam yönetim sürecinde yeni gelişme",
                body=activity.note[:300],
                link=reverse("managed_services:detail", kwargs={"pk": managed_request.pk}),
            )
        messages.success(request, "Süreç notu eklendi.")
    else:
        messages.error(request, "Not eklenemedi.")
    return redirect("managed_services:detail", pk=managed_request.pk)
