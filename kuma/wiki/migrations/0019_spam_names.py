# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wiki', '0018_update_locales'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='revisionakismetsubmission',
            options={'verbose_name': 'Akismet submission', 'verbose_name_plural': 'Akismet submissions'},
        ),
        migrations.AlterField(
            model_name='revisionakismetsubmission',
            name='type',
            field=models.CharField(db_index=True, max_length=4, verbose_name='type', choices=[(b'spam', 'Spam'), (b'ham', 'Ham')]),
        ),
    ]
