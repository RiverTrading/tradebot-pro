import msgspec

from collections import defaultdict
from tradebot.base import PublicConnector, PrivateConnector
from tradebot.entity import EventSystem
from tradebot.types import BookL1
from tradebot.constants import EventType
from tradebot.exchange.bybit.types import (
    BybitWsMessageGeneral,
    BybitWsOrderbookDepthMsg,
    BybitOrderBook,
)
from tradebot.exchange.bybit.websockets import BybitWSClient
from tradebot.exchange.bybit.constants import BybitAccountType
from tradebot.exchange.bybit.exchange import BybitExchangeManager


class BybitPublicConnector(PublicConnector):
    def __init__(
        self,
        account_type: BybitAccountType,
        exchange: BybitExchangeManager,
    ):
        super().__init__(
            account_type=account_type,
            market=exchange.market,
            market_id=exchange.market_id,
            exchange_id=exchange.exchange_id,
            ws_client=BybitWSClient(
                account_type=account_type, handler=self._ws_msg_handler
            ),
        )
        self._ws_client: BybitWSClient = self._ws_client
        self._ws_msg_orderbook_decoder = msgspec.json.Decoder(BybitWsOrderbookDepthMsg)
        self._ws_msg_general_decoder = msgspec.json.Decoder(BybitWsMessageGeneral)

        self._orderbook = defaultdict(BybitOrderBook)

    @property
    def market_type(self):
        if self._account_type.is_spot:
            return "_spot"
        elif self._account_type.is_linear:
            return "_linear"
        elif self._account_type.is_inverse:
            return "_inverse"
        else:
            raise ValueError(f"Unsupported BybitAccountType.{self._account_type.value}")

    def _ws_msg_handler(self, raw: bytes):
        try:
            self._log.debug(str(raw))

            ws_msg: BybitWsMessageGeneral = self._ws_msg_general_decoder.decode(raw)

            if "orderbook" in ws_msg.topic:
                self._handle_orderbook(raw, ws_msg.topic)

        except Exception:
            self._log.error(f"Error decoding message: {str(raw)}")

    def _handle_orderbook(self, raw: bytes, topic: str):
        msg: BybitWsOrderbookDepthMsg = self._ws_msg_orderbook_decoder.decode(raw)
        id = msg.data.s + self.market_type
        market = self._market_id[id]
        symbol = market["symbol"]

        res = self._orderbook[symbol].parse_orderbook_depth(msg, levels=1)

        bookl1 = BookL1(
            exchange=self._exchange_id,
            symbol=symbol,
            timestamp=msg.ts,
            bid=res["bids"][0][0],
            bid_size=res["bids"][0][1],
            ask=res["asks"][0][0],
            ask_size=res["asks"][0][1],
        )

        EventSystem.emit(EventType.BOOKL1, bookl1)

    async def subscribe_bookl1(self, symbol: str):
        market = self._market.get(symbol, None)
        symbol = market["id"] if market else symbol
        await self._ws_client.subscribe_order_book(symbol, depth=1)

    async def subscribe_trade(self, symbol: str):
        pass

    async def subscribe_kline(self, symbol: str, interval: str):
        pass