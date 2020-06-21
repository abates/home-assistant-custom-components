import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.const import ATTR_NAME, CONF_URL, CONF_NAME, CONF_API_KEY
from homeassistant.components.monoprice.media_player import MonopriceZone

from pymonoprice import ZoneStatus
import requests
import logging
from pprint import pformat


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
    """Set up the sensor platform."""
    _LOGGER.debug("Setting up monoprice_rest")
    zones = []

    source_id_name = {
        int(index): value["name"] for index, value in config[CONF_SOURCES].items()
    }
    _LOGGER.warn(f"source id name: {source_id_name}")
    source_name_id = {v: k for k, v in source_id_name.items()}
    source_names = sorted(source_name_id.keys(), key=lambda v: source_name_id[v])
    sources = [source_id_name, source_name_id, source_names]

    _LOGGER.warn(f"SOURCES: {sources}")
    monoprice = Monoprice(config.get(CONF_URL), config.get(CONF_API_KEY))

    for zone in monoprice.zones():
        zones.append(MonopriceZone(monoprice, sources, "monoprice_rest", zone))

    async_add_entities(zones)


class Monoprice:
    def __init__(self, url, apiKey):
        self._url = url
        self._api_key = apiKey
        self._session = requests.Session()
        pass

    def _request(self, method, url):
        data = None
        try:
            params = dict(key=self._api_key)
            response = self._session.request(
                method, f"{self._url}/{url}", params=params,
            )

            if response.status_code == 200:
                data = response.json()
            elif response.status_code == 401:
                _LOGGER.warning("Authentication failed, check API KEY")
            else:
                _LOGGER.warning(
                    "Zone status update failed with HTTP code %d", response.status_code
                )
        except ConnectionError as ex:
            self._update_success = False
            _LOGGER.warning("Failed to connect to %s: %s", self._url, ex)
        except ValueError as ex:
            _LOGGER.warning("JSON decoding failed: %s", ex)
        except Exception as ex:
            _LOGGER.warning("Failed to retrieve zone status: %s", ex)

        return data

    def _get(self, url):
        return self._request("GET", url)

    def _put(self, url):
        return self._request("PUT", url)

    def zones(self):
        return self._get("zones")

    def zone_status(self, zone: int):
        status = None
        data = self._get(f"{zone}/status")
        if data:
            status = ZoneStatus(
                data["zone"],
                data["pa"],
                data["power"],
                data["mute"],
                data["do_not_disturb"],
                data["treble"],
                data["bass"],
                data["balance"],
                data["volume"],
                data["source"],
                data["keypad"],
            )
        return status

    def set_power(self, zone: int, power: bool):
        self._put(f"{zone}/power/{power}")

    def set_mute(self, zone: int, mute: bool):
        self._put(f"{zone}/mute/{mute}")

    def set_volume(self, zone: int, volume: int):
        self._put(f"{zone}/volume/{volume}")

    def set_treble(self, zone: int, treble: int):
        self._put(f"{zone}/treble/{treble}")

    def set_bass(self, zone: int, bass: int):
        self._put(f"{zone}/bass/{bass}")

    def set_balance(self, zone: int, balance: int):
        self._put(f"{zone}/balance/{balance}")

    def set_source(self, zone: int, source: int):
        self._put(f"{zone}/source/{source}")

    def restore_zone(self, status: ZoneStatus):
        self._put(
            f"{status.zone}/restore",
            {
                "power": status.power,
                "mute": status.mute,
                "volume": status.volume,
                "treble": status.treble,
                "bass": status.bass,
                "balance": status.balance,
                "source": status.source,
            },
        )
