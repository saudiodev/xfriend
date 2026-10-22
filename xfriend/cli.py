"""xfriend CLI: init / run / doctor."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import typer

from xfriend.config import default_config_yaml, load_config

app = typer.Typer(no_args_is_help=True, add_completion=False)


def _err(msg: str) -> None:
    typer.secho(f"error: {msg}", fg=typer.colors.RED, err=True)
    raise typer.Exit(1)


@app.command()
def init(name: str = typer.Argument(..., help="Companion name / directory")):
    """Scaffold a new companion directory with xfriend.yaml + persona.md."""
    target = Path(name)
    if target.exists() and any(target.iterdir()):
        _err(f"directory {name!r} exists and is not empty")
    target.mkdir(parents=True, exist_ok=True)
    (target / "xfriend.yaml").write_text(default_config_yaml(name), encoding="utf-8")
    persona = (target / "persona.md").write_text(
        f"# {name}\n\nYou are {name}. Write your personality, appearance, "
        "history, and preferences here. Keep the voice natural and consistent.\n",
        encoding="utf-8",
    )
    typer.echo(f"Created {name}/xfriend.yaml and {name}/persona.md")
    typer.echo(f"Edit them, set your API keys, then run: xfriend run --config {name}/xfriend.yaml")


@app.command()
def run(
    config: Path = typer.Option("xfriend.yaml", "--config", "-c", help="Path to xfriend.yaml"),
    once: str = typer.Option(None, "--once", "-o", help="Send one message and exit"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Only print replies"),
):
    """Start an interactive chat with the companion (or send one message)."""
    from xfriend.orchestrator import build_from_file

    if not config.exists():
        _err(f"config not found: {config} (run `xfriend init <name>` first)")
    companion = build_from_file(str(config))
    typer.echo(f"companion: {companion}")

    if once is not None:
        reply = companion.chat(once)
        _print_reply(reply, quiet)
        companion.close()
        return

    try:
        while True:
            try:
                line = input("you> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not line:
                continue
            if line.lower() in (":q", ":quit", ":exit"):
                break
            reply = companion.chat(line)
            _print_reply(reply, quiet)
    finally:
        companion.close()
        typer.echo("\n(saved memory & facts)")


def _print_reply(reply, quiet: bool) -> None:
    if not quiet:
        typer.echo("companion> ", nl=False)
    typer.echo(reply.text)
    for media in reply.media:
        if media.type == "image":
            typer.echo(f"   [image] {media.url or media.path}")
        elif media.type == "audio":
            typer.echo(f"   [voice] {media.path}")
            if media.duration_secs is not None:
                typer.echo(f"           {media.duration_secs:.1f}s")


@app.command()
def doctor(config: Path = typer.Option("xfriend.yaml", "--config", "-c")):
    """Check config, API keys, base image, and module wiring."""
    if not config.exists():
        _err(f"config not found: {config}")
    try:
        cfg = load_config(str(config))
    except Exception as exc:
        _err(f"failed to load config: {exc}")

    ok = True

    def check(label: str, good: bool, detail: str = "") -> None:
        nonlocal ok
        color = typer.colors.GREEN if good else typer.colors.RED
        mark = "ok" if good else "FAIL"
        typer.echo(f"  [{mark}] {label}" + (f" — {detail}" if detail else ""))
        if not good:
            ok = False

    typer.echo(f"companion: {cfg.name}")
    typer.echo("llm:")
    check(f"provider {cfg.llm.provider} api key", bool(cfg.llm.api_key),
          "set " + cfg.llm.preset.get("env_key", "the provider env var"))
    check(f"model {cfg.llm.model}", bool(cfg.llm.model))
    typer.echo("image:")
    if cfg.image.enabled:
        check("enabled — api key", bool(cfg.image.api_key), "set WAVESPEED_API_KEY")
        if cfg.image.base_image and not cfg.image.base_image.startswith(("http", "data:")):
            check("base_image exists", Path(cfg.image.base_image).exists(), cfg.image.base_image)
        else:
            check("base_image set", bool(cfg.image.base_image))
        check("loras", True, f"{len(cfg.image.loras)} configured (optional)")
    else:
        typer.echo("  [--] disabled")
    typer.echo("voice:")
    if cfg.voice.enabled:
        check("enabled — api key", bool(cfg.voice.api_key), "set SECRETVOICE_API_KEY")
        check("voice_id", bool(cfg.voice.voice_id), cfg.voice.voice_id)
    else:
        typer.echo("  [--] disabled")
    typer.echo("memory:")
    check("store", cfg.memory.store in ("json", "inmemory"), cfg.memory.store)
    check(f"keep_messages={cfg.memory.keep_messages} + compact_batch={cfg.memory.compact_batch}",
          True)
    typer.echo("")
    typer.echo("ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED (see above)")
    raise typer.Exit(0 if ok else 1)


def main():
    app()


if __name__ == "__main__":
    main()