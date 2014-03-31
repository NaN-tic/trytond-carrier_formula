#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from decimal import Decimal

from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction

__all__ = ['ShipmentIn', 'ShipmentOut']
__metaclass__ = PoolMeta


def _formula_amount(lines, company):
    pool = Pool()
    Move = pool.get('stock.move')
    Currency = pool.get('currency.currency')

    amount = 0
    for line in lines or []:
        unit_price = getattr(line, 'unit_price',
            Move.default_unit_price() if hasattr(Move, 'default_unit_price')
            else Decimal(0))
        currency = getattr(line, 'currency',
            Move.default_currency() if hasattr(Move, 'default_currency')
            else None)
        if currency:
            unit_price = Currency.compute(currency, unit_price,
                company.currency, round=False)
        if unit_price:
            amount += unit_price * Decimal(str(line.quantity or 0))
    return amount


class ShipmentIn:
    __name__ = 'stock.shipment.in'

    def _get_carrier_context(self):
        Company = Pool().get('company.company')
        context = super(ShipmentIn, self)._get_carrier_context()
        if not self.carrier:
            return context

        context = context.copy()
        if self.carrier.carrier_cost_method != 'formula':
            return context

        company = Company(Transaction().context['company'])
        context['record'] = self
        context['amount'] = _formula_amount(self.incoming_moves, company)
        context['currency'] = company.currency.id
        return context


class ShipmentOut:
    __name__ = 'stock.shipment.out'

    @classmethod
    def __setup__(cls):
        super(ShipmentOut, cls).__setup__()
        for fname in ('carrier', 'customer', 'inventory_moves', 'origin'):
            if fname not in cls.inventory_moves.on_change:
                cls.inventory_moves.on_change.append(fname)
        for fname in cls.inventory_moves.on_change:
            if fname not in cls.carrier.on_change:
                cls.carrier.on_change.append(fname)

    def _get_carrier_context(self):
        Company = Pool().get('company.company')
        context = super(ShipmentOut, self)._get_carrier_context()
        if not self.carrier:
            return context

        context = context.copy()
        if self.carrier.carrier_cost_method != 'formula':
            return context
        
        if self.origin and self.origin.__name__ == 'sale.sale':
            company = Company(Transaction().context['company'])
            context['record'] = self.origin
            context['amount'] = _formula_amount(self.inventory_moves, company)
            context['currency'] = company.currency.id
        return context
