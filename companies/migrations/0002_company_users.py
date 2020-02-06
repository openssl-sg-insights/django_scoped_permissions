# Generated by Django 3.0.3 on 2020-02-06 14:37

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('companies', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='users',
            field=models.ManyToManyField(related_name='companies', to=settings.AUTH_USER_MODEL),
        ),
    ]
