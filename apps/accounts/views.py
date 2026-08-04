from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.db.models.functions import Coalesce
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView

from apps.listings.models import Conversation, Favorite, Offer

from .forms import SignUpForm


class SignUpView(CreateView):
    form_class = SignUpForm
    template_name = "registration/signup.html"
    success_url = reverse_lazy("accounts:dashboard")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("accounts:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, "İlan Şehri hesabın oluşturuldu. Hoş geldin!")
        return response


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["my_listings"] = (
            user.listings.select_related("category")
            .prefetch_related("images")
            .order_by("-updated_at")[:12]
        )
        context["received_offers"] = (
            Offer.objects.filter(listing__owner=user)
            .select_related("listing", "sender")
            .order_by("-created_at")[:10]
        )
        context["sent_offers"] = user.offers.select_related("listing")[:10]
        context["managed_requests"] = user.managed_requests.select_related("listing")[:10]
        context["favorite_items"] = (
            Favorite.objects.filter(user=user, listing__status="published")
            .select_related("listing", "listing__category")
            .prefetch_related("listing__images")[:4]
        )
        context["conversations"] = (
            Conversation.objects.filter(Q(buyer=user) | Q(seller=user))
            .select_related("listing", "buyer", "seller")
            .prefetch_related("messages")
            .annotate(
                unread_count=Coalesce(
                    Count(
                        "messages",
                        filter=Q(messages__is_read=False) & ~Q(messages__sender=user),
                    ),
                    0,
                )
            )
            .order_by("-updated_at")[:6]
        )
        context["favorite_count"] = Favorite.objects.filter(user=user, listing__status="published").count()
        context["unread_message_count"] = sum(
            item.unread_count for item in context["conversations"]
        )
        return context
