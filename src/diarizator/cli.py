from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .api import DiarizatorConfig, diarize
from .bundle import create_bundle, validate_bundle
from .environment import capture_environment
from .media import inspect_media
from .output import validate_run_outputs


def _run(args: argparse.Namespace, mode: str) -> None:
    config = DiarizatorConfig(
        speaker_count_mode=mode,
        num_speakers=getattr(args, "num_speakers", None),
        min_speakers=getattr(args, "min_speakers", None),
        max_speakers=getattr(args, "max_speakers", None),
        backend=args.backend,
        language=args.language,
    )
    path = diarize(args.audio, args.output, config=config, token=os.environ.get("HF_TOKEN"))
    print(path)


def main() -> None:
    parser = argparse.ArgumentParser(prog="diarizator", description="Reproducible speaker diarization and ASR")
    sub = parser.add_subparsers(dest="command", required=True)
    inspect_cmd = sub.add_parser("inspect", help="Inspect an audio file without running models")
    inspect_cmd.add_argument("audio", type=Path)
    for name in ("run", "exact", "bounded"):
        command = sub.add_parser(name)
        command.add_argument("audio", type=Path)
        command.add_argument("--output", type=Path, default=Path("diarizator-results"))
        command.add_argument("--backend", choices=("community-1", "legacy-3.1"), default="community-1")
        command.add_argument("--language", default="auto")
        if name == "run":
            command.add_argument("--speaker-count", choices=("estimated", "exact", "bounded"), default="estimated")
            command.add_argument("--num-speakers", type=int)
            command.add_argument("--min-speakers", type=int)
            command.add_argument("--max-speakers", type=int)
        if name == "exact":
            command.add_argument("--num-speakers", type=int, required=True)
        if name == "bounded":
            command.add_argument("--min-speakers", type=int, required=True)
            command.add_argument("--max-speakers", type=int, required=True)
    validate_cmd = sub.add_parser("validate")
    validate_cmd.add_argument("run_dir", type=Path)
    bundle_cmd = sub.add_parser("bundle")
    bundle_cmd.add_argument("run_dirs", type=Path, nargs="+")
    bundle_cmd.add_argument("--output", dest="destination", type=Path, default=Path("diarizator-results.zip"))
    sub.add_parser("environment")
    demo_cmd = sub.add_parser("demo", help="Run or inspect the installed controlled demonstration")
    demo_cmd.add_argument("--inspect", action="store_true")
    demo_cmd.add_argument("--output", type=Path, default=Path("diarizator-demo-results"))
    args = parser.parse_args()

    if args.command == "inspect":
        result = inspect_media(args.audio)
    elif args.command in {"run", "exact", "bounded"}:
        mode = args.speaker_count if args.command == "run" else args.command
        _run(args, mode)
        return
    elif args.command == "validate":
        result = validate_run_outputs(args.run_dir)
    elif args.command == "bundle":
        result = create_bundle(args.run_dirs, args.destination)
        validate_bundle(args.destination)
    elif args.command == "environment":
        result = capture_environment()
    else:
        source_demo = Path(__file__).resolve().parents[2] / "examples" / "controlled_demo" / "The_Measure_of_a_Good_Life.mp3"
        installed_demo = Path(os.sys.prefix) / "share" / "diarizator" / "examples" / "controlled_demo" / source_demo.name
        demo = source_demo if source_demo.exists() else installed_demo
        if args.inspect:
            result = inspect_media(demo)
        else:
            path = diarize(demo, args.output, config=DiarizatorConfig(speaker_count_mode="exact", num_speakers=2), token=os.environ.get("HF_TOKEN"))
            print(path)
            return
    print(json.dumps(result, indent=2, sort_keys=True))
    if isinstance(result, dict) and result.get("status") == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
