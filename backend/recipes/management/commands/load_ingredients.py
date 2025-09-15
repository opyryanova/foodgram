import csv
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from recipes.models import Ingredient


class Command(BaseCommand):
    help = "Load ingredients into DB from JSON or CSV."

    def add_arguments(self, parser):
        parser.add_argument("--path", type=str, default=None)
        parser.add_argument("--truncate", action="store_true")

    def handle(self, *args, **opts):
        base = Path(settings.BASE_DIR)
        path = (
            Path(opts["path"]).expanduser().resolve()
            if opts["path"]
            else (
                (base / "data" / "ingredients.json")
                if (base / "data" / "ingredients.json").exists()
                else (base / "data" / "ingredients.csv")
            )
        )
        if not path.exists():
            raise CommandError(f"Data file not found: {path}")

        if opts["truncate"]:
            Ingredient.objects.all().delete()

        items = (
            self._load_json(path)
            if path.suffix.lower() == ".json"
            else self._load_csv(path)
        )

        created = 0
        for it in items:
            name = (it.get("name") or "").strip()
            mu = (it.get("measurement_unit") or "").strip()
            if not name or not mu:
                continue
            _, was_created = Ingredient.objects.get_or_create(
                name=name,
                measurement_unit=mu,
            )
            if was_created:
                created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Loaded {len(items)} items, created {created}, "
                f"total {Ingredient.objects.count()}"
            )
        )

    def _load_json(self, path: Path):
        data = json.loads(path.read_text(encoding="utf-8"))
        if (
            data
            and isinstance(data, list)
            and isinstance(data[0], dict)
            and "fields" in data[0]
        ):
            return [
                {
                    "name": i["fields"].get("name"),
                    "measurement_unit": i["fields"].get("measurement_unit"),
                }
                for i in data
            ]
        return data

    def _load_csv(self, path: Path):
        text = path.read_text(encoding="utf-8")
        try:
            dialect = csv.Sniffer().sniff(text[:2048], delimiters=";,")
        except csv.Error:
            dialect = csv.get_dialect("excel")

        rows = list(csv.reader(text.splitlines(), dialect))
        items = []

        header = [str(x).strip().lower() for x in rows[0]] if rows else []
        has_header = any(
            h in header
            for h in (
                "name",
                "measurement_unit",
                "название",
                "единица",
                "единица_измерения",
            )
        )
        start = 1 if has_header else 0

        for r in rows[start:]:
            if not r:
                continue
            name = (r[0] if len(r) > 0 else "").strip()
            mu = (r[1] if len(r) > 1 else "").strip()
            if name and mu:
                items.append({"name": name, "measurement_unit": mu})

        return items
