# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def clear_json(apps, schema_editor):
    """Clear cached Document JSON.

    In forward migration, this allows regenerating with UUIDs.
    In reverse migration, this allows regenerating without UUIDs.
    """
    Document = apps.get_model('wiki', 'Document')
    Document.objects.all().update(json=None)


class Migration(migrations.Migration):

    dependencies = [
        ('wiki', '0023_require_document_uuid'),
    ]

    operations = [
        migrations.RunPython(clear_json, clear_json)
    ]
