import asyncio
from tradebot.types import Trade
from tradebot.constants import WSType
from tradebot.strategy import Strategy
from tradebot.exchange.binance import (
    BinanceWSManager,
    BinanceAccountType,
    BinanceExchangeManager,
)


class Demo(Strategy):
    def __init__(self):
        super().__init__()
        self.market = {}

    def on_trade(self, trade: Trade):
        self.market[trade.symbol] = trade

    def on_tick(self, tick):
        spot = self.market.get("BTC/USDT", None)
        linear = self.market.get("BTC/USDT:USDT", None)
        if spot and linear:
            ratio = linear.price / spot.price - 1
            print(f"ratio: {ratio}")


async def main():
    try:
        exchange = BinanceExchangeManager({"exchange_id": "binance"})
        await exchange.load_markets()  # get `market` and `market_id` data

        ws_spot = BinanceWSManager(
            BinanceAccountType.SPOT,
            exchange.market,
            exchange.market_id,
        )

        ws_usdm = BinanceWSManager(
            BinanceAccountType.USD_M_FUTURE,
            exchange.market,
            exchange.market_id,
        )
        await ws_spot.connect()
        await ws_usdm.connect()

        demo = Demo()

        demo.add_ws_manager(WSType.BINANCE_SPOT, ws_spot)
        demo.add_ws_manager(WSType.BINANCE_USD_M_FUTURE, ws_usdm)

        await demo.subscribe_trade(WSType.BINANCE_SPOT, "BTC/USDT")
        await demo.subscribe_trade(WSType.BINANCE_USD_M_FUTURE, "BTC/USDT:USDT")

        await demo.run()

    except asyncio.CancelledError:
        await exchange.close()
        ws_usdm.disconnect()
        ws_spot.disconnect()


if __name__ == "__main__":
    asyncio.run(main())