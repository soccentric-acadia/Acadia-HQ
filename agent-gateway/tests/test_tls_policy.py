"""T-P34 (HQ-030): the gateway refuses a plaintext listener in production."""

from gateway.config import GatewaySettings
from gateway.server import plaintext_refused


def _s(**kw):
    return GatewaySettings(_env_file=None, **kw)


def test_production_without_tls_is_refused():
    assert "refusing" in plaintext_refused("production", _s())


def test_tls_configured_is_allowed():
    assert plaintext_refused("production", _s(tls_cert_path="c", tls_key_path="k")) is None


def test_dev_and_test_may_run_plaintext():
    assert plaintext_refused("dev", _s()) is None
    assert plaintext_refused("test", _s()) is None


def test_explicit_tls_terminator_override():
    assert (
        plaintext_refused("production", _s(allow_insecure_behind_tls_terminator=True)) is None
    )
