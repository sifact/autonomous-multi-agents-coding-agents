`shipping.py` has a bug: parcels that weigh exactly a tier limit are charged the price of the
next tier.

Example: `shipping_cost(1)` should be `4.0` (a 1 kg parcel is in the lightest tier) but returns
`7.5`.

Contract (keep every name and signature):

- `shipping_cost(weight_kg)` prices by weight in kg: up to and including 1 kg costs 4.00;
  over 1 kg up to and including 5 kg costs 7.50; over 5 kg up to and including 20 kg costs
  15.00; anything heavier costs 30.00. Fractional weights follow the same rules.
- A weight of zero or less raises `ValueError`.
- `order_shipping(subtotal, weight_kg)` is 0.0 when the subtotal is 75.00 or more, otherwise
  it is `shipping_cost(weight_kg)`. It already works for subtotals and must keep working.
