import logging
from datetime import datetime, timedelta, timezone
from typing import Any, TypedDict

from aiohttp import ClientSession

from custom_components.voltalis.const import VOLTALIS_API_BASE_URL, VOLTALIS_API_LOGIN_ROUTE
from custom_components.voltalis.lib.application.providers.http_client import (
    HttpClientException,
    HttpClientResponse,
    TData,
)
from custom_components.voltalis.lib.domain.exceptions import VoltalisAuthenticationException
from custom_components.voltalis.lib.infrastructure.providers.http_client_aiohttp import HttpClientAioHttp


class VoltalisClientAiohttp(HttpClientAioHttp):
    """
    Aiohttp client for Voltalis API.
    It implements authentication and token management.
    """

    BASE_URL = VOLTALIS_API_BASE_URL
    LOGIN_ROUTE = VOLTALIS_API_LOGIN_ROUTE

    class Storage(TypedDict):
        """Dict that represent the storage of the client"""

        auth_token: str | None
        token_created_at: datetime | None
        default_site_id: str | None

    def __init__(
        self,
        *,
        session: ClientSession,
        base_url: str = BASE_URL,
    ) -> None:
        super().__init__(session=session, base_url=base_url)

        # Setup storage
        self.__storage = VoltalisClientAiohttp.Storage(
            auth_token=None,
            token_created_at=None,
            default_site_id=None,
        )
        self.__token_max_age_days: int | None = 7

        # Configure logger
        logger = logging.getLogger(__name__)
        self.__logger = logger

    @property
    def storage(self) -> "VoltalisClientAiohttp.Storage":
        """Get the aiohttp storage."""
        return self.__storage

    def _is_token_expired(self) -> bool:
        if self.__token_max_age_days is None:
            return False
        if self.__storage["token_created_at"] is None:
            return True
        
        token_age = datetime.now(timezone.utc) - self.__storage["token_created_at"]
        max_age = timedelta(days=self.__token_max_age_days)
        
        if token_age > max_age:
            self.__logger.debug(
                "Token age: %s days, max age: %s days",
                token_age.days,
                self.__token_max_age_days
            )
            return True
        
        return False

    async def get_access_token(
        self,
        *,
        username: str,
        password: str,
    ) -> str:
        """Get Voltalis access token."""

        payload = {
            "login": username,
            "password": password,
        }
        try:
            response: HttpClientResponse[dict] = await self.send_request(
                url=VoltalisClientAiohttp.LOGIN_ROUTE,
                method="POST",
                body=payload,
                can_retry=False,
            )
            del username
            del password
            return response.data["token"]
        except HttpClientException as err:
            self.__logger.error("Error while getting access token: %s", err)
            if err.response and err.response.status == 401:
                raise VoltalisAuthenticationException("Invalid username or password") from err
            raise err

    async def __get_me(self) -> str:
        response: HttpClientResponse[dict] = await self.send_request(
            url="/api/account/me",
            method="GET",
        )
        return response.data["defaultSite"]["id"]

    async def login(self, *, username: str, password: str) -> None:
        """Execute Voltalis login."""

        self.__logger.info("Voltalis login in progress...")
        token = await self.get_access_token(
            username=username,
            password=password,
        )

        del username
        del password

        self.__storage["auth_token"] = token
        self.__storage["token_created_at"] = datetime.now(timezone.utc)
        self.__storage["default_site_id"] = await self.__get_me()

        self.__logger.info("Voltalis login successful")

    async def logout(self) -> None:
        if self.__storage["auth_token"] is None:
            return

        self.__logger.info("Voltalis logout in progress...")
        await self.send_request(url="/auth/logout", method="DELETE")
        self.__logger.info("Logout successful")

        self.__storage["auth_token"] = None
        self.__storage["token_created_at"] = None
        self.__storage["default_site_id"] = None

    async def send_request(
        self,
        *,
        url: str,
        method: str,
        body: Any | None = None,
        query_params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> HttpClientResponse[TData]:
        """Send http requests to Voltalis."""

        if self.__storage["auth_token"] is not None and url != VoltalisClientAiohttp.LOGIN_ROUTE:
            if self._is_token_expired():
                self.__logger.warning(
                    "Token expired (age > %s days), forcing re-authentication",
                    self.__token_max_age_days
                )
                self.__storage["auth_token"] = None
                self.__storage["token_created_at"] = None

        if self.__storage["auth_token"] is None and url != VoltalisClientAiohttp.LOGIN_ROUTE:
            raise VoltalisAuthenticationException("No authentication token available. Please login first.")

        headers = {
            **{
                "content-type": "application/json",
                "accept": "*/*",
            },
            **(headers or {}),
        }
        if self.__storage["auth_token"] is not None:
            headers["Authorization"] = f"Bearer {self.__storage['auth_token']}"

        _url = url
        if self.__storage["default_site_id"] is not None:
            _url = url.format(site_id=self.__storage["default_site_id"])

        response: HttpClientResponse[TData] = await super().send_request(
            url=_url,
            method=method,
            body=body,
            query_params=query_params,
            headers=headers,
            **kwargs,
        )

        return response
