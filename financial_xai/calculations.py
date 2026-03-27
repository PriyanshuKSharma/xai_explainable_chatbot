from __future__ import annotations

from math import ceil


def simple_interest(principal: float, annual_rate: float, years: float) -> dict[str, float]:
    interest = principal * annual_rate * years / 100
    total_amount = principal + interest
    return {"interest": round(interest, 2), "total_amount": round(total_amount, 2)}


def compound_interest(
    principal: float,
    annual_rate: float,
    years: float,
    compounds_per_year: int = 1,
) -> dict[str, float]:
    periodic_rate = annual_rate / (100 * compounds_per_year)
    total_amount = principal * ((1 + periodic_rate) ** (compounds_per_year * years))
    interest = total_amount - principal
    return {"interest": round(interest, 2), "total_amount": round(total_amount, 2)}


def sip_future_value(
    monthly_investment: float,
    annual_rate: float,
    years: float,
    contribution_timing: str = "end",
) -> dict[str, float]:
    periods = int(ceil(years * 12))
    monthly_rate = annual_rate / (12 * 100)
    invested_amount = monthly_investment * periods

    if monthly_rate == 0:
        maturity_amount = invested_amount
    else:
        maturity_amount = monthly_investment * (((1 + monthly_rate) ** periods - 1) / monthly_rate)
        if contribution_timing == "beginning":
            maturity_amount *= 1 + monthly_rate

    estimated_gain = maturity_amount - invested_amount
    return {
        "invested_amount": round(invested_amount, 2),
        "estimated_gain": round(estimated_gain, 2),
        "maturity_amount": round(maturity_amount, 2),
    }


def fd_maturity(
    principal: float,
    annual_rate: float,
    years: float,
    compounds_per_year: int = 4,
) -> dict[str, float]:
    return compound_interest(principal, annual_rate, years, compounds_per_year)


def rd_maturity(monthly_deposit: float, annual_rate: float, years: float) -> dict[str, float]:
    return sip_future_value(monthly_deposit, annual_rate, years, contribution_timing="end")


def emi(principal: float, annual_rate: float, years: float) -> float:
    months = int(ceil(years * 12))
    monthly_rate = annual_rate / (12 * 100)

    if monthly_rate == 0:
        return round(principal / months, 2)

    growth_factor = (1 + monthly_rate) ** months
    monthly_payment = principal * monthly_rate * growth_factor / (growth_factor - 1)
    return round(monthly_payment, 2)
