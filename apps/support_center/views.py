from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView, TemplateView

from apps.listings.services import consume_rate_limit

from .forms import StaffTicketUpdateForm, SupportReplyForm, SupportTicketForm
from .models import StaffActionLog, SupportTicket
from .services import add_ticket_reply, log_staff_action


FAQ_GROUPS = [
    {
        "title": "Üyelik ve güvenlik",
        "icon": "🛡️",
        "items": [
            ("Telefonumu nasıl doğrularım?", "Hesabım > Hesabı doğrula bölümünden telefon veya e-posta doğrulaması başlatabilirsin."),
            ("Şifremi unuttum, ne yapmalıyım?", "Giriş ekranındaki Şifremi unuttum bağlantısını kullanarak yeni şifre bağlantısı isteyebilirsin."),
            ("Şüpheli bir kullanıcıyı nasıl engellerim?", "Kullanıcının profilindeki Engelle seçeneğini kullanabilir, ilanını ayrıca şikâyet edebilirsin."),
        ],
    },
    {
        "title": "İlan ve moderasyon",
        "icon": "📣",
        "items": [
            ("İlanım neden incelemede?", "Yeni ve güncellenen ilanlar güvenlik kontrolünden geçer. Sonuç Hesabım ve Bildirimler ekranında görünür."),
            ("İlanımı daha güçlü nasıl yaparım?", "Açıklayıcı başlık, ayrıntılı açıklama, gerçek fiyat ve en az dört aydınlık fotoğraf ekle."),
            ("Taslağımı nerede bulurum?", "Hesabım > Taslaklarım bölümünden kayıtlı ilan taslaklarına devam edebilirsin."),
        ],
    },
    {
        "title": "Mesaj, teklif ve işlem",
        "icon": "🤝",
        "items": [
            ("Teklif nasıl çalışır?", "Alıcı teklif gönderir; satıcı kabul, ret veya karşı teklif verebilir. Kabul edilince işlem kaydı açılır."),
            ("Ödemeyi İlan Şehri mi alıyor?", "Hayır. Mevcut sürüm para transferine aracılık etmez; yalnız anlaşma ve teslim sürecini kayıt altına alır."),
            ("Uyuşmazlık nasıl bildirilir?", "İşlem detayından uyuşmazlık bildirimi açabilir ve kanıtları destek talebine ekleyebilirsin."),
        ],
    },
    {
        "title": "Tam Yönetim ve Kazanç Ağı",
        "icon": "🧭",
        "items": [
            ("Tam Yönetim nedir?", "İlan hazırlama, fotoğraf, mesaj ve randevu süreçlerinin İlan Şehri ekibi tarafından yönetilmesidir."),
            ("Görev ortağı nasıl olurum?", "Kazanç Ağı başvurusunu doldurup inceleme sonucunu bekleyebilirsin."),
        ],
    },
]


class HelpCenterView(TemplateView):
    template_name = "support_center/help_center.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get("q", "").strip().lower()
        groups = FAQ_GROUPS
        if query:
            filtered = []
            for group in FAQ_GROUPS:
                items = [item for item in group["items"] if query in (item[0] + " " + item[1]).lower()]
                if items:
                    filtered.append({**group, "items": items})
            groups = filtered
        context["faq_groups"] = groups
        context["query"] = query
        if self.request.user.is_authenticated:
            context["open_ticket_count"] = self.request.user.support_tickets.exclude(
                status__in=[SupportTicket.Status.RESOLVED, SupportTicket.Status.CLOSED]
            ).count()
            context["recent_tickets"] = self.request.user.support_tickets.all()[:4]
        return context


class TicketListView(LoginRequiredMixin, ListView):
    template_name = "support_center/ticket_list.html"
    context_object_name = "tickets"
    paginate_by = 20

    def get_queryset(self):
        qs = self.request.user.support_tickets.select_related("assigned_to", "related_listing").annotate(
            reply_count=Count("replies")
        )
        status = self.request.GET.get("status", "").strip()
        if status in {value for value, _ in SupportTicket.Status.choices}:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_choices"] = SupportTicket.Status.choices
        return context


class TicketCreateView(LoginRequiredMixin, CreateView):
    model = SupportTicket
    form_class = SupportTicketForm
    template_name = "support_center/ticket_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if not consume_rate_limit(self.request, "support_ticket", limit=4, period=3600):
            form.add_error(None, "Bir saat içinde en fazla 4 destek talebi açabilirsin.")
            return self.form_invalid(form)
        form.instance.user = self.request.user
        form.instance.priority = SupportTicket.Priority.NORMAL
        response = super().form_valid(form)
        log_staff_action(
            actor=self.request.user,
            action=StaffActionLog.Action.TICKET_CREATED,
            summary=f"Destek talebi açıldı: {self.object.subject}",
            target=self.object,
        )
        messages.success(self.request, "Destek talebin oluşturuldu. Yanıt geldiğinde bildirim alacaksın.")
        return response


class TicketDetailView(LoginRequiredMixin, DetailView):
    model = SupportTicket
    template_name = "support_center/ticket_detail.html"
    context_object_name = "ticket"
    slug_field = "public_id"
    slug_url_kwarg = "public_id"

    def get_queryset(self):
        return self.request.user.support_tickets.select_related(
            "assigned_to", "related_listing", "related_transaction__listing"
        ).prefetch_related("replies__author")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["public_replies"] = self.object.replies.filter(is_internal_note=False).select_related("author")
        context["reply_form"] = SupportReplyForm()
        return context


@login_required
@require_POST
def ticket_reply(request, public_id):
    ticket = get_object_or_404(SupportTicket, public_id=public_id, user=request.user)
    if ticket.status == SupportTicket.Status.CLOSED:
        messages.warning(request, "Kapatılmış talebe yanıt gönderilemez.")
        return redirect(ticket.get_absolute_url())
    if not consume_rate_limit(request, "support_reply", limit=12, period=3600):
        messages.error(request, "Kısa sürede çok fazla yanıt gönderdin. Biraz sonra yeniden dene.")
        return redirect(ticket.get_absolute_url())
    form = SupportReplyForm(request.POST)
    if form.is_valid():
        add_ticket_reply(ticket=ticket, author=request.user, message=form.cleaned_data["message"])
        messages.success(request, "Yanıtın destek ekibine iletildi.")
    else:
        messages.error(request, "Yanıt metnini kontrol et.")
    return redirect(ticket.get_absolute_url())


@login_required
@require_POST
def close_ticket(request, public_id):
    ticket = get_object_or_404(SupportTicket, public_id=public_id, user=request.user)
    if ticket.status != SupportTicket.Status.CLOSED:
        ticket.status = SupportTicket.Status.CLOSED
        ticket.resolved_at = timezone.now()
        ticket.save(update_fields=["status", "resolved_at", "updated_at"])
        messages.success(request, "Destek talebi kapatıldı.")
    return redirect(ticket.get_absolute_url())


class StaffSupportRequiredMixin(UserPassesTestMixin):
    raise_exception = True

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff


class StaffSupportBoardView(StaffSupportRequiredMixin, TemplateView):
    template_name = "support_center/staff_board.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = SupportTicket.objects.select_related("user", "assigned_to", "related_listing")
        status = self.request.GET.get("status", "").strip()
        priority = self.request.GET.get("priority", "").strip()
        assigned = self.request.GET.get("assigned", "").strip()
        query = self.request.GET.get("q", "").strip()
        if status in {value for value, _ in SupportTicket.Status.choices}:
            qs = qs.filter(status=status)
        if priority in {value for value, _ in SupportTicket.Priority.choices}:
            qs = qs.filter(priority=priority)
        if assigned == "me":
            qs = qs.filter(assigned_to=self.request.user)
        elif assigned == "none":
            qs = qs.filter(assigned_to__isnull=True)
        if query:
            qs = qs.filter(Q(subject__icontains=query) | Q(description__icontains=query) | Q(user__username__icontains=query))
        context.update(
            {
                "tickets": qs[:100],
                "status_filter": status,
                "priority_filter": priority,
                "assigned_filter": assigned,
                "query": query,
                "stats": {
                    "open": SupportTicket.objects.filter(status=SupportTicket.Status.OPEN).count(),
                    "in_progress": SupportTicket.objects.filter(status=SupportTicket.Status.IN_PROGRESS).count(),
                    "waiting_user": SupportTicket.objects.filter(status=SupportTicket.Status.WAITING_USER).count(),
                    "urgent": SupportTicket.objects.filter(
                        priority=SupportTicket.Priority.URGENT,
                    ).exclude(status__in=[SupportTicket.Status.RESOLVED, SupportTicket.Status.CLOSED]).count(),
                },
                "recent_logs": StaffActionLog.objects.select_related("actor")[:15],
                "status_choices": SupportTicket.Status.choices,
                "priority_choices": SupportTicket.Priority.choices,
            }
        )
        return context


class StaffTicketDetailView(StaffSupportRequiredMixin, DetailView):
    model = SupportTicket
    template_name = "support_center/staff_detail.html"
    context_object_name = "ticket"
    slug_field = "public_id"
    slug_url_kwarg = "public_id"

    def get_queryset(self):
        return SupportTicket.objects.select_related(
            "user", "assigned_to", "related_listing", "related_transaction__listing"
        ).prefetch_related("replies__author")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["update_form"] = StaffTicketUpdateForm(instance=self.object)
        context["reply_rows"] = self.object.replies.select_related("author")
        context["action_logs"] = StaffActionLog.objects.filter(
            target_type="SupportTicket", target_id=str(self.object.pk)
        ).select_related("actor")[:20]
        return context


@user_passes_test(lambda user: user.is_authenticated and user.is_staff)
@require_POST
def staff_ticket_update(request, public_id):
    ticket = get_object_or_404(SupportTicket.objects.select_related("user", "assigned_to"), public_id=public_id)
    previous = {
        "status": ticket.status,
        "priority": ticket.priority,
        "assigned_to_id": ticket.assigned_to_id,
    }
    form = StaffTicketUpdateForm(request.POST, instance=ticket)
    if not form.is_valid():
        messages.error(request, "Destek talebi bilgilerini kontrol et.")
        return redirect("support_center:staff_detail", public_id=ticket.public_id)

    ticket = form.save(commit=False)
    if ticket.status in {SupportTicket.Status.RESOLVED, SupportTicket.Status.CLOSED} and not ticket.resolved_at:
        ticket.resolved_at = timezone.now()
    elif ticket.status not in {SupportTicket.Status.RESOLVED, SupportTicket.Status.CLOSED}:
        ticket.resolved_at = None
    ticket.save()

    public_reply = form.cleaned_data.get("public_reply", "").strip()
    internal_note = form.cleaned_data.get("internal_note", "").strip()
    if public_reply:
        add_ticket_reply(
            ticket=ticket,
            author=request.user,
            message=public_reply,
            update_status=ticket.status not in {SupportTicket.Status.RESOLVED, SupportTicket.Status.CLOSED},
        )
        log_staff_action(
            actor=request.user,
            action=StaffActionLog.Action.TICKET_REPLIED,
            summary=f"Kullanıcıya yanıt gönderildi: {ticket.subject}",
            target=ticket,
        )
    if internal_note:
        add_ticket_reply(ticket=ticket, author=request.user, message=internal_note, internal=True)
        log_staff_action(
            actor=request.user,
            action=StaffActionLog.Action.INTERNAL_NOTE,
            summary=f"İç not eklendi: {ticket.subject}",
            target=ticket,
        )
    if previous != {
        "status": ticket.status,
        "priority": ticket.priority,
        "assigned_to_id": ticket.assigned_to_id,
    }:
        log_staff_action(
            actor=request.user,
            action=StaffActionLog.Action.TICKET_STATUS,
            summary=f"Talep güncellendi: {ticket.subject}",
            target=ticket,
            metadata={"before": previous, "after": {
                "status": ticket.status,
                "priority": ticket.priority,
                "assigned_to_id": ticket.assigned_to_id,
            }},
        )
    messages.success(request, "Destek talebi güncellendi.")
    return redirect("support_center:staff_detail", public_id=ticket.public_id)
