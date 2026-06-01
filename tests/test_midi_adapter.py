"""Tests for MidiManager (mocked mido backend)."""

from unittest.mock import MagicMock, patch

import pytest

from rig.midi.adapter import MidiConnectionError, MidiManager


@pytest.fixture
def midi():
    """MidiManager backed by mocked mido."""
    with patch("rig.midi.adapter._HAS_MIDO", True):
        yield MidiManager()


class TestPortDiscovery:
    def test_list_ports_returns_names(self, midi):
        with patch("rig.midi.adapter.mido.get_output_names", return_value=["Port A", "Port B"]):
            assert midi.list_output_ports() == ["Port A", "Port B"]

    def test_list_ports_empty_when_no_backend(self):
        with patch("rig.midi.adapter._HAS_MIDO", False):
            m = MidiManager()
            assert m.list_output_ports() == []

    def test_list_ports_handles_backend_error(self, midi):
        with patch(
            "rig.midi.adapter.mido.get_output_names", side_effect=RuntimeError("no backend")
        ):
            assert midi.list_output_ports() == []


class TestConnection:
    def test_connect_opens_and_stores_port(self, midi):
        fake_port = MagicMock()
        with patch("rig.midi.adapter.mido.open_output", return_value=fake_port) as mock_open:
            midi.connect("My Interface", "hx-stomp")
            mock_open.assert_called_once_with("My Interface")
            assert midi.is_connected("hx-stomp") is True

    def test_connect_shares_port_by_name(self, midi):
        fake_port = MagicMock()
        with patch("rig.midi.adapter.mido.open_output", return_value=fake_port) as mock_open:
            midi.connect("Shared Port", "hx-stomp")
            midi.connect("Shared Port", "brothers")
            # Port opened only once
            mock_open.assert_called_once_with("Shared Port")
            assert midi.is_connected("hx-stomp") is True
            assert midi.is_connected("brothers") is True

    def test_connect_raises_on_failure(self, midi):
        with patch("rig.midi.adapter.mido.open_output", side_effect=OSError("port busy")):
            with pytest.raises(MidiConnectionError, match="Could not open"):
                midi.connect("Busy Port", "device-x")
            assert midi.is_connected("device-x") is False

    def test_connect_raises_when_no_mido(self):
        with patch("rig.midi.adapter._HAS_MIDO", False):
            m = MidiManager()
            with pytest.raises(MidiConnectionError, match="mido library"):
                m.connect("Any Port", "device-x")

    def test_is_connected_false_when_not_connected(self, midi):
        assert midi.is_connected("nonexistent") is False

    def test_disconnect_removes_device(self, midi):
        fake_port = MagicMock()
        with patch("rig.midi.adapter.mido.open_output", return_value=fake_port):
            midi.connect("P", "d1")
            midi.disconnect("d1")
            assert midi.is_connected("d1") is False
            fake_port.close.assert_called_once()

    def test_disconnect_keeps_port_when_shared(self, midi):
        fake_port = MagicMock()
        with patch("rig.midi.adapter.mido.open_output", return_value=fake_port):
            midi.connect("P", "d1")
            midi.connect("P", "d2")
            midi.disconnect("d1")
            # Port stays open because d2 still uses it
            fake_port.close.assert_not_called()
            assert midi.is_connected("d2") is True

    def test_disconnect_all_closes_everything(self, midi):
        fake_port = MagicMock()
        with patch("rig.midi.adapter.mido.open_output", return_value=fake_port):
            midi.connect("P1", "d1")
            midi.connect("P2", "d2")
            midi.disconnect_all()
            assert midi.is_connected("d1") is False
            assert midi.is_connected("d2") is False
            assert fake_port.close.call_count == 2


class TestSending:
    def test_send_program_change(self, midi):
        fake_port = MagicMock()
        with (
            patch("rig.midi.adapter.mido.open_output", return_value=fake_port),
            patch("rig.midi.adapter.mido.Message") as mock_msg,
        ):
            midi.connect("P", "hx-stomp")
            midi.send_program_change("hx-stomp", 12, 1)
            mock_msg.assert_called_once_with("program_change", program=12, channel=1)
            fake_port.send.assert_called_once()

    def test_send_program_change_to_nonexistent_device(self, midi):
        with pytest.raises(MidiConnectionError, match="no open MIDI"):
            midi.send_program_change("ghost", 1, 1)

    def test_send_control_change(self, midi):
        fake_port = MagicMock()
        with (
            patch("rig.midi.adapter.mido.open_output", return_value=fake_port),
            patch("rig.midi.adapter.mido.Message") as mock_msg,
        ):
            midi.connect("P", "mood")
            midi.send_control_change("mood", 14, 64, 5)
            mock_msg.assert_called_once_with("control_change", control=14, value=64, channel=5)
            fake_port.send.assert_called_once()

    def test_send_raises_when_no_mido(self):
        with patch("rig.midi.adapter._HAS_MIDO", False):
            m = MidiManager()
            with pytest.raises(MidiConnectionError, match="mido library"):
                m.send_program_change("x", 1, 1)
