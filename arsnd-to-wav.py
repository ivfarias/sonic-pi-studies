#!/usr/bin/env python3
"""Extract embedded WAV samples from Elektron .arsnd ZIP archives.

Uses Python 3's standard library. Preset synthesis and effects are not rendered.
"""

import argparse
from pathlib import Path
import sys
import zipfile


def save_sample(destination, data):
    """Leave existing files intact; skip identical files or choose a free name."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    candidate = destination
    number = 2
    while True:
        try:
            with candidate.open("xb") as output:
                output.write(data)
            return candidate, True
        except FileExistsError:
            if candidate.is_file() and candidate.read_bytes() == data:
                return candidate, False
            candidate = destination.with_name(
                f"{destination.stem} ({number}){destination.suffix}"
            )
            number += 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="An .arsnd file or folder to scan recursively")
    parser.add_argument(
        "-o", "--output", type=Path, default=Path("extracted_wavs"),
        help="Destination folder (default: ./extracted_wavs)",
    )
    args = parser.parse_args()
    source = args.source.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if source.is_dir():
        files = sorted(
            p for p in source.rglob("*")
            if p.is_file() and p.suffix.lower() == ".arsnd"
        )
        root = source
    elif source.is_file() and source.suffix.lower() == ".arsnd":
        files = [source]
        root = source.parent
    else:
        parser.error("Source must be an existing folder or .arsnd file")
    if not files:
        print("No .arsnd files found.", file=sys.stderr)
        return 1

    written = unchanged = empty = errors = 0
    for preset in files:
        try:
            with zipfile.ZipFile(preset) as archive:
                samples = [
                    info for info in archive.infolist()
                    if not info.is_dir() and info.filename.lower().endswith(".wav")
                ]
                if not samples:
                    print(f"NO SAMPLE: {preset.relative_to(root)}")
                    empty += 1
                    continue
                for index, info in enumerate(samples, 1):
                    data = archive.read(info)
                    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
                        raise ValueError(f"Embedded file is not a RIFF WAV: {info.filename}")
                    suffix = "" if len(samples) == 1 else f" - sample {index}"
                    # Preserve source folders and name each WAV after its preset.
                    # Archive paths are never used as destination paths.
                    destination = (
                        output / preset.parent.relative_to(root)
                        / f"{preset.stem}{suffix}.wav"
                    )
                    saved, is_new = save_sample(destination, data)
                    if is_new:
                        written += 1
                        print(f"EXTRACTED: {saved}")
                    else:
                        unchanged += 1
                        print(f"ALREADY EXTRACTED: {saved}")
        except (OSError, ValueError, RuntimeError, EOFError, zipfile.BadZipFile,
                NotImplementedError) as error:
            errors += 1
            print(f"ERROR: {preset}: {error}", file=sys.stderr)

    print(
        f"\nScanned {len(files)} preset(s). Extracted {written} WAV(s); "
        f"already present {unchanged}; presets without WAVs {empty}; errors {errors}."
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())