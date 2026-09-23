"""Fixtures."""

from pathlib import Path

import pytest

# pytest-homeassistant-custom-component ships its own `custom_components`
# package; add this repository's folder to it so the integration is found.
import custom_components

_REPO_COMPONENTS = str(Path(__file__).parent.parent / "custom_components")
if _REPO_COMPONENTS not in custom_components.__path__:
    custom_components.__path__.append(_REPO_COMPONENTS)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations in all tests."""
    yield
