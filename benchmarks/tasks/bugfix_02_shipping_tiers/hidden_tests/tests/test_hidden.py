import pytest

from shipping import order_shipping, shipping_cost


def test_a_parcel_at_the_top_of_a_tier_stays_in_that_tier():
    assert shipping_cost(1) == 4.00
    assert shipping_cost(5) == 7.50
    assert shipping_cost(20) == 15.00


def test_float_weights_at_a_limit():
    assert shipping_cost(1.0) == 4.00
    assert shipping_cost(5.0) == 7.50
    assert shipping_cost(20.0) == 15.00


def test_just_over_a_limit_moves_to_the_next_tier():
    assert shipping_cost(1.001) == 7.50
    assert shipping_cost(5.001) == 15.00
    assert shipping_cost(20.001) == 30.00
    assert shipping_cost(1.0001) == 7.50
    assert shipping_cost(5.0001) == 15.00
    assert shipping_cost(20.0001) == 30.00


def test_weights_inside_each_tier():
    assert shipping_cost(0.001) == 4.00
    assert shipping_cost(0.5) == 4.00
    assert shipping_cost(2.5) == 7.50
    assert shipping_cost(12) == 15.00
    assert shipping_cost(50) == 30.00


def test_non_positive_weight_raises():
    for weight in (0, 0.0, -1, -0.5):
        with pytest.raises(ValueError):
            shipping_cost(weight)


def test_orders_of_75_or_more_ship_free():
    assert order_shipping(75.00, 3) == 0.0
    assert order_shipping(75.01, 40) == 0.0
    assert order_shipping(500, 1) == 0.0


def test_smaller_orders_pay_by_weight():
    assert order_shipping(74.99, 3) == 7.50
    assert order_shipping(10, 25) == 30.00
    assert order_shipping(0, 0.2) == 4.00


def test_order_shipping_at_the_tier_limits():
    assert order_shipping(10, 1) == 4.00
    assert order_shipping(10, 5) == 7.50
    assert order_shipping(10, 20) == 15.00
