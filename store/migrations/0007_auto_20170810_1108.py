# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-08-10 08:08
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0006_auto_20170810_1010'),
    ]

    operations = [
        migrations.RenameField(
            model_name='review',
            old_name='Book',
            new_name='book',
        ),
    ]
