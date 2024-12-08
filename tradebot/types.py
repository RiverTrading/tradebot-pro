import warnings
from decimal import Decimal
from collections import defaultdict
from typing import Any, Dict, List, Tuple
from typing import Literal, Optional
from msgspec import Struct, field
from tradebot.constants import (
    OrderSide,
    OrderType,
    TimeInForce,
    OrderStatus,
    PositionSide,
    AssetType,
)


class BookL1(Struct, gc=False):
    exchange: str
    symbol: str
    bid: float
    ask: float
    bid_size: float
    ask_size: float
    timestamp: int


class BookL2(Struct):
    exchange: str
    symbol: str
    bids: List[Tuple[float, float]]
    asks: List[Tuple[float, float]]
    timestamp: int


class Trade(Struct, gc=False):
    exchange: str
    symbol: str
    price: float
    size: float
    timestamp: int


class Kline(Struct, gc=False):
    exchange: str
    symbol: str
    interval: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: int


class MarkPrice(Struct, gc=False):
    exchange: str
    symbol: str
    price: float
    timestamp: int


class FundingRate(Struct, gc=False):
    exchange: str
    symbol: str
    rate: float
    timestamp: int
    next_funding_time: int


class IndexPrice(Struct, gc=False):
    exchange: str
    symbol: str
    price: float
    timestamp: int


class Order(Struct):
    exchange: str
    symbol: str
    status: OrderStatus
    id: Optional[str] = None
    amount: Optional[Decimal] = None
    filled: Optional[Decimal] = None
    client_order_id: Optional[str] = None
    timestamp: Optional[int] = None
    type: Optional[OrderType] = None
    side: Optional[OrderSide] = None
    time_in_force: Optional[TimeInForce] = None
    price: Optional[float] = None
    average: Optional[float] = None
    last_filled_price: Optional[float] = None
    last_filled: Optional[Decimal] = None
    remaining: Optional[Decimal] = None
    fee: Optional[float] = None
    fee_currency: Optional[str] = None
    cost: Optional[float] = None
    cum_cost: Optional[float] = None
    reduce_only: Optional[bool] = None
    position_side: Optional[PositionSide] = None

    @property
    def success(self) -> bool:
        return self.status != OrderStatus.FAILED


class Asset(Struct):
    """
    Buy BTC/USDT: amount = 0.01, cost: 600

    OrderStatus.INITIALIZED: BTC(free: 0.0, locked: 0.0) USDT(free: 1000, locked: 0)
    OrderStatus.PENDING: BTC(free: 0.0, locked: 0) USDT(free: 400, locked: 600) USDT.update_locked(600) USDT.update_free(-600)

    OrderStatus.PARTIALLY_FILLED: BTC(free: 0.005, locked: 0) USDT(free: 400, locked: 300) BTC.update_free(0.005) USDT.update_locked(-300)
    OrderStatus.FILLED: BTC(free: 0.01, locked: 0.0) USDT(free: 400, locked: 0) BTC.update_free(0.005) USDT.update_locked(-300)

    Buy BTC/USDT: amount = 0.01, cost: 200

    OrderStatus.INITIALIZED: BTC(free: 0.01, locked: 0.0) USDT(free: 400, locked: 0)
    OrderStatus.PENDING: BTC(free: 0.01, locked: 0.0) USDT(free: 200, locked: 200) USDT.update_locked(200) USDT.update_free(-200)
    OrderStatus.FILLED: BTC(free: 0.02, locked: 0.0) USDT(free: 200, locked: 0) BTC.update_free(0.01) USDT.update_locked(-200)

    Sell BTC/USDT: amount = 0.01, cost: 300
    OrderStatus.INITIALIZED: BTC(free: 0.02, locked: 0.0) USDT(free: 200, locked: 0)
    OrderStatus.PENDING: BTC(free: 0.01, locked: 0.01) USDT(free: 200, locked: 0) BTC.update_locked(0.01) BTC.update_free(-0.01)
    OrderStatus.PARTIALLY_FILLED: BTC(free: 0.01, locked: 0.005) USDT(free: 350, locked: 0) BTC.update_locked(-0.005) USDT.update_free(150)
    OrderStatus.FILLED: BTC(free: 0.01, locked: 0.0) USDT(free: 500, locked: 0) BTC.update_locked(-0.005) USDT.update_free(150)
    """

    asset: str
    free: Decimal = field(default=Decimal("0.0"))
    borrowed: Decimal = field(default=Decimal("0.0"))
    locked: Decimal = field(default=Decimal("0.0"))

    @property
    def total(self) -> Decimal:
        return self.free + self.locked

    def _update_free(self, amount: Decimal):
        """
        if amount > 0, then it is a buying action
        if amount < 0, then it is a selling action
        """
        self.free += amount

    def _update_borrowed(self, amount: Decimal):
        """
        if amount > 0, then it is a borrowing action
        if amount < 0, then it is a repayment action
        """
        self.borrowed += amount
        self.free += amount

    def _update_locked(self, amount: Decimal):
        """
        if amount > 0, then it is a new order action
        if amount < 0, then it is a cancellation/filled/partially filled action
        """
        self.locked += amount

    def _set_value(self, free: Decimal, borrowed: Decimal, locked: Decimal):
        if free is not None:
            self.free = free
        if borrowed is not None:
            self.borrowed = borrowed
        if locked is not None:
            self.locked = locked


class Precision(Struct):
    """
     "precision": {
      "amount": 0.0001,
      "price": 1e-05,
      "cost": null,
      "base": 1e-08,
      "quote": 1e-08
    },
    """

    amount: float | None = None
    price: float | None = None
    cost: float | None = None
    base: float | None = None
    quote: float | None = None


class LimitMinMax(Struct):
    """
    "limits": {
      "amount": {
        "min": 0.0001,
        "max": 1000.0
      },
      "price": {
        "min": 1e-05,
        "max": 1000000.0
      },
      "cost": {
        "min": 0.01,
        "max": 1000000.0
      }
    },
    """

    min: float | None
    max: float | None


class Limit(Struct):
    leverage: LimitMinMax = None
    amount: LimitMinMax = None
    price: LimitMinMax = None
    cost: LimitMinMax = None
    market: LimitMinMax = None


class MarginMode(Struct):
    isolated: bool | None
    cross: bool | None


class BaseMarket(Struct):
    """Base market structure for all exchanges."""

    id: str
    lowercaseId: str | None
    symbol: str
    base: str
    quote: str
    settle: str | None
    baseId: str
    quoteId: str
    settleId: str | None
    type: AssetType
    spot: bool
    margin: bool | None
    swap: bool
    future: bool
    option: bool
    index: bool | str | None
    active: bool
    contract: bool
    linear: bool | None
    inverse: bool | None
    subType: AssetType | None
    taker: float
    maker: float
    contractSize: float | None
    expiry: int | None
    expiryDatetime: str | None
    strike: float | str | None
    optionType: str | None
    precision: Precision
    limits: Limit
    marginModes: MarginMode
    created: int | None
    tierBased: bool | None
    percentage: bool | None
    # feeSide: str  # not supported by okx exchanges


class MarketData(Struct):
    bookl1: Dict[str, Dict[str, BookL1]] = defaultdict(dict)
    bookl2: Dict[str, Dict[str, BookL2]] = defaultdict(dict)
    trade: Dict[str, Dict[str, Trade]] = defaultdict(dict)
    kline: Dict[str, Dict[str, Kline]] = defaultdict(dict)
    mark_price: Dict[str, Dict[str, MarkPrice]] = defaultdict(dict)
    funding_rate: Dict[str, Dict[str, FundingRate]] = defaultdict(dict)
    index_price: Dict[str, Dict[str, IndexPrice]] = defaultdict(dict)

    def update_bookl1(self, bookl1: BookL1):
        self.bookl1[bookl1.exchange][bookl1.symbol] = bookl1

    def update_bookl2(self, bookl2: BookL2):
        self.bookl2[bookl2.exchange][bookl2.symbol] = bookl2

    def update_trade(self, trade: Trade):
        self.trade[trade.exchange][trade.symbol] = trade

    def update_kline(self, kline: Kline):
        self.kline[kline.exchange][kline.symbol] = kline

    def update_mark_price(self, mark_price: MarkPrice):
        self.mark_price[mark_price.exchange][mark_price.symbol] = mark_price

    def update_funding_rate(self, funding_rate: FundingRate):
        self.funding_rate[funding_rate.exchange][funding_rate.symbol] = funding_rate

    def update_index_price(self, index_price: IndexPrice):
        self.index_price[index_price.exchange][index_price.symbol] = index_price


"""
class Position(Struct):

    one-way mode:
    > order (side: buy) -> side: buy | pos_side: net/both | reduce_only: False [open long position]
    > order (side: sell) -> side: sell | pos_side: net/both | reduce_only: False [open short position]
    > order (side: buy, reduce_only=True) -> side: buy | pos_side: net/both | reduce_only: True [close short position]
    > order (side: sell, reduce_only=True) -> side: sell | pos_side: net/both | reduce_only: True [close long position]

    hedge mode:
    > order (side: buy, pos_side: long) -> side: buy | pos_side: long | reduce_only: False [open long position]
    > order (side: sell, pos_side: short) -> side: sell | pos_side: short | reduce_only: False [open short position]
    > order (side: sell, pos_side: long) -> side: sell | pos_side: long | reduce_only: True [close long position]
    > order (side: buy, pos_side: short) -> side: buy | pos_side: short | reduce_only: True [close short position]

    
"""


class Position(Struct):
    symbol: str
    exchange: str
    strategy_id: str
    side: Optional[PositionSide] = None
    signed_amount: Decimal = Decimal("0")
    entry_price: float = 0
    unrealized_pnl: float = 0
    realized_pnl: float = 0
    last_order_filled: Dict[str, Decimal] = field(default_factory=dict)

    @property
    def amount(self) -> Decimal:
        return abs(self.signed_amount)

    @property
    def is_open(self) -> bool:
        return self.amount != 0

    @property
    def is_closed(self) -> bool:
        return not self.is_open

    @property
    def is_long(self) -> bool:
        return self.side == PositionSide.LONG

    @property
    def is_short(self) -> bool:
        return self.side == PositionSide.SHORT

    def _calculate_fill_delta(self, order: Order) -> Decimal:
        """
        calculate the fill delta of the order, since filled in order is cumulative,
        we need to calculate the delta of the order
        """

        previous_fill = self.last_order_filled.get(order.id, Decimal("0"))
        current_fill = order.filled
        fill_delta = current_fill - previous_fill
        if order.status in (OrderStatus.FILLED, OrderStatus.CANCELED):
            self.last_order_filled.pop(order.id, None)
        else:
            self.last_order_filled[order.id] = order.filled
        return fill_delta

    def _calculate_pnl(self, current_price: float, amount: Decimal) -> float:
        """Calculate PNL based on position side and current price"""
        if self.side == PositionSide.LONG:
            return float(amount) * (current_price - self.entry_price)
        elif self.side == PositionSide.SHORT:
            return float(amount) * (self.entry_price - current_price)
        return 0.0

    def apply(self, order: Order):
        if order.position_side == PositionSide.FLAT:
            fill_delta = self._calculate_fill_delta(order)
            
            if (self.signed_amount > 0 and order.side == OrderSide.SELL) or (
                self.signed_amount < 0 and order.side == OrderSide.BUY
            ):
                close_amount = min(abs(self.signed_amount), fill_delta) # 平仓数量最大不超过当前持仓数量
                remaining_amount = fill_delta - close_amount # 剩余数量
                self._close_position(order, close_amount)
                if remaining_amount > 0:
                    self._open_position(order, remaining_amount)
            else:
                self._open_position(order, fill_delta)
        else:
            pass

    def _close_position(self, order: Order, close_amount: Decimal):
        price = order.average or order.price

        if order.side == OrderSide.BUY:
            if self.side != PositionSide.SHORT:
                warnings.warn(f"Cannot close short position with {self.side}")
            self.realized_pnl += self._calculate_pnl(price, close_amount)
            self.signed_amount += close_amount
        elif order.side == OrderSide.SELL:
            if self.side != PositionSide.LONG:
                warnings.warn(f"Cannot close long position with {self.side}")
            self.realized_pnl += self._calculate_pnl(price, close_amount)
            self.signed_amount -= close_amount

        self.unrealized_pnl = self._calculate_pnl(price, self.amount)

        if self.signed_amount == 0:
            self.side = None
            self.entry_price = 0
            self.unrealized_pnl = 0

    def _open_position(self, order: Order, open_amount: Decimal):
        if order.side == OrderSide.BUY:
            if not self.side:
                self.side = PositionSide.LONG
            else:
                if self.side != PositionSide.LONG:
                    warnings.warn(f"Cannot open long position with {self.side}")
                
            tmp_amount = self.signed_amount + open_amount
            price = order.average or order.price
            self.entry_price = (
                (self.entry_price * float(self.signed_amount) + price * float(open_amount))
                / float(tmp_amount)
                if tmp_amount != 0
                else 0
            )
            self.signed_amount = tmp_amount
            
        elif order.side == OrderSide.SELL:
            if not self.side:
                self.side = PositionSide.SHORT
            else:
                if self.side != PositionSide.SHORT:
                    warnings.warn(f"Cannot open short position with {self.side}")
                
            tmp_amount = self.signed_amount - open_amount
            price = order.average or order.price
            self.entry_price = (
                (self.entry_price * float(self.signed_amount) - price * float(open_amount))
                / float(tmp_amount)
                if tmp_amount != 0
                else 0
            )
            self.signed_amount = tmp_amount
            
        self.unrealized_pnl = self._calculate_pnl(price, self.amount)
