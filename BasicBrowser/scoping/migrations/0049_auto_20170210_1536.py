# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2017-02-10 15:36
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scoping', '0048_auto_20170209_1708'),
    ]

    operations = [
        migrations.AlterField(
            model_name='query',
            name='type',
            field=models.TextField(default='default', null=True, verbose_name='Query Type'),
        ),
    ]
