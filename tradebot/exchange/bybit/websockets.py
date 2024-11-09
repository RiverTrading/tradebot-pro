import hmac
import orjson
import asyncio

from typing import Any, Callable
from asynciolimiter import Limiter


from tradebot.base import WSClient
from tradebot.exchange.bybit.constants import BybitAccountType

from nautilus_trader.common.component import LiveClock


class BybitWSClient(WSClient):
    def __init__(
        self,
        account_type: BybitAccountType,
        handler: Callable[..., Any],
        api_key: str = None,
        secret: str = None,
    ):
        self._account_type = account_type
        self._api_key = api_key
        self._secret = secret
        self._clock = LiveClock()
        self._authed = False
        if self.is_private:
            url = account_type.ws_private_url
        else:
            url = account_type.ws_public_url
        # Bybit: do not exceed 500 requests per 5 minutes
        super().__init__(
            url,
            limiter=Limiter(500 / 5 * 60),
            handler=handler,
            ping_idle_timeout=2,
            specific_ping_msg=None,
            auto_ping_strategy="ping_when_idle",
        )

    @property
    def is_private(self):
        return self._api_key is not None or self._secret is not None

    def _generate_signature(self):
        expires = self._clock.timestamp_ms() + 1_000
        signature = str(
            hmac.new(
                bytes(self._secret, "utf-8"),
                bytes(f"GET/realtime{expires}", "utf-8"),
                digestmod="sha256",
            ).hexdigest()
        )
        return signature, expires

    def _get_auth_payload(self):
        signature, expires = self._generate_signature()
        return {"op": "auth", "args": [self._api_key, expires, signature]}

    async def _auth(self):
        if not self._authed:
            await self._send(self._get_auth_payload())
            self._authed = True
            await asyncio.sleep(5)

    async def _subscribe(self, topic: str, auth: bool = False):
        if topic not in self._subscriptions:
            await self.connect()
            payload = {"op": "subscribe", "args": [topic]}
            if auth:
                await self._auth()
            self._subscriptions[topic] = payload
            await self._send(payload)
            self._log.debug(f"Subscribing to {topic}.{self._account_type.value}...")
        else:
            self._log.debug(f"Already subscribed to {topic}")

    async def subscribe_order_book(self, symbol: str, depth: int):
        """
        ### Linear & inverse:
        - Level 1 data, push frequency: 10ms
        - Level 50 data, push frequency: 20ms
        - Level 200 data, push frequency: 100ms
        - Level 500 data, push frequency: 100ms

        ### Spot:
        - Level 1 data, push frequency: 10ms
        - Level 50 data, push frequency: 20ms
        - Level 200 data, push frequency: 200ms

        ### Option:
        - Level 25 data, push frequency: 20ms
        - Level 100 data, push frequency: 100ms
        """
        topic = f"orderbook.{depth}.{symbol}"
        await self._subscribe(topic)

    async def subscribe_trade(self, symbol: str):
        topic = f"publicTrade.{symbol}"
        await self._subscribe(topic)

    async def subscribe_ticker(self, symbol: str):
        topic = f"tickers.{symbol}"
        await self._subscribe(topic)
    
    async def subscribe_kline(self, symbol: str, interval: int):
        """
        ### Available intervals:
        - 1 3 5 15 30 (min)
        - 60 120 240 360 720 (min)
        """
        topic = f"kline.{interval}.{symbol}"
        await self._subscribe(topic)

    async def _resubscribe(self):
        if self.is_private:
            self._authed = False
            await self._auth()
        for _, payload in self._subscriptions.items():
            await self._send(payload)