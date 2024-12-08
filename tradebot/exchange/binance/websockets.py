from typing import Literal, Callable
from typing import Any
from asynciolimiter import Limiter


from tradebot.base import WSClient
from tradebot.exchange.binance.constants import BinanceAccountType


class BinanceWSClient(WSClient):
    def __init__(self, account_type: BinanceAccountType, handler: Callable[..., Any]):
        self._account_type = account_type
        url = account_type.ws_url
        super().__init__(url, limiter=Limiter(3 / 1), handler=handler)

    async def _subscribe(self, params: str, subscription_id: str):
        if subscription_id not in self._subscriptions:
            await self.connect()
            id = self._clock.timestamp_ms()
            payload = {
                "method": "SUBSCRIBE",
                "params": [params],
                "id": id,
            }
            self._subscriptions[subscription_id] = payload
            await self._send(payload)
            self._log.info(f"Subscribing to {subscription_id}...")
        else:
            self._log.info(f"Already subscribed to {subscription_id}")

    async def subscribe_agg_trade(self, symbol: str):
        if (
            self._account_type.is_isolated_margin_or_margin
            or self._account_type.is_portfolio_margin
        ):
            raise ValueError(
                "Not Supported for `Margin Account` or `Portfolio Margin Account`"
            )
        subscription_id = f"agg_trade.{symbol}"
        params = f"{symbol.lower()}@aggTrade"
        await self._subscribe(params, subscription_id)

    async def subscribe_trade(self, symbol: str):
        if (
            self._account_type.is_isolated_margin_or_margin
            or self._account_type.is_portfolio_margin
        ):
            raise ValueError(
                "Not Supported for `Margin Account` or `Portfolio Margin Account`"
            )
        subscription_id = f"trade.{symbol}"
        params = f"{symbol.lower()}@trade"
        await self._subscribe(params, subscription_id)

    async def subscribe_book_ticker(self, symbol: str):
        if (
            self._account_type.is_isolated_margin_or_margin
            or self._account_type.is_portfolio_margin
        ):
            raise ValueError(
                "Not Supported for `Margin Account` or `Portfolio Margin Account`"
            )
        subscription_id = f"book_ticker.{symbol}"
        params = f"{symbol.lower()}@bookTicker"
        await self._subscribe(params, subscription_id)

    async def subscribe_mark_price(
        self, symbol: str, interval: Literal["1s", "3s"] = "1s"
    ):
        if not self._account_type.is_future:
            raise ValueError("Only Supported for `Future Account`")
        subscription_id = f"mark_price.{symbol}"
        params = f"{symbol.lower()}@markPrice@{interval}"
        await self._subscribe(params, subscription_id)

    async def subscribe_user_data_stream(self, listen_key: str):
        subscription_id = "user_data_stream"
        await self._subscribe(listen_key, subscription_id)

    async def subscribe_kline(
        self,
        symbol: str,
        interval: Literal[
            "1s",
            "1m",
            "3m",
            "5m",
            "15m",
            "30m",
            "1h",
            "2h",
            "4h",
            "6h",
            "8h",
            "12h",
            "1d",
            "3d",
            "1w",
            "1M",
        ],
    ):
        if (
            self._account_type.is_isolated_margin_or_margin
            or self._account_type.is_portfolio_margin
        ):
            raise ValueError(
                "Not Supported for `Margin Account` or `Portfolio Margin Account`"
            )
        subscription_id = f"kline.{symbol}.{interval}"
        params = f"{symbol.lower()}@kline_{interval}"
        await self._subscribe(params, subscription_id)

    async def _resubscribe(self):
        for _, payload in self._subscriptions.items():
            await self._send(payload)


