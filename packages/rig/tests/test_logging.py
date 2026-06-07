import logging

from rig.log_setup import _HANDLER_ATTR, setup_logging


def _rig_logger() -> logging.Logger:
    return logging.getLogger("rig")


def _rig_handlers():
    return [h for h in _rig_logger().handlers if getattr(h, _HANDLER_ATTR, False)]


class TestLoggingSetup:
    def teardown_method(self):
        """Reset rig logger between tests."""
        for handler in _rig_handlers():
            _rig_logger().removeHandler(handler)

    def test_setup_default_level_is_warning(self):
        setup_logging(verbose=0)
        assert _rig_logger().level == logging.WARNING

    def test_setup_verbose_level_is_info(self):
        setup_logging(verbose=1)
        assert _rig_logger().level == logging.INFO

    def test_setup_debug_level_is_debug(self):
        setup_logging(verbose=2)
        assert _rig_logger().level == logging.DEBUG

    def test_setup_verbose_3_still_debug(self):
        setup_logging(verbose=3)
        assert _rig_logger().level == logging.DEBUG

    def test_setup_does_not_propagate(self):
        setup_logging(verbose=1)
        assert not _rig_logger().propagate

    def test_setup_adds_rig_console_handler(self):
        setup_logging(verbose=1)
        assert len(_rig_handlers()) == 1

    def test_setup_is_idempotent(self):
        setup_logging(verbose=1)
        setup_logging(verbose=1)
        assert len(_rig_handlers()) == 1

    def test_setup_replaces_handler_on_level_change(self):
        setup_logging(verbose=1)
        setup_logging(verbose=2)
        assert len(_rig_handlers()) == 1
        assert _rig_logger().level == logging.DEBUG


def _get_module_loggers() -> list[str]:
    """Return list of module-level loggers we expect to exist."""
    return [
        "rig.config.loader",
        "rig.engine.apply",
        "rig.engine.plan",
        "rig.engine.diff",
        "rig.engine.state",
        "rig.ingest.hx_stomp",
        "rig.ingest.mc6_config",
    ]


class TestModuleLoggers:
    def test_all_modules_have_named_logger(self):
        for name in _get_module_loggers():
            logger = logging.getLogger(name)
            assert logger.name == name

    def test_module_loggers_propagate_to_rig(self):
        setup_logging(verbose=1)
        for name in _get_module_loggers():
            log = logging.getLogger(name)
            assert log.name == name
            assert log.getEffectiveLevel() == logging.INFO
