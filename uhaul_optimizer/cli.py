"""Command-line interface for the U-Haul space optimizer."""

import argparse
import json
import sys

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from .furniture import FURNITURE_CATALOG, FurnitureItem, get_catalog_item
from .optimizer import Recommendation, TrailerFit, find_minimum_trailer
from .trailers import UHAUL_TRAILERS

console = Console()


def list_catalog() -> None:
    """Print the built-in furniture catalog."""
    table = Table(title="Furniture Catalog (dimensions in inches)")
    table.add_column("Slug", style="cyan", no_wrap=True)
    table.add_column("Item", style="white")
    table.add_column("L x W x H", style="green")
    table.add_column("Lbs", style="magenta", justify="right")
    table.add_column("Flags", style="yellow")
    for slug, item in FURNITURE_CATALOG.items():
        flags = []
        if item.keep_upright:
            flags.append("upright")
        if not item.stackable:
            flags.append("no-stack")
        table.add_row(
            slug, item.name,
            f"{item.length:g}x{item.width:g}x{item.height:g}",
            f"{item.weight:g}", ", ".join(flags),
        )
    console.print(table)


def list_trailers() -> None:
    """Print the trailer catalog."""
    table = Table(title="U-Haul Trailers (approximate interior dimensions)")
    table.add_column("Trailer", style="cyan")
    table.add_column("Interior L x W x H", style="green")
    table.add_column("Volume", style="white", justify="right")
    table.add_column("Max load", style="magenta", justify="right")
    table.add_column("Type", style="yellow")
    for t in sorted(UHAUL_TRAILERS, key=lambda x: x.volume_cuft):
        table.add_row(
            t.name,
            f'{t.length:g}"x{t.width:g}"x{t.height:g}"',
            f"{t.volume_cuft:g} cu ft",
            f"{t.max_load:,.0f} lbs",
            "enclosed" if t.enclosed else "open",
        )
    console.print(table)


def parse_item_args(specs: list[str]) -> list[FurnitureItem]:
    """Parse ``slug[:qty]`` or ``name=LxWxH[:weight[:qty]]`` specs into items."""
    items: list[FurnitureItem] = []
    for spec in specs:
        if "=" in spec:
            # Custom item:  "Glass cabinet=40x18x60:120:1"
            name_part, rest = spec.split("=", 1)
            fields = rest.split(":")
            dims = fields[0].lower().split("x")
            if len(dims) != 3:
                raise ValueError(f"Bad dimensions in {spec!r}; expected LxWxH.")
            l, w, h = (float(d) for d in dims)
            weight = float(fields[1]) if len(fields) > 1 and fields[1] else 0.0
            qty = int(fields[2]) if len(fields) > 2 and fields[2] else 1
            items.append(FurnitureItem(name_part.strip(), l, w, h, weight, qty))
        else:
            # Catalog item:  "queen_mattress:1"
            slug, _, qty_str = spec.partition(":")
            qty = int(qty_str) if qty_str else 1
            items.append(get_catalog_item(slug, qty))
    return items


def _bar(fraction: float, width: int = 24) -> str:
    fraction = max(0.0, min(1.0, fraction))
    filled = round(fraction * width)
    return "█" * filled + "░" * (width - filled)


def display_recommendation(rec: Recommendation, items: list[FurnitureItem]) -> None:
    """Render the optimizer result."""
    # Inventory summary.
    inv = Table(title="Your load")
    inv.add_column("Item", style="white")
    inv.add_column("Qty", justify="right", style="cyan")
    inv.add_column("Each (cu ft)", justify="right", style="green")
    inv.add_column("Total (cu ft)", justify="right", style="green")
    for it in items:
        inv.add_row(it.name, str(it.quantity), f"{it.volume_cuft:.1f}", f"{it.total_volume_cuft:.1f}")
    console.print(inv)
    console.print(
        f"[bold]Total:[/bold] {rec.total_volume_cuft:.0f} cu ft, "
        f"{rec.total_weight:,.0f} lbs\n"
    )

    # Headline recommendation.
    if rec.recommended is not None:
        t = rec.recommended.trailer
        util = rec.recommended.utilization
        text = Text()
        text.append(f"\n  {t.name}\n", style="bold green")
        text.append(f"  {t.summary()}\n", style="white")
        text.append(f"  Packs to ~{util*100:.0f}% of capacity  {_bar(util)}\n", style="cyan")
        if t.note:
            text.append(f"  {t.note}\n", style="dim")
        console.print(Panel(text, title="✅ Smallest trailer that fits", border_style="green"))
    else:
        text = Text(
            "\n  No single trailer in the catalog fits everything.\n"
            "  Consider a moving truck (10'-26'), two trips, or paring down.\n",
            style="bold red",
        )
        console.print(Panel(text, title="⚠️  Nothing fits", border_style="red"))

    # Full breakdown of every trailer.
    table = Table(title="All trailers (smallest first)")
    table.add_column("Trailer", style="cyan")
    table.add_column("Fits?", justify="center")
    table.add_column("Fill", style="green")
    table.add_column("Notes / blockers", style="white")
    for ev in rec.evaluations:
        verdict = "[green]yes[/green]" if ev.fits else "[red]no[/red]"
        note = ev.trailer.note if ev.fits else "; ".join(ev.blockers)
        table.add_row(
            ev.trailer.name, verdict,
            f"{ev.utilization*100:.0f}% {_bar(ev.utilization, 12)}",
            note,
        )
    console.print(table)
    console.print(
        "\n[dim]Heuristic estimate — confirm exact trailer specs at uhaul.com "
        "and measure tight items. Pack heavy/flat pieces low and upright.[/dim]"
    )


def load_items_from_json(path: str) -> list[FurnitureItem]:
    """Load an inventory from a JSON file: a list of objects or {slug: qty}."""
    with open(path) as f:
        data = json.load(f)
    items: list[FurnitureItem] = []
    if isinstance(data, dict):
        for slug, qty in data.items():
            items.append(get_catalog_item(slug, int(qty)))
    elif isinstance(data, list):
        for obj in data:
            if "slug" in obj:
                items.append(get_catalog_item(obj["slug"], int(obj.get("quantity", 1))))
            else:
                items.append(FurnitureItem(
                    name=obj["name"],
                    length=float(obj["length"]),
                    width=float(obj["width"]),
                    height=float(obj["height"]),
                    weight=float(obj.get("weight", 0)),
                    quantity=int(obj.get("quantity", 1)),
                    keep_upright=bool(obj.get("keep_upright", False)),
                    stackable=bool(obj.get("stackable", True)),
                ))
    else:
        raise ValueError("JSON must be a list of items or a {slug: qty} object.")
    return items


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find the smallest U-Haul trailer for your furniture.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  uhaul.py queen_mattress sofa:1 dresser dining_chair:4\n"
            "  uhaul.py --file inventory.json --enclosed-only\n"
            '  uhaul.py "Antique hutch=44x20x72:150:1" refrigerator\n'
            "  uhaul.py --list-furniture\n"
        ),
    )
    parser.add_argument("items", nargs="*", help="slug[:qty] or 'Name=LxWxH[:lbs[:qty]]'")
    parser.add_argument("-f", "--file", help="Load inventory from a JSON file.")
    parser.add_argument("--enclosed-only", action="store_true",
                        help="Only consider weatherproof enclosed cargo trailers.")
    parser.add_argument("--list-furniture", action="store_true", help="Show the furniture catalog.")
    parser.add_argument("--list-trailers", action="store_true", help="Show the trailer catalog.")
    args = parser.parse_args()

    if args.list_furniture:
        list_catalog()
        return
    if args.list_trailers:
        list_trailers()
        return

    items: list[FurnitureItem] = []
    try:
        if args.file:
            items.extend(load_items_from_json(args.file))
        if args.items:
            items.extend(parse_item_args(args.items))
    except (KeyError, ValueError) as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    if not items:
        parser.print_help()
        console.print("\n[yellow]Add some furniture, e.g.:[/yellow] uhaul.py queen_mattress sofa dresser")
        sys.exit(1)

    rec = find_minimum_trailer(items, enclosed_only=args.enclosed_only)
    display_recommendation(rec, items)


if __name__ == "__main__":
    main()
