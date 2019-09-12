# This file is part carrier_formula module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
try:
    from trytond.modules.carrier_formula.tests.test_carrier_formula import suite
except ImportError:
    from .test_carrier_formula import suite

__all__ = ['suite']
