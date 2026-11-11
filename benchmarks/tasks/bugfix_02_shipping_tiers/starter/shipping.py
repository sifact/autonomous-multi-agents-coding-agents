"""Shipping prices for a small web shop."""

FREE_SHIPPING_FROM = 75.00

# (heaviest weight in kg, price in dollars) for each tier, lightest first.
TIERS = [(1, 4.00), (5, 7.50), (20, 15.00)]
HEAVY_PRICE = 30.00


def shipping_cost(weight_kg: float) -> float:
    """Price in dollars for sending one parcel of the given weight."""
    if weight_kg <= 0:
        raise ValueError("weight must be positive")
    for limit, price in TIERS:
        if weight_kg < limit:
            return price
    return HEAVY_PRICE


def order_shipping(subtotal: float, weight_kg: float) -> float:
    """Shipping charged on an order; large orders ship for free."""
    if subtotal >= FREE_SHIPPING_FROM:
        return 0.0
    return shipping_cost(weight_kg)
