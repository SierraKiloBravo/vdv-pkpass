import base64
import secrets
import dacite
from django.db import models
from django.core import validators
from . import ticket as t
from . import vdv, uic


def make_pass_token():
    return secrets.token_urlsafe(32)


class Ticket(models.Model):
    TYPE_DEUTCHLANDTICKET = "deutschlandticket"
    TYPE_BAHNCARD = "bahncard"
    TYPE_UNKNOWN = "unknown"

    TICKET_TYPES = (
        (TYPE_DEUTCHLANDTICKET, "Deutschlandticket"),
        (TYPE_BAHNCARD, "Bahncard"),
        (TYPE_UNKNOWN, "Unknown"),
    )

    id = models.CharField(max_length=32, primary_key=True, verbose_name="ID")
    ticket_type = models.CharField(max_length=255, choices=TICKET_TYPES, verbose_name="Ticket type", default=TYPE_UNKNOWN)
    pkpass_authentication_token = models.CharField(max_length=255, verbose_name="PKPass authentication token", default=make_pass_token)


class VDVTicketInstance(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="vdv_instances")
    ticket_number = models.PositiveIntegerField(verbose_name="Ticket number")
    ticket_org_id = models.PositiveIntegerField(verbose_name="Organization ID")
    validity_start = models.DateTimeField()
    validity_end = models.DateTimeField()
    barcode_data = models.BinaryField()
    decoded_data = models.JSONField()

    class Meta:
        unique_together = [
            ["ticket_number", "ticket_org_id"],
        ]
        ordering = ["-validity_start"]

    def as_ticket(self) -> t.VDVTicket:
        config = dacite.Config(type_hooks={bytes: base64.b64decode})
        raw_ticket = base64.b64decode(self.decoded_data["ticket"])
        return t.VDVTicket(
            root_ca=dacite.from_dict(data_class=vdv.CertificateData, data=self.decoded_data["root_ca"], config=config),
            issuing_ca=dacite.from_dict(data_class=vdv.CertificateData, data=self.decoded_data["issuing_ca"], config=config),
            envelope_certificate=dacite.from_dict(data_class=vdv.CertificateData, data=self.decoded_data["envelope_certificate"], config=config),
            raw_ticket=raw_ticket,
            ticket=vdv.VDVTicket.parse(raw_ticket)
        )

class UICTicketInstance(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="uic_instances")
    reference = models.CharField(max_length=20, verbose_name="Ticket ID")
    distributor_rics = models.PositiveIntegerField(validators=[validators.MaxValueValidator(9999)], verbose_name="Distributor RICS")
    issuing_time = models.DateTimeField()
    barcode_data = models.BinaryField()
    decoded_data = models.JSONField()

    class Meta:
        unique_together = [
            ["reference", "distributor_rics"],
        ]
        ordering = ["-issuing_time"]

    def as_ticket(self) -> t.UICTicket:
        config = dacite.Config(type_hooks={bytes: base64.b64decode})
        ticket_envelope = dacite.from_dict(data_class=uic.Envelope, data=self.decoded_data["envelope"], config=config)
        return t.UICTicket(
            raw_bytes=self.barcode_data,
            envelope=ticket_envelope,
            head=t.parse_ticket_uic_head(ticket_envelope),
            layout=t.parse_ticket_uic_layout(ticket_envelope),
            flex=t.parse_ticket_uic_flex(ticket_envelope),
            other_records=[r for r in ticket_envelope.records if not r.id.startswith("U_")]
        )