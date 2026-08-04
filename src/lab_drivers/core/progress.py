"""Replacement for the console ``loading`` helper the drivers were written against.

The original ``loading`` module was a console spinner/progress-bar utility that
lived in the application this driver layer was extracted from. It did not come
across -- deliberately, since progress indicators are the orchestration concern
this package excludes -- but the imports did, so several drivers still reference
it. Four of them (`Keysight34460A`, `RigolDP832`, `RigolDS7034`, `U1233A`)
imported it unconditionally and therefore could not be imported at all.

This module supplies the same call surface with the display removed: waits are
plain sleeps, progress reports go to the log, and the prompt honours the same
non-interactive rule as :mod:`lab_drivers.core.ports` -- an unattended process
raises instead of blocking forever on a terminal nobody is watching.

The class keeps its original lowercase name so the existing call sites
(``self.loading.delay_with_loading_indicator(...)``) need no changes.
"""

from __future__ import annotations

import time

from lab_drivers.core.log import get_logger
from lab_drivers.core.ports import can_prompt

_log = get_logger(__name__)


class loading:  # noqa: N801 - matches the historical module's class name
    """Headless stand-in for the console progress helper."""

    def __init__(self, interactive: bool | None = None) -> None:
        #: None = decide from whether stdin is a terminal.
        self.interactive = interactive

    def delay_with_loading_indicator(self, seconds: float, text: str = "") -> None:
        """Wait, without drawing anything."""
        if text:
            _log.debug("%s (%.3gs)", text, seconds)
        time.sleep(max(0.0, seconds))

    def display_loading_bar(self, fraction: float, loading_text: str = "") -> None:
        """Report progress to the log instead of redrawing a bar."""
        _log.debug("%s %.0f%%", loading_text or "progress", max(0.0, min(1.0, fraction)) * 100)

    def input_with_flashing(self, prompt: str = "") -> str:
        """Ask the operator a question, or refuse when nobody can answer.

        Raises:
            RuntimeError: this process has no terminal to prompt on. Callers
                that must run unattended should supply the value up front
                rather than reaching a prompt at all.
        """
        if not can_prompt(self.interactive):
            raise RuntimeError(
                f"Interactive input is required but unavailable: {prompt.strip() or 'prompt'}. "
                f"Supply the value directly instead of relying on a prompt."
            )
        return input(prompt)
