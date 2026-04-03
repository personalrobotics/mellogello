#!/usr/bin/env python3
"""VS Code-friendly deploy utility for MelloGello MicroPython firmware."""

from __future__ import annotations

import argparse
import importlib
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable, Optional

DEFAULT_BAUDRATE = 115200
DEFAULT_SOURCE = Path("reference/main.py")
DEFAULT_TARGET = ":main.py"
DEFAULT_SETTINGS = Path("reference/mello_settings.py")
DEFAULT_ASSETS_DIR = Path("reference/assets")
DEFAULT_ASSET_MANIFEST = DEFAULT_ASSETS_DIR / "manifest.txt"
DEFAULT_SECRETS_SOURCE = Path(".secrets/wifi_secrets.py")
DEFAULT_SECRETS_TARGET = ":wifi_secrets.py"


def _list_ports_module():
    try:
        return importlib.import_module("serial.tools.list_ports")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "pyserial is not available. Install host dependencies first: "
            "python -m pip install -r requirements-host.txt"
        ) from exc


def _serial_module():
    try:
        return importlib.import_module("serial")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "pyserial is not available. Install host dependencies first: "
            "python -m pip install -r requirements-host.txt"
        ) from exc


def _run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def _run_allow_fail(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=False)


def _mpremote_cmd(*args: str) -> list[str]:
    return [sys.executable, "-m", "mpremote", *args]


def _find_mello_port(explicit_port: Optional[str]) -> str:
    if explicit_port:
        return explicit_port

    candidates: list[str] = []
    list_ports = _list_ports_module()
    for p in list_ports.comports():
        haystack = " ".join(
            [
                p.device or "",
                p.description or "",
                p.manufacturer or "",
                p.product or "",
                p.hwid or "",
            ]
        ).lower()
        if "m5stack" in haystack or "uiflow" in haystack or "303a" in haystack:
            candidates.append(p.device)

    if len(candidates) == 1:
        return candidates[0]

    if len(candidates) > 1:
        raise RuntimeError(
            "Multiple possible Mello ports found: "
            + ", ".join(candidates)
            + ". Use --port explicitly."
        )

    raise RuntimeError(
        "No Mello serial port found automatically. Use --port (for example COM5)."
    )


def _ensure_mpremote() -> None:
    try:
        _run(_mpremote_cmd("--help"))
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise RuntimeError(
            "mpremote is not available. Install host dependencies first: "
            "python -m pip install -r requirements-host.txt"
        ) from exc


def _mkdir_remote(port: str, remote_dir: str) -> None:
    _run_allow_fail(_mpremote_cmd("connect", port, "fs", "mkdir", remote_dir))


def _prepare_port_for_repl(port: str) -> None:
    serial_mod = _serial_module()
    try:
        with serial_mod.Serial(port=port, baudrate=115200, timeout=0.3) as ser:
            try:
                ser.dtr = False
                ser.rts = False
            except Exception:
                pass

            ser.write(b"\r\x03\x03\x02\x03")
            ser.flush()
    except Exception:
        pass


def _copy_file(port: str, source: Path, target: str) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Source file not found: {source}")

    cmd = _mpremote_cmd("connect", port, "fs", "cp", str(source), target)
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            _run(cmd)
            return
        except subprocess.CalledProcessError:
            if attempt >= max_attempts:
                raise RuntimeError(
                    "Upload failed: could not enter MicroPython raw REPL. "
                    "Ensure the board is running MicroPython in normal run mode "
                    "(not bootloader/JTAG flash mode), then pause stream output and retry."
                )

            print("warning: upload attempt failed; trying to interrupt/reset REPL and retry...")
            _prepare_port_for_repl(port)
            time.sleep(0.5)


def _manifest_asset_files(assets_dir: Path, manifest_path: Path) -> list[Path]:
    if not manifest_path.exists():
        return []

    files: list[Path] = []
    for raw in manifest_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        candidate = assets_dir / line
        if not candidate.exists():
            raise FileNotFoundError(f"Asset listed in manifest was not found: {candidate}")
        if candidate.is_dir():
            continue
        files.append(candidate)
    return files


def _deploy_assets(port: str, assets_dir: Path, manifest_path: Path, remote_root: str) -> None:
    if not assets_dir.exists():
        return

    files = _manifest_asset_files(assets_dir=assets_dir, manifest_path=manifest_path)
    if not files:
        return

    root = remote_root.rstrip("/")
    _mkdir_remote(port, root)

    for source in files:
        rel = source.relative_to(assets_dir).as_posix()
        parts = rel.split("/")
        path_so_far = root
        for part in parts[:-1]:
            path_so_far = f"{path_so_far}/{part}"
            _mkdir_remote(port, path_so_far)

        target = f"{root}/{rel}"
        _copy_file(port=port, source=source, target=target)


def _deploy(
    port: str,
    source: Path,
    target: str,
    settings_source: Path,
    with_assets: bool,
    assets_dir: Path,
    asset_manifest: Path,
    assets_target_root: str,
    with_secrets: bool,
    secrets_source: Path,
    secrets_target: str,
) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Source file not found: {source}")

    _ensure_mpremote()

    # In normal run mode, proactively interrupt any running script before copy.
    _prepare_port_for_repl(port)
    time.sleep(0.25)

    _copy_file(port=port, source=source, target=target)

    if settings_source.exists():
        _copy_file(port=port, source=settings_source, target=":mello_settings.py")

    if with_assets:
        _deploy_assets(
            port=port,
            assets_dir=assets_dir,
            manifest_path=asset_manifest,
            remote_root=assets_target_root,
        )

    if with_secrets:
        if not secrets_source.exists():
            raise FileNotFoundError(
                "Secrets file was requested but not found: "
                f"{secrets_source}. Create it from .secrets/wifi_secrets.py.example"
            )
        _copy_file(port=port, source=secrets_source, target=secrets_target)

    _run(_mpremote_cmd("connect", port, "soft-reset"))


def _reboot(port: str) -> None:
    _ensure_mpremote()
    _run(_mpremote_cmd("connect", port, "soft-reset"))


def _monitor(port: str, baudrate: int) -> None:
    _run([sys.executable, "-m", "serial.tools.miniterm", port, str(baudrate)])


def _list_ports() -> None:
    list_ports = _list_ports_module()
    ports = list(list_ports.comports())
    if not ports:
        print("No serial ports detected.")
        return

    for p in ports:
        print(f"{p.device}\t{p.description}\t{p.hwid}")


def _prompt_device_ready() -> None:
    print("Prepare device for upload before continuing.")
    print("CoreS3 must be running MicroPython in normal run mode for mpremote file upload.")
    print("Do not use bootloader/JTAG flashing mode for this step.")
    print("If firmware is currently streaming, pause it before continuing.")
    answer = input("Press Enter to continue upload, or type 'q' to cancel: ").strip().lower()
    if answer == "q":
        raise RuntimeError("Upload cancelled by user before device preparation.")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MelloGello MicroPython deploy helper")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-ports", help="List visible serial ports")

    deploy = sub.add_parser("deploy", help="Copy firmware to device and soft-reset")
    deploy.add_argument("--port", default=None, help="Serial port, e.g. COM5")
    deploy.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help=f"Path to firmware source (default: {DEFAULT_SOURCE})",
    )
    deploy.add_argument(
        "--target",
        default=DEFAULT_TARGET,
        help=f"Target path on device (default: {DEFAULT_TARGET})",
    )
    deploy.add_argument(
        "--prompt-device-ready",
        action="store_true",
        help="Prompt user to place device in required upload mode before deploy",
    )
    deploy.add_argument(
        "--settings-source",
        type=Path,
        default=DEFAULT_SETTINGS,
        help=f"Path to runtime settings file (default: {DEFAULT_SETTINGS})",
    )
    deploy.add_argument(
        "--with-assets",
        action="store_true",
        help="Upload files listed in reference/assets/manifest.txt to device assets dir",
    )
    deploy.add_argument(
        "--assets-dir",
        type=Path,
        default=DEFAULT_ASSETS_DIR,
        help=f"Local assets dir (default: {DEFAULT_ASSETS_DIR})",
    )
    deploy.add_argument(
        "--asset-manifest",
        type=Path,
        default=DEFAULT_ASSET_MANIFEST,
        help=f"Asset manifest path (default: {DEFAULT_ASSET_MANIFEST})",
    )
    deploy.add_argument(
        "--assets-target-root",
        default=":assets",
        help="Target directory on device for assets (default: :assets)",
    )
    deploy.add_argument(
        "--with-secrets",
        action="store_true",
        help="Upload local Wi-Fi secrets file to device",
    )
    deploy.add_argument(
        "--secrets-source",
        type=Path,
        default=DEFAULT_SECRETS_SOURCE,
        help=f"Local secrets source (default: {DEFAULT_SECRETS_SOURCE})",
    )
    deploy.add_argument(
        "--secrets-target",
        default=DEFAULT_SECRETS_TARGET,
        help=f"Target path for secrets on device (default: {DEFAULT_SECRETS_TARGET})",
    )

    reboot = sub.add_parser("reboot", help="Soft-reset MicroPython device")
    reboot.add_argument("--port", default=None, help="Serial port, e.g. COM5")

    monitor = sub.add_parser("monitor", help="Open serial monitor")
    monitor.add_argument("--port", default=None, help="Serial port, e.g. COM5")
    monitor.add_argument("--baudrate", type=int, default=DEFAULT_BAUDRATE)

    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = _parser().parse_args(argv)

    try:
        if args.command == "list-ports":
            _list_ports()
            return 0

        if args.command == "deploy" and getattr(args, "prompt_device_ready", False):
            _prompt_device_ready()

        port = _find_mello_port(getattr(args, "port", None))
        print(f"Using port: {port}")

        if args.command == "deploy":
            _deploy(
                port=port,
                source=args.source,
                target=args.target,
                settings_source=args.settings_source,
                with_assets=args.with_assets,
                assets_dir=args.assets_dir,
                asset_manifest=args.asset_manifest,
                assets_target_root=args.assets_target_root,
                with_secrets=args.with_secrets,
                secrets_source=args.secrets_source,
                secrets_target=args.secrets_target,
            )
        elif args.command == "reboot":
            _reboot(port=port)
        elif args.command == "monitor":
            _monitor(port=port, baudrate=args.baudrate)
        else:
            raise RuntimeError(f"Unknown command: {args.command}")

        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
