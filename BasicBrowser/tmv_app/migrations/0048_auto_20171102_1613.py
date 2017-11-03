# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-11-02 16:13
from __future__ import unicode_literals

from django.db import migrations, models
import tmv_app.models


class Migration(migrations.Migration):

    dependencies = [
        ('tmv_app', '0047_auto_20171102_1233'),
    ]

    operations = [
        migrations.AddField(
            model_name='runstats',
            name='max_df',
            field=tmv_app.models.MinMaxFloat(default=0.95),
        ),
        migrations.AddField(
            model_name='runstats',
            name='min_freq',
            field=models.IntegerField(default=1, help_text='Minimum frequency of terms'),
        ),
        migrations.AlterField(
            model_name='runstats',
            name='max_features',
            field=models.IntegerField(default=0, help_text='Maximum number of terms'),
        ),
    ]
