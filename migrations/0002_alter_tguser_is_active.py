# Generated by Django 5.0.1 on 2024-03-07 14:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rewriteBot", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="tguser",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
    ]
