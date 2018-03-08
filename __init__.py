# This file is part carrier_formula module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool
from . import carrier
from . import stock
from . import sale


def register():
    Pool.register(
        carrier.Carrier,
        carrier.FormulaPriceList,
        stock.ShipmentIn,
        stock.ShipmentOut,
        sale.Sale,
        module='carrier_formula', type_='model')
