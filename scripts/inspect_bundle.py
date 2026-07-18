import argparse
import json
import zipfile
from pathlib import Path
from diarizator.bundle import validate_bundle

parser = argparse.ArgumentParser()
parser.add_argument("bundle", type=Path)
args = parser.parse_args()
validate_bundle(args.bundle)
with zipfile.ZipFile(args.bundle) as archive:
    print(json.dumps({"status": "PASS", "entries": archive.namelist()}, indent=2))
