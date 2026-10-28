"""Offline GLB inspection; exit 0 pending visual review, 2 rejected, 1 invalid."""

import argparse
import json
from pathlib import Path

from archimind.assets import CatalogError, load_catalog
from archimind.assets.inspection import InspectionError, inspect_furniture_asset


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-id", required=True)
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--expected-sha256")
    args = parser.parse_args()
    try:
        record = load_catalog().get_record(args.asset_id)
        result = inspect_furniture_asset(
            args.file, record, expected_sha256=args.expected_sha256
        )
        print(result.model_dump_json(indent=2))
        return 0 if result.status == "automated_pass_visual_pending" else 2
    except (InspectionError, CatalogError) as error:
        code = (
            str(error)
            if isinstance(error, InspectionError)
            else "invalid_catalog_reference"
        )
        print(
            json.dumps(
                {"status": "rejected", "render_qualified": False, "error_code": code}
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
