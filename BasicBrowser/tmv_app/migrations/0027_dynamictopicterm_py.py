# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-08-17 14:49
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tmv_app', '0026_auto_20170807_1242'),
    ]

    operations = [
        migrations.AddField(
            model_name='dynamictopicterm',
            name='PY',
            field=models.IntegerField(db_index=True, null=True),
        ),
    ]
