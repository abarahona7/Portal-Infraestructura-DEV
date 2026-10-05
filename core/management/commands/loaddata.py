"""Impide cargar fixtures sobre datos existentes del portal."""

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management.base import CommandError
from django.core.management.commands.loaddata import Command as DjangoLoadDataCommand
from django.db import connections


class Command(DjangoLoadDataCommand):
    def handle(self, *fixture_labels, **options):
        alias = options['database']
        connection = connections[alias]
        tables = set(connection.introspection.table_names())
        models = [get_user_model(), *apps.get_app_config('core').get_models()]
        if any(model._meta.db_table not in tables for model in models):
            raise CommandError('Aplique todas las migraciones antes de cargar la fixture.')
        for model in models:
            if model._base_manager.using(alias).exists():
                raise CommandError(
                    'La base ya contiene usuarios o datos del portal. '
                    'No se permite loaddata sobre un destino no vacío.'
                )
        return super().handle(*fixture_labels, **options)
