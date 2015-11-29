#!/usr/bin/env python
# This file is part of carrier_formula module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.tests.test_tryton import test_view, test_depends
from trytond.tests.test_tryton import doctest_setup, doctest_teardown
import trytond.tests.test_tryton
import unittest
import doctest


class CarrierFormulaTestCase(unittest.TestCase):
    'Test Carrier Formula module'

    def setUp(self):
        trytond.tests.test_tryton.install_module(
            'carrier_formula')

    def test0005views(self):
        'Test views'
        test_view('carrier_formula')

    def test0006depends(self):
        'Test depends'
        test_depends()


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        CarrierFormulaTestCase))
    suite.addTests(doctest.DocFileSuite(
            'scenario_carrier_formula.rst',
            setUp=doctest_setup, tearDown=doctest_teardown, encoding='utf-8',
            optionflags=doctest.REPORT_ONLY_FIRST_FAILURE))
    return suite
