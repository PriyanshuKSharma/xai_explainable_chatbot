from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BankProduct:
    bank: str
    product: str
    tenure_years_min: float
    tenure_years_max: float
    rate_annual_pct: float
    compounding: str | None = None
    notes: str | None = None


class BankDatasetError(RuntimeError):
    pass


class BankProductService:
    def __init__(self, data_path: str | None = None) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        default_path = repo_root / "data" / "banks" / "bank_products.json"
        self.data_path = Path(data_path) if data_path else default_path
        self._cache: list[BankProduct] | None = None

    def _load(self) -> list[BankProduct]:
        if self._cache is not None:
            return self._cache

        if not self.data_path.exists():
            self._cache = []
            return self._cache

        try:
            raw = json.loads(self.data_path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise BankDatasetError(f"Failed to read bank dataset: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise BankDatasetError(f"Invalid bank dataset JSON: {exc}") from exc

        if not isinstance(raw, list):
            raise BankDatasetError("Bank dataset must be a JSON list.")

        items: list[BankProduct] = []
        for row in raw:
            if not isinstance(row, dict):
                continue
            bank = str(row.get("bank", "")).strip()
            product = str(row.get("product", "")).strip().upper()
            if not bank or not product:
                continue

            try:
                tmin = float(row.get("tenure_years_min"))
                tmax = float(row.get("tenure_years_max"))
                rate = float(row.get("rate_annual_pct"))
            except (TypeError, ValueError):
                continue

            items.append(
                BankProduct(
                    bank=bank.upper(),
                    product=product,
                    tenure_years_min=tmin,
                    tenure_years_max=tmax,
                    rate_annual_pct=rate,
                    compounding=str(row.get("compounding")).strip() if row.get("compounding") else None,
                    notes=str(row.get("notes")).strip() if row.get("notes") else None,
                )
            )

        self._cache = items
        return items

    def list_products(self) -> list[BankProduct]:
        return list(self._load())

    def find_rates(
        self,
        *,
        product: str | None = None,
        bank: str | None = None,
        tenure_years: float | None = None,
    ) -> list[BankProduct]:
        product_norm = product.upper().strip() if product else None
        bank_norm = bank.upper().strip() if bank else None

        matches: list[BankProduct] = []
        for item in self._load():
            if product_norm and item.product != product_norm:
                continue
            if bank_norm and item.bank != bank_norm:
                continue
            if tenure_years is not None and not (item.tenure_years_min <= tenure_years <= item.tenure_years_max):
                continue
            matches.append(item)

        matches.sort(key=lambda x: x.rate_annual_pct, reverse=True)
        return matches

    def best_rate(
        self,
        *,
        product: str,
        tenure_years: float | None = None,
    ) -> BankProduct | None:
        matches = self.find_rates(product=product, tenure_years=tenure_years)
        return matches[0] if matches else None

