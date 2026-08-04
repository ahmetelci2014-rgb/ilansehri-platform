from django.urls import path

from .views import (
    HelpCenterView,
    StaffSupportBoardView,
    StaffTicketDetailView,
    TicketCreateView,
    TicketDetailView,
    TicketListView,
    close_ticket,
    staff_ticket_update,
    ticket_reply,
)

app_name = "support_center"
urlpatterns = [
    path("", HelpCenterView.as_view(), name="help_center"),
    path("talep/yeni/", TicketCreateView.as_view(), name="ticket_create"),
    path("taleplerim/", TicketListView.as_view(), name="ticket_list"),
    path("talep/<uuid:public_id>/", TicketDetailView.as_view(), name="ticket_detail"),
    path("talep/<uuid:public_id>/yanit/", ticket_reply, name="ticket_reply"),
    path("talep/<uuid:public_id>/kapat/", close_ticket, name="ticket_close"),
    path("ekip/", StaffSupportBoardView.as_view(), name="staff_board"),
    path("ekip/<uuid:public_id>/", StaffTicketDetailView.as_view(), name="staff_detail"),
    path("ekip/<uuid:public_id>/guncelle/", staff_ticket_update, name="staff_update"),
]
