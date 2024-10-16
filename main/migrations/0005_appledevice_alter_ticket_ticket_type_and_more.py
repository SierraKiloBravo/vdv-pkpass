# Generated by Django 5.0.9 on 2024-10-09 20:37

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0004_uicticketinstance_vdvticketinstance_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="AppleDevice",
            fields=[
                (
                    "device_id",
                    models.CharField(
                        max_length=255,
                        primary_key=True,
                        serialize=False,
                        verbose_name="Device ID",
                    ),
                ),
                (
                    "push_token",
                    models.CharField(max_length=255, verbose_name="Push token"),
                ),
            ],
        ),
        migrations.AlterField(
            model_name="ticket",
            name="ticket_type",
            field=models.CharField(
                choices=[
                    ("deutschlandticket", "Deutschlandticket"),
                    ("bahncard", "Bahncard"),
                    ("fahrkarte", "Fahrkarte"),
                    ("interrail", "Interrail"),
                    ("unknown", "Unknown"),
                ],
                default="unknown",
                max_length=255,
                verbose_name="Ticket type",
            ),
        ),
        migrations.AlterField(
            model_name="vdvticketinstance",
            name="ticket",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="vdv_instances",
                to="main.ticket",
            ),
        ),
    ]
