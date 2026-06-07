"""MidiManager: MIDI output port management for rig apply.

Shares port connections by port name so multiple device_ids routed
through the same physical interface open it only once.
"""

from __future__ import annotations

import logging
from typing import Any

from rig.config.errors import ConfigError

logger = logging.getLogger(__name__)

_HAS_MIDO = False
try:
    import mido  # noqa: F401 — used dynamically below

    _HAS_MIDO = True
except ImportError:
    pass


class MidiConnectionError(ConfigError):
    """MIDI port open or send failure."""


class MidiManager:
    """Manages MIDI output connections shared by port name.

    Usage::

        midi = MidiManager()
        ports = midi.list_output_ports()          # ["USB MIDI Interface", ...]
        midi.connect("USB MIDI Interface", "hx-stomp")
        midi.send_program_change("hx-stomp", 12, 1)
        midi.disconnect_all()
    """

    def __init__(self) -> None:
        self._ports: dict[str, Any] = {}  # port_name → mido.ports.BaseOutput
        self._device_ports: dict[str, str] = {}  # device_id → port_name

    # ------------------------------------------------------------------
    # Port discovery
    # ------------------------------------------------------------------

    def list_output_ports(self) -> list[str]:
        """Return available MIDI output port names.

        Returns an empty list when mido is not installed or the backend
        cannot be loaded (no MIDI hardware, missing rtmidi, etc.).
        """
        if not _HAS_MIDO:
            logger.debug("mido not available – no MIDI ports")
            return []
        try:
            import mido

            names = mido.get_output_names()
            logger.debug("Available MIDI output ports: %s", names)
            return names
        except Exception:
            logger.debug("Failed to enumerate MIDI ports", exc_info=True)
            return []

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self, port_name: str, device_id: str) -> None:
        """Open *port_name* and associate it with *device_id*.

        Raises MidiConnectionError on failure.
        """
        if not _HAS_MIDO:
            raise MidiConnectionError("mido library is not available")

        if port_name not in self._ports:
            try:
                import mido

                logger.debug("Opening MIDI output '%s'", port_name)
                self._ports[port_name] = mido.open_output(port_name)
                logger.info("MIDI output '%s' opened", port_name)
            except Exception as exc:
                msg = f"Could not open MIDI output '{port_name}': {exc}"
                logger.error(msg)
                raise MidiConnectionError(msg) from exc

        self._device_ports[device_id] = port_name
        logger.debug("Device '%s' → port '%s'", device_id, port_name)

    def is_connected(self, device_id: str) -> bool:
        """Return True when *device_id* has an open port."""
        port_name = self._device_ports.get(device_id)
        if port_name is None:
            return False
        return port_name in self._ports

    def disconnect(self, device_id: str) -> None:
        """Close the port for *device_id* (if last user)."""
        port_name = self._device_ports.pop(device_id, None)
        if port_name is None:
            return
        # Only close when no other device references this port
        if port_name not in self._device_ports.values():
            port = self._ports.pop(port_name, None)
            if port is not None:
                try:
                    port.close()
                    logger.debug("MIDI output '%s' closed", port_name)
                except Exception:
                    logger.warning("Error closing MIDI port '%s'", port_name, exc_info=True)

    def disconnect_all(self) -> None:
        """Close every open port."""
        for port_name in list(self._ports.keys()):
            port = self._ports.pop(port_name, None)
            if port is not None:
                try:
                    port.close()
                except Exception:
                    logger.warning("Error closing MIDI port '%s'", port_name, exc_info=True)
        self._device_ports.clear()
        logger.debug("All MIDI ports closed")

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    def _port_for(self, device_id: str) -> Any:
        """Return the open port for *device_id* or raise."""
        port_name = self._device_ports.get(device_id)
        if port_name is None:
            raise MidiConnectionError(f"Device '{device_id}' has no open MIDI connection")
        port = self._ports.get(port_name)
        if port is None:
            raise MidiConnectionError(
                f"Port '{port_name}' for device '{device_id}' is no longer open"
            )
        return port

    def send(self, device_id: str, message: Any) -> None:
        """Send a mido.Message on the device's associated port."""
        port = self._port_for(device_id)
        try:
            port.send(message)
            logger.debug("Sent %s on '%s'", message, self._device_ports.get(device_id))
        except Exception as exc:
            raise MidiConnectionError(f"MIDI send failed for '{device_id}': {exc}") from exc

    def send_program_change(self, device_id: str, program: int, channel: int) -> None:
        """Convenience: send a Program Change message."""
        if not _HAS_MIDO:
            raise MidiConnectionError("mido library is not available")
        import mido

        msg = mido.Message("program_change", program=program, channel=channel - 1)
        self.send(device_id, msg)

    def send_control_change(self, device_id: str, control: int, value: int, channel: int) -> None:
        """Convenience: send a Control Change message."""
        if not _HAS_MIDO:
            raise MidiConnectionError("mido library is not available")
        import mido

        msg = mido.Message("control_change", control=control, value=value, channel=channel - 1)
        self.send(device_id, msg)

    def send_sysex(self, device_id: str, data: list[int]) -> None:
        """Send a SysEx message. data must include the leading F0 and trailing F7."""
        if not _HAS_MIDO:
            raise MidiConnectionError("mido library is not available")
        import mido

        # mido's SysEx data field excludes the F0/F7 framing bytes
        msg = mido.Message("sysex", data=data[1:-1])
        self.send(device_id, msg)
