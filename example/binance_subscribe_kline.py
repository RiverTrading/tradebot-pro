import asyncio
import ccxt
import pickle
import os
from tradebot.exchange._binance import BinanceWebsocketManager
from tradebot.constants import Url

market_id = {}

market = ccxt.binance().load_markets()
for _, v in market.items():
    if v["subType"] == "linear":
        market_id[f"{v['id']}_swap"] = v
    elif v["type"] == "spot":
        market_id[f"{v['id']}_spot"] = v
    else:
        market_id[v["id"]] = v

event_data = []

def cb_cm_future(msg):
    event_data.append(msg)


def cb_um_future(msg):
    event_data.append(msg)


def cb_spot(msg):
    event_data.append(msg)


async def main():
    try:
        ws_spot_client = BinanceWebsocketManager(Url.Binance.Spot)
        ws_um_client = BinanceWebsocketManager(Url.Binance.UsdMFuture)
        ws_cm_client = BinanceWebsocketManager(Url.Binance.CoinMFuture)
        await ws_cm_client.subscribe_kline(
            "BTCUSD_PERP", interval="1m", callback=cb_cm_future
        )
        await ws_um_client.subscribe_kline(
            "BTCUSDT", interval="1m", callback=cb_um_future
        )
        await ws_um_client.subscribe_agg_trade(
            "BTCUSDT", callback=cb_um_future
        )
        
        await ws_um_client.subscribe_book_ticker(
            "BTCUSDT", callback=cb_um_future
        )
        
        await ws_spot_client.subscribe_kline("BTCUSDT", interval="1s", callback=cb_spot)
        await ws_spot_client.subscribe_klines(
            ["ETHUSDT", "SOLOUSDT"], interval="1s", callback=cb_spot
        )

        while True:
            await asyncio.sleep(1)

    except asyncio.CancelledError:
        await ws_spot_client.close()
        await ws_um_client.close()
        
        folder = "benchmark/data"
        
        if not os.path.exists(folder):
            os.makedirs(folder)
        
        path_file = os.path.join(folder, "data.pickle")
        
        
        with open(path_file, "wb") as f:
            pickle.dump(event_data, f)
        
        print("Websocket closed")


if __name__ == "__main__":
    asyncio.run(main())
