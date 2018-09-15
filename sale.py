# This file is part carrier_formula module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import PoolMeta

__all__ = ['Sale']


class Sale(metaclass=PoolMeta):
    __name__ = 'sale.sale'

    def _get_carrier_context(self):
        context = super(Sale, self)._get_carrier_context()

        if self.carrier and self.carrier.carrier_cost_method != 'formula':
            return context
        if not self.currency:
            return context
        context = context.copy()
        context['record'] = self
        return context
