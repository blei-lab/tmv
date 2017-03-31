# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2017-03-22 13:28
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scoping', '0064_auto_20170317_1314'),
    ]

    operations = [
        migrations.AddField(
            model_name='query',
            name='refdblen',
            field=models.IntegerField(null=True, verbose_name='Snowball Number of references in the DB'),
        ),
        migrations.AddField(
            model_name='query',
            name='refscraplen',
            field=models.IntegerField(null=True, verbose_name='Snowball Number of references to be scraped'),
        ),
        migrations.AddField(
            model_name='query',
            name='reftotlen',
            field=models.IntegerField(null=True, verbose_name='Snowball Number of references'),
        ),
    ]
