# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('wiki', '0016_extend_revision_ip'),
    ]

    operations = [
        migrations.AlterField(
            model_name='documentspamattempt',
            name='created',
            field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created', db_index=True),
        ),
        migrations.AlterField(
            model_name='revisionakismetsubmission',
            name='sent',
            field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='sent at', db_index=True),
        ),
    ]
