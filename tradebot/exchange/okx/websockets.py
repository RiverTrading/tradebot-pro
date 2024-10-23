import time
import asyncio

from typing import Literal
from typing import Any, Dict
from decimal import Decimal

from asynciolimiter import Limiter


from tradebot.types import (
    BookL1,
    Trade,
    Kline,
    MarkPrice,
    FundingRate,
    IndexPrice,
    Order,
)
from tradebot.entity import EventSystem
from tradebot.base import WSManager
from tradebot.constants import EventType


from tradebot.exchange.okx.constants import STREAM_URLS
from tradebot.exchange.okx.constants import OkxAccountType


class OkxWSManager(WSManager):
    def __init__(
        self,
        account_type: OkxAccountType,
        market: Dict[str, Any],
        market_id: Dict[str, Any],
        api_key: str = None,
        secret: str = None,
        passphrase: str = None,
    ):
        if api_key or secret or passphrase:
            url = f"{STREAM_URLS[account_type]}/v5/private"
        else:
            url = f"{STREAM_URLS[account_type]}/v5/public"

        super().__init__(url, limiter=Limiter(2 / 1), handler=self._callback)
        self._exchange_id = "okx"
        self._market = market
        self._market_id = market_id
        self._api_key = api_key
        self._secret = secret
        self._passphrase = passphrase

    async def subscribe_book_l1(self, symbol: str):
        channel = "bbo-tbt"

        market = self._market.get(symbol, None)
        symbol = market["id"] if market else symbol

        subscription_id = f"{channel}.{symbol}"

        if subscription_id not in self._subscriptions:
            await self._limiter.wait()
            payload = {
                "op": "subscribe",
                "args": [{"channel": channel, "instId": symbol}],
            }
            self._subscriptions[subscription_id] = payload
            self._send(payload)
        else:
            print(f"Already subscribed to {subscription_id}")

    async def subscribe_trade(self, symbol: str):
        channel = "trades"

        market = self._market.get(symbol, None)
        symbol = market["id"] if market else symbol

        subscription_id = f"{channel}.{symbol}"

        if subscription_id not in self._subscriptions:
            await self._limiter.wait()
            payload = {
                "op": "subscribe",
                "args": [{"channel": channel, "instId": symbol}],
            }
            self._subscriptions[subscription_id] = payload
            self._send(payload)
        else:
            print(f"Already subscribed to {subscription_id}")

    async def subscribe_kline(self, symbol: str, interval: str):
        pass

    async def _resubscribe(self):
        pass

    def _callback(self, msg):
        if "event" in msg:
            if msg["event"] == "error":
                self._log.error(str(msg))
            elif msg["event"] == "subscribe":
                pass
            elif msg["event"] == "login":
                self._log.info(f"Login successful: {msg}")
            elif msg["event"] == "channel-conn-count":
                self._log.info(f"Channel connection count: {msg['connCount']}")
        elif "arg" in msg:
            channel = msg["arg"]["channel"]
            match channel:
                case "bbo-tbt":
                    self._parse_bbo_tbt(msg)
                case "trades":
                    self._parse_trade(msg)

    def _parse_trade(self, msg):
        """
        {
            "arg": {
                "channel": "trades",
                "instId": "BTC-USD-191227"
            },
            "data": [
                {
                    "instId": "BTC-USD-191227",
                    "tradeId": "9",
                    "px": "0.016",
                    "sz": "50",
                    "side": "buy",
                    "ts": "1597026383085"
                }
            ]
        }
        """
        data = msg["data"][0]
        id = msg["arg"]["instId"]
        market = self._market_id[id]

        trade = Trade(
            exchange=self._exchange_id,
            symbol=market["symbol"],
            price=float(data["px"]),
            size=float(data["sz"]),
            timestamp=int(data["ts"]),
        )
        EventSystem.emit(EventType.TRADE, trade)

    def _parse_bbo_tbt(self, msg):
        """
        {
            'arg': {
                'channel': 'bbo-tbt',
                'instId': 'BTC-USDT'
            },
            'data': [{
                'asks': [['67201.2', '2.17537208', '0', '7']],
                'bids': [['67201.1', '1.44375999', '0', '5']],
                'ts': '1729594943707',
                'seqId': 34209632254
            }]
        }
        """
        data = msg["data"][0]
        id = msg["arg"]["instId"]
        market = self._market_id[id]

        bookl1 = BookL1(
            exchange=self._exchange_id,
            symbol=market["symbol"],
            bid=float(data["bids"][0][0]),
            ask=float(data["asks"][0][0]),
            bid_size=float(data["bids"][0][1]),
            ask_size=float(data["asks"][0][1]),
            timestamp=int(data["ts"]),
        )
        EventSystem.emit(EventType.BOOKL1, bookl1)