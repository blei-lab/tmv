# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2018-03-22 10:51
from __future__ import unicode_literals

from django.conf import settings
import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.CITIES_COUNTRY_MODEL),
        ('parliament', '0025_seat_party'),
    ]

    operations = [
        migrations.RenameField(
            model_name='person',
            old_name='bio',
            new_name='short_bio',
        ),
        migrations.AddField(
            model_name='party',
            name='alt_names',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.TextField(), null=True, size=None),
        ),
        migrations.AddField(
            model_name='person',
            name='academic_title',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='person',
            name='adel',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='person',
            name='country_of_birth',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.CITIES_COUNTRY_MODEL),
        ),
        migrations.AddField(
            model_name='person',
            name='date_of_death',
            field=models.DateField(null=True),
        ),
        migrations.AddField(
            model_name='person',
            name='family_status',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='person',
            name='gender',
            field=models.IntegerField(choices=[(1, 'Female'), (2, 'Male')], null=True),
        ),
        migrations.AddField(
            model_name='person',
            name='occupation',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='person',
            name='ortszusatz',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='person',
            name='place_of_birth',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='person',
            name='prefix',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='person',
            name='religion',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='person',
            name='title',
            field=models.TextField(null=True),
        ),
    ]
