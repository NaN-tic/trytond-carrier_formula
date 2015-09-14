#This file is part carrier_formula module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
from trytond.pool import Pool
from .carrier import *
from .stock import *
from .sale import *

def register():
    Pool.register(
        Carrier,
        FormulaPriceList,
        ShipmentIn,
        ShipmentOut,
        Sale,
        module='carrier_formula', type_='model')
