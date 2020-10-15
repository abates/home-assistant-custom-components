"""Support to interact with a Music Player Daemon."""
from ssl import SSLCertVerificationError
import voluptuous as vol
from urllib.parse import urljoin

from homeassistant.components.mpd.media_player import MpdDevice
from homeassistant.components.mpd.media_player import (
    PLATFORM_SCHEMA as MPD_PLATFORM_SCHEMA,
)
from aiohttp.client_exceptions import ClientConnectorError
from homeassistant.helpers import aiohttp_client
from homeassistant.util import ssl

from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_NAME,
    CONF_URL,
    CONF_PASSWORD,
)

import homeassistant.helpers.config_validation as cv
import logging

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = MPD_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_URL): cv.string,
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the MPD platform."""
    host = config.get(CONF_HOST)
    port = config.get(CONF_PORT)
    name = config.get(CONF_NAME)
    http_url = config.get(CONF_URL)
    password = config.get(CONF_PASSWORD)

    device = MopidyDevice(hass, http_url, host, port, password, name)
    add_entities([device], True)


class MopidyDevice(MpdDevice):
    def __init__(self, hass, http_url, host, port, password, name):
        super().__init__(host, port, password, name)
        self.hass = hass
        self._url = http_url
        self._session = aiohttp_client.async_get_clientsession(hass)
        self._ssl_context = ssl.client_context()
        self._update = self.update
        self._image_url = None
        self._last_media_content_id = None
        self.update = None

    async def _get_image_url(self, uri):
        _LOGGER.debug(f"Getting image for {uri}")
        url = f"{self._url}/mopidy/rpc"
        data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "core.library.get_images",
            "params": [[uri]],
        }

        try:
            response = await self._session.request(
                "POST",
                url,
                json=data,
                ssl=self._ssl_context,
            )

            if response.status == 200:
                if response.content_type == "application/json":
                    data = await response.json()
                    if len(data["result"][uri]) > 0:
                        url = urljoin(self._url, data["result"][uri][0]["uri"])
                        _LOGGER.debug("Found artwork URL: %s", url)
                        return url
                    _LOGGER.debug("No artwork found")
                    return None
                _LOGGER.warning(
                    "Cannot process content type %s: %s",
                    response.content_type,
                    response,
                )
            else:
                _LOGGER.warning(
                    "Request %s failed with Server code %d",
                    url,
                    response.status,
                )
        except ClientConnectorError as ex:
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
            _LOGGER.warning("Request %s failed: %s", url, ex)
            raise ex
        return None

    async def async_update(self):
        await self.hass.async_add_executor_job(self._update)
        if self._is_connected:
            if self._last_media_content_id != self.media_content_id:
                self._image_url = await self._get_image_url(self.media_content_id)
            self._last_media_content_id = self.media_content_id
        else:
            self._image_url = None

    @property
    def media_image_url(self):
        """Image url of current playing media."""
        _LOGGER.debug("Returning image url: %s", self._image_url)
        return self._image_url
