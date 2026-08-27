import time

from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError


class Command(BaseCommand):
    """Blocks until the configured database accepts connections. Used by the
    container entrypoint so the app doesn't start migrating before Postgres
    is ready to accept connections."""

    help = "Waits for the database to become available."

    def add_arguments(self, parser):
        parser.add_argument("--timeout", type=int, default=30)

    def handle(self, *args, **options):
        timeout = options["timeout"]
        elapsed = 0
        self.stdout.write("Checking database availability...")
        while elapsed < timeout:
            try:
                connections["default"].cursor()
            except OperationalError:
                elapsed += 1
                time.sleep(1)
            else:
                self.stdout.write(self.style.SUCCESS("Database available."))
                return
        self.stderr.write(self.style.ERROR(f"Database not available after {timeout}s."))
        raise SystemExit(1)
