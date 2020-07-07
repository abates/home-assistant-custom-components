import asyncio
from functools import wraps
import logging
from pprint import pformat
from ssl import SSLCertVerificationError

import requests
import voluptuous as vol

from homeassistant.components.media_player import MediaPlayerEntity
from homeassistant.components.media_player.const import (
    SUPPORT_SELECT_SOURCE,
    SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON,
    SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_SET,
    SUPPORT_VOLUME_STEP,
)

from homeassistant.const import (
    ATTR_NAME,
    CONF_API_KEY,
    CONF_NAME,
    CONF_PORT,
    CONF_URL,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.helpers import aiohttp_client
import homeassistant.helpers.config_validation as cv
from homeassistant.util import ssl

DOMAIN = "monoprice_rest"
SUPPORT_MONOPRICE = (
    SUPPORT_VOLUME_MUTE
    | SUPPORT_VOLUME_SET
    | SUPPORT_VOLUME_STEP
    | SUPPORT_TURN_ON
    | SUPPORT_TURN_OFF
    | SUPPORT_SELECT_SOURCE
)

_LOGGER = logging.getLogger(__name__)

CONF_SOURCES = "sources"

SOURCE_IDS = vol.All(vol.Coerce(int), vol.Range(min=1, max=6))

SOURCE_SCHEMA = vol.Schema({vol.Required(CONF_NAME): str})

PLATFORM_SCHEMA = cv.PLATFORM_SCHEMA.extend(
    {
        vol.Required(ATTR_NAME): str,
        vol.Required(CONF_URL): str,
        vol.Required(CONF_API_KEY): str,
        vol.Required(CONF_SOURCES): vol.Schema({SOURCE_IDS: SOURCE_SCHEMA}),
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the media player platform."""
    _LOGGER.debug("Setting up monoprice_rest")
    zones = []

    source_id_name = {
        int(index): value["name"] for index, value in config[CONF_SOURCES].items()
    }

    source_name_id = {v: k for k, v in source_id_name.items()}
    source_names = sorted(source_name_id.keys(), key=lambda v: source_name_id[v])
    sources = [source_id_name, source_name_id, source_names]

    session = aiohttp_client.async_get_clientsession(hass)

    monoprice = Monoprice(config.get(CONF_URL), config.get(CONF_API_KEY), session)

    zones = await monoprice.zones()
    if zones:
        entities = []
        for zone in zones:
            _LOGGER.debug(f"Setting up zone {zone}")
            entities.append(MonopriceZone(monoprice, sources, "monoprice_rest", zone))
        async_add_entities(entities)
    else:
        _LOGGER.warn("Failed to retrieve zones from server")


class Monoprice:
    def __init__(self, url, apiKey, session):
        self._url = url
        self._api_key = apiKey
        self._session = session
        self._context = ssl.client_context()

    async def _request(self, method, url):
        url = f"{self._url}/{url}"
        try:
            response = await self._session.request(
                method,
                url,
                ssl=self._context,
                headers={"X-Auth-Key": f"{self._api_key}"},
            )

            if response.status == 200:
                if response.content_type == "application/json":
                    return await response.json()
                else:
                    return await response.text()

            elif response.status == 401:
                _LOGGER.warning("Authentication failed, check API KEY")
            else:
                _LOGGER.warning(
                    "%s Request %s failed with Server code %d",
                    method,
                    url,
                    response.status,
                )
        except ConnectionError as ex:
            self._update_success = False
            _LOGGER.warning("Failed to connect to %s: %s", url, ex)
        except SSLCertVerificationError as ex:
            self._update_success = False
            _LOGGER.warning("SSL Verification failed")
        except ValueError as ex:
            self._update_success = False
            _LOGGER.warning("JSON decoding failed: %s", ex)
        except Exception as ex:
            self._update_success = False
            _LOGGER.warning("%s Request %s failed: %s", method, url, ex)
            raise ex

    async def get(self, url):
        return await self._request("GET", url)

    async def put(self, url):
        return await self._request("PUT", url)

    async def zones(self):
        zones = await self.get("zones")
        _LOGGER.debug(f"Got zones {zones}")
        return zones


class MonopriceZone(MediaPlayerEntity):
    """Representation of a Monoprice amplifier zone."""

    def __init__(self, monoprice, sources, namespace, zone_id):
        """Initialize new zone."""
        self._monoprice = monoprice
        # dict source_id -> source name
        self._source_id_name = sources[0]
        # dict source name -> source_id
        self._source_name_id = sources[1]
        # ordered list of all source names
        self._source_names = sources[2]
        self._zone_id = zone_id
        self._unique_id = f"{namespace}_{self._zone_id}"
        self._name = f"Zone {self._zone_id}"

        self._snapshot = None
        self._state = None
        self._volume = None
        self._source = None
        self._mute = None
        self._update_success = True

    async def async_update(self):
        """Retrieve latest state."""
        status = None
        state = await self._monoprice.get(f"{self._zone_id}/status")
        if not state:
            self._update_success = False
            return

        self._state = STATE_ON if state["power"] else STATE_OFF
        self._volume = state["volume"]
        self._mute = state["mute"]
        idx = state["source"]
        if idx in self._source_id_name:
            self._source = self._source_id_name[idx]
        else:
            self._source = None

    @property
    def entity_registry_enabled_default(self):
        """Return if the entity should be enabled when first added to the entity registry."""
        return self._zone_id < 20 or self._update_success

    @property
    def device_info(self):
        """Return device info for this device."""
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
            "manufacturer": "Monoprice",
            "model": "6-Zone Amplifier",
        }

    @property
    def unique_id(self):
        """Return unique ID for this device."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the zone."""
        return self._name

    @property
    def state(self):
        """Return the state of the zone."""
        return self._state

    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        if self._volume is None:
            return None
        return self._volume / 38.0

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        return self._mute

    @property
    def supported_features(self):
        """Return flag of media commands that are supported."""
        return SUPPORT_MONOPRICE

    @property
    def media_title(self):
        """Return the current source as medial title."""
        return self._source

    @property
    def source(self):
        """Return the current input source of the device."""
        return self._source

    @property
    def source_list(self):
        """List of available input sources."""
        return self._source_names

    async def snapshot(self):
        """Save zone's current state."""
        self._snapshot = await self._monoprice.zone_status(self._zone_id)

    async def restore(self):
        """Restore saved state."""
        if self._snapshot:
            await self._monoprice.put(
                f"{self._zone_id}/restore",
                {
                    "power": self._snapshot.power,
                    "mute": self._snapshot.mute,
                    "volume": self._snapshot.volume,
                    "treble": self._snapshot.treble,
                    "bass": self._snapshot.bass,
                    "balance": self._snapshot.balance,
                    "source": self._snapshot.source,
                },
            )
            self.schedule_update_ha_state(True)

    async def select_source(self, source):
        """Set input source."""
        if source not in self._source_name_id:
            return
        idx = self._source_name_id[source]
        await self._monoprice.put(f"{self._zone_id}/source/{idx}")

    async def turn_on(self):
        """Turn the media player on."""
        await self._monoprice.put(f"{self._zone_id}/power/True")

    async def turn_off(self):
        """Turn the media player off."""
        await self._monoprice.put(f"{self._zone_id}/power/False")

    async def mute_volume(self, mute):
        """Mute (true) or unmute (false) media player."""
        await self._monoprice.put(f"{self._zone_id}/mute/{mute}")

    async def set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        await self._monoprice.put(f"{self._zone_id}/volume/{int(volume * 38)}")

    async def volume_up(self):
        """Volume up the media player."""
        if self._volume is None:
            return
        await self._monoprice.put(f"{self._zone_id}/volume/{min(self._volume + 1, 38)}")

    async def volume_down(self):
        """Volume down media player."""
        if self._volume is None:
            return
        await self._monoprice.put(f"{self._zone_id}/volume/{max(self._volume - 1, 0)}")
