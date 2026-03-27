from financial_xai.calculations import compound_interest, simple_interest, sip_future_value


def test_simple_interest_calculation() -> None:
    result = simple_interest(100000, 8, 3)
    assert result["interest"] == 24000.00
    assert result["total_amount"] == 124000.00


def test_compound_interest_calculation() -> None:
    result = compound_interest(100000, 10, 2, 1)
    assert result["interest"] == 21000.00
    assert result["total_amount"] == 121000.00


def test_sip_projection_grows_above_invested_amount() -> None:
    result = sip_future_value(5000, 12, 10)
    assert result["invested_amount"] == 600000.00
    assert result["maturity_amount"] > result["invested_amount"]
