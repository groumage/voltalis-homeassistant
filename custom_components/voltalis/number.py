"""Number platform for Voltalis integration."""

from homeassistant.components.number import NumberEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.voltalis.const import DOMAIN
from custom_components.voltalis.lib.domain.config_entry_data import VoltalisConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VoltalisConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Voltalis number entities."""
    
    client = entry.runtime_data.voltalis_client
    
    async_add_entities([VoltalisTokenLifetimeNumber(entry, client)])


class VoltalisTokenLifetimeNumber(NumberEntity):
    """Number entity to control token lifetime in days."""

    _attr_has_entity_name = True
    _attr_name = "Token lifetime"
    _attr_icon = "mdi:clock-outline"
    _attr_native_min_value = 1
    _attr_native_max_value = 999
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "days"

    def __init__(self, entry: VoltalisConfigEntry, client) -> None:
        """Initialize the number entity."""
        self._entry = entry
        self._client = client
        self._attr_unique_id = f"{entry.entry_id}_token_lifetime"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Token revocation",
            "manufacturer": "Voltalis",
            "model": "Revoke Token Button",
        }

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self._client._VoltalisClientAiohttp__token_max_age_days or 7

    async def async_set_native_value(self, value: float) -> None:
        """Set the token lifetime."""
        self._client._VoltalisClientAiohttp__token_max_age_days = int(value)
        self.async_write_ha_state()
