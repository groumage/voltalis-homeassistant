"""Button platform for Voltalis integration."""

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.voltalis.const import DOMAIN
from custom_components.voltalis.lib.domain.config_entry_data import VoltalisConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VoltalisConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Voltalis button entities."""
    
    client = entry.runtime_data.voltalis_client
    
    async_add_entities([VoltalisRevokeTokenButton(entry, client)])


class VoltalisRevokeTokenButton(ButtonEntity):
    """Button entity to revoke the authentication token."""

    _attr_has_entity_name = True
    _attr_name = "Revoke token"
    _attr_icon = "mdi:lock-reset"

    def __init__(self, entry: VoltalisConfigEntry, client) -> None:
        """Initialize the button entity."""
        self._entry = entry
        self._client = client
        self._attr_unique_id = f"{entry.entry_id}_revoke_token"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Token revocation",
            "manufacturer": "Voltalis",
            "model": "Revoke Token Button",
        }

    async def async_press(self) -> None:
        """Handle the button press - revoke the token."""
        self._client.storage["auth_token"] = None
        self._client.storage["token_created_at"] = None
