"""Abstract multimeter interface and helper implementations.

This module defines `Multimeter`, an abstract base class describing the
operations typically needed when controlling or reading from a digital
multimeter (DMM). Concrete backends (pyvisa, simulator, serial, etc.)
should subclass `Multimeter` and implement the abstract primitives.

The base class provides useful default behavior for averaging,
calibration offsets, streaming, and config persistence.
"""

from __future__ import annotations

import abc
import json
import re
import threading
import time
from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Tuple,
)


class Multimeter(abc.ABC):
    """Abstract multimeter interface.

    Subclasses must implement transport primitives (`list_resources`,
    `connect`, `disconnect`, `write`, `query`, and `measure_raw`). The
    base class implements averaging, simple streaming, calibration
    offsets, config persistence, and helpers like `identify()`.
    """

    DEFAULT_MODES = ("VDC", "VAC", "A", "OHM", "HZ", "CAP")

    def __init__(self) -> None:
        # connection state
        self.connected: bool = False
        self.resource: Optional[str] = None

        # acquisition state
        self.mode: str = "VDC"
        self.range: str = "AUTO"

        # calibration offsets to apply (additive): final = raw + offset
        self.calibration: Dict[str, float] = {m: 0.0 for m in self.DEFAULT_MODES}

        # averaging
        self.averaging_enabled: bool = False
        self.averaging_count: int = 1

        # profile / custom command overrides (for vendor-specific mappings)
        self.profile: str = "generic"
        self.custom_cmds: Dict[str, str] = {}

        # streaming helpers
        self._stream_thread: Optional[threading.Thread] = None
        self._stream_stop: threading.Event = threading.Event()

    # -----------------------------
    # Transport / lifecycle (abstract)
    # -----------------------------
    @staticmethod
    @abc.abstractmethod
    def list_resources() -> List[str]:
        """Return available resources for this platform/back-end.

        Implementations must return a list of resource strings.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def connect(
        self,
        resource: Optional[str] = None,
        *,
        simulate: bool = False,
        timeout_ms: Optional[int] = None,
    ) -> None:
        """Open a connection to `resource` (or start simulation).

        Implementations should set `self.connected` and `self.resource`.
        """

    @abc.abstractmethod
    def disconnect(self) -> None:
        """Close the connection and cleanup resources."""

    # Low-level command primitives (abstract)
    @abc.abstractmethod
    def write(self, cmd: str) -> None:
        """Send a command to the instrument. No response expected."""
        raise NotImplementedError()

    @abc.abstractmethod
    def query(self, cmd: str, timeout_ms: Optional[int] = None) -> str:
        """Send a query and return the raw reply string."""

    @abc.abstractmethod
    def measure_raw(self) -> Tuple[float, str]:
        """Perform a single, raw measurement and return (value, unit).

        This should not apply calibration or averaging — those are handled
        by the base class `measure()` helper.
        """

    # -----------------------------
    # Convenience helpers (base implementations)
    # -----------------------------
    def is_connected(self) -> bool:
        """Return True if the instrument connection is open."""
        return bool(self.connected)

    def identify(self) -> Optional[str]:
        """Return device identity string using `*IDN?` when available.

        Subclasses that don't support `query` should override this.
        """
        try:
            return self.query("*IDN?")
        except Exception:
            return None

    def set_mode(self, mode: str) -> None:
        """Set measurement mode (e.g. `VDC`, `VAC`, `A`, `OHM`, `HZ`)."""
        self.mode = mode

    # -----------------------------
    # Resistance / Capacitance helpers
    # -----------------------------
    def measure_resistance(self) -> Tuple[float, str]:
        """Convenience: set mode to resistance and measure.

        Returns (value, unit)."""
        if self.mode != "OHM":
            self.set_mode("OHM")
        return self.measure()

    def set_resistance_range(self, rng: str) -> None:
        """Set the resistance measurement range (e.g. 'AUTO', '5E3')."""
        if self.mode != "OHM":
            self.set_mode("OHM")
        self.set_range(rng)

    def measure_capacitance(self) -> Tuple[float, str]:
        """Convenience: set mode to capacitance and measure.

        Returns (value, unit).
        """
        if self.mode != "CAP":
            self.set_mode("CAP")
        return self.measure()

    def set_capacitance_range(self, rng: str) -> None:
        """Set the capacitance measurement range (e.g. 'AUTO', '50E-9')."""
        if self.mode != "CAP":
            self.set_mode("CAP")
        self.set_range(rng)

    def get_mode(self) -> str:
        return self.mode

    def set_range(self, rng: str) -> None:
        """Set measurement range string (e.g. `AUTO`, `5`, `50E-3`)."""
        self.range = rng

    def get_range(self) -> str:
        return self.range

    # Averaging / calibration
    def enable_averaging(self, enabled: bool) -> None:
        self.averaging_enabled = bool(enabled)

    def set_averaging_count(self, count: int) -> None:
        self.averaging_count = max(1, int(count))

    def set_calibration_offset(self, mode: str, offset: float) -> None:
        self.calibration[mode] = float(offset)

    def get_calibration_offset(self, mode: str) -> float:
        return float(self.calibration.get(mode, 0.0))

    # Measurement with averaging & calibration applied
    def measure(self) -> Tuple[float, str]:
        """Return a measurement applying averaging and calibration offsets.

        Calls the abstract `measure_raw()` which concrete backends must
        implement.
        """
        if self.averaging_enabled and self.averaging_count > 1:
            samples: List[float] = []
            unit = ""
            for _ in range(self.averaging_count):
                v, unit = self.measure_raw()
                samples.append(v)
                # small delay between samples — backends may choose different timings
                time.sleep(0.01)
            raw = sum(samples) / len(samples)
        else:
            raw, unit = self.measure_raw()

        offset = float(self.calibration.get(self.mode, 0.0))
        return raw + offset, unit

    # Config persistence
    def save_config(self, path: Optional[str] = None) -> None:
        if path is None:
            path = "calibration.json"
        data: Dict[str, Any] = {
            "calibration": self.calibration,
            "averaging": {
                "enabled": self.averaging_enabled,
                "count": self.averaging_count,
            },
            "profile": self.profile,
            "custom_cmds": self.custom_cmds,
        }
        with open(path, "w") as fh:
            json.dump(data, fh, indent=2)

    def load_config(self, path: Optional[str] = None) -> None:
        if path is None:
            path = "calibration.json"
        try:
            with open(path, "r") as fh:
                data = json.load(fh)
            self.calibration.update(data.get("calibration", {}))
            avg = data.get("averaging", {})
            self.averaging_enabled = bool(avg.get("enabled", self.averaging_enabled))
            try:
                self.averaging_count = int(avg.get("count", self.averaging_count))
            except Exception:
                pass
            prof = data.get("profile")
            if prof:
                self.profile = prof
            self.custom_cmds = data.get("custom_cmds", {}) or {}
        except FileNotFoundError:
            # silent fallback when config does not exist
            return

    # Simple streaming support
    def start_stream(
        self, callback: Callable[[float, str], None], interval: float = 0.15
    ) -> None:
        """Call `callback(value, unit)` periodically with measured values.

        The default implementation uses a background thread. Subclasses
        that require special handling may override.
        """
        if self._stream_thread and self._stream_thread.is_alive():
            return
        self._stream_stop.clear()

        def _loop() -> None:
            while not self._stream_stop.is_set():
                try:
                    v, u = self.measure()
                    try:
                        callback(v, u)
                    except Exception:
                        # swallow callback errors to keep streaming alive
                        pass
                except Exception:
                    # swallow measurement errors and continue
                    pass
                time.sleep(float(interval))

        self._stream_thread = threading.Thread(target=_loop, daemon=True)
        self._stream_thread.start()

    def stop_stream(self) -> None:
        if self._stream_thread and self._stream_thread.is_alive():
            self._stream_stop.set()
            self._stream_thread.join(timeout=1.0)
            self._stream_thread = None

    # Utility
    @staticmethod
    def parse_numeric_response(resp: str) -> float:
        """Extract and return the first numeric value from `resp`.

        Accepts scientific notation and returns a float. Raises `ValueError`
        if no numeric value can be found.
        """
        m = re.search(r"[-+]?\d*\.?\d+(?:[Ee][-+]?\d+)?", str(resp))
        if not m:
            raise ValueError("no numeric value in response")
        return float(m.group(0))
