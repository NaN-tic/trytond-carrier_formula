# This file is part carrier_formula module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from decimal import Decimal
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction

__all__ = ['ShipmentIn', 'ShipmentOut']
_ZERO = Decimal(0)

def _formula_amount(lines, company):
    pool = Pool()
    Move = pool.get('stock.move')
    Currency = pool.get('currency.currency')

    amount = _ZERO
    for line in lines or []:
        unit_price = getattr(line, 'unit_price',
            Move.default_unit_price() if hasattr(Move, 'default_unit_price')
            else _ZERO)
        currency = getattr(line, 'currency',
            Move.default_currency() if hasattr(Move, 'default_currency')
            else None)
        if currency:
            unit_price = Currency.compute(currency, unit_price,
                company.currency, round=False)
        amount += (unit_price or _ZERO) * Decimal(str(line.quantity or 0))
    return amount


class ShipmentIn(metaclass=PoolMeta):
    __name__ = 'stock.shipment.in'

    def _get_carrier_context(self):
        Company = Pool().get('company.company')

        context = super(ShipmentIn, self)._get_carrier_context()
        if not self.carrier:
            return context
        if self.carrier.carrier_cost_method != 'formula':
            return context
        company = Company(Transaction().context['company'])
        context['record'] = self
        context['amount'] = _formula_amount(self.incoming_moves, company)
        context['currency'] = company.currency.id
        return context


class ShipmentOut(metaclass=PoolMeta):
    __name__ = 'stock.shipment.out'

    def _get_carrier_context(self):
        Company = Pool().get('company.company')

        context = super(ShipmentOut, self)._get_carrier_context()
        if not self.carrier:
            return context
        if self.carrier.carrier_cost_method != 'formula':
            return context
        if self.origin and self.origin.__name__ == 'sale.sale':
            context['record'] = self.origin
        else:
            context['record'] = self
        company = Company(Transaction().context['company'])
        context['amount'] = _formula_amount(self.inventory_moves, company)
        context['currency'] = company.currency.id
        return context
