# This file is part carrier_formula module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from decimal import Decimal
from simpleeval import simple_eval

from trytond import backend
from trytond.model import ModelSQL, ModelView, MatchMixin, sequence_ordered, fields
from trytond.pyson import Eval, Bool
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.config import config as config_
from trytond.tools import decistmt

__all__ = ['Carrier', 'FormulaPriceList']

DIGITS = config_.getint('product', 'price_decimal', default=4)


class Carrier(metaclass=PoolMeta):
    __name__ = 'carrier'
    formula_currency = fields.Many2One('currency.currency', 'Currency',
        states={
            'invisible': Eval('carrier_cost_method') != 'formula',
            'required': Eval('carrier_cost_method') == 'formula',
            'readonly': Bool(Eval('formula_price_list', [])),
            },
        depends=['carrier_cost_method', 'formula_price_list'])
    formula_currency_digits = fields.Function(fields.Integer(
            'Formula Currency Digits'),
        'on_change_with_formula_currency_digits')
    formula_price_list = fields.One2Many(
        'carrier.formula_price_list', 'carrier', 'Price List',
        states={
            'invisible': Eval('carrier_cost_method') != 'formula',
            },
        depends=['carrier_cost_method', 'formula_currency'])

    @classmethod
    def __setup__(cls):
        super(Carrier, cls).__setup__()
        selection = ('formula', 'Formula')
        if selection not in cls.carrier_cost_method.selection:
            cls.carrier_cost_method.selection.append(selection)

    @staticmethod
    def default_formula_currency():
        Company = Pool().get('company.company')
        company = Transaction().context.get('company')
        if company:
            return Company(company).currency.id

    @staticmethod
    def default_formula_currency_digits():
        Company = Pool().get('company.company')
        company = Transaction().context.get('company')
        if company:
            return Company(company).currency.digits
        return 2

    @fields.depends('formula_currency')
    def on_change_with_formula_currency_digits(self, name=None):
        if self.formula_currency:
            return self.formula_currency.digits
        return 2

    @staticmethod
    def round_price_formula(number, digits):
        quantize = Decimal(10) ** -Decimal(digits)
        return Decimal(number).quantize(quantize)

    def get_context_formula(self, record):
        return {
            'names': {
                'record': record,
            },
            'functions': {
                'getattr': getattr,
                'setattr': setattr,
                'hasattr': hasattr,
                'Decimal': Decimal,
                'round': round,
                },
            }

    def get_formula_pattern(self, record):
        return {}

    def compute_formula_price(self, record):
        "Compute price based on formula"
        context = self.get_context_formula(record)
        pattern = self.get_formula_pattern(record)
        for line in self.formula_price_list:
            if line.match(pattern):
                if simple_eval(decistmt(line.formula), **context):
                    return line.get_unit_price()
        return Decimal(0)

    def get_sale_price(self):
        # Designed to get shipment price with a current sale (default)
        # or calculate prices for a hipotetic order (sale cart).
        # Second case, we add in context a carrier and simulate a sale in
        # record to evaluate (safe eval) in carrier formula.

        # Example:
        # sale = Sale()
        # sale.untaxed_amount = untaxed_amount
        # sale.tax_amount = tax_amount
        # sale.total_amount = total_amount
        # context = {}
        # context['record'] = record
        # context['carrier'] = carrier

        price, currency_id = super(Carrier, self).get_sale_price()
        if self.carrier_cost_method == 'formula':
            price = Decimal(0)
            currency_id = self.formula_currency.id
            carrier = Transaction().context.get('carrier', None)
            record = Transaction().context.get('record', None)

            if carrier:
                price = self.compute_formula_price(record)
            elif record and record.__name__ == 'sale.sale':
                if record.carrier:
                    record.untaxed_amount = Decimal(0)
                    for line in record.lines:
                        if (hasattr(line, 'shipment_cost')
                                and line.shipment_cost):
                            continue
                        if line.amount and line.type == 'line':
                            record.untaxed_amount += line.amount
                    record.tax_amount = record.get_tax_amount()
                    record.total_amount = (
                        record.untaxed_amount + record.tax_amount)

                    price = self.compute_formula_price(record)
                else:
                    price = self.carrier_product.list_price
            else:
                price = self.carrier_product.list_price

        price = self.round_price_formula(price, self.formula_currency_digits)
        return price, currency_id

    def get_purchase_price(self):
        price, currency_id = super(Carrier, self).get_purchase_price()
        if self.carrier_cost_method == 'formula':
            price = Decimal(0)
            currency_id = self.formula_currency.id
            record = Transaction().context.get('record', None)

            if record and record.__name__ == 'purchase.purchase':
                if record.carrier:
                    record.untaxed_amount = Decimal(0)
                    for line in record['lines']:
                        if (not line.shipment_cost
                                and line.amount
                                and line.type == 'line'):
                            record.untaxed_amount += line.amount
                    record.tax_amount = record.get_tax_amount()
                    record.total_amount = (
                        record.untaxed_amount + record.tax_amount)

                    price = self.compute_formula_price(record)
                else:
                    price = self.carrier_product.list_price
            else:
                price = self.carrier_product.list_price

        price = self.round_price_formula(price, self.formula_currency_digits)
        return price, currency_id


class FormulaPriceList(sequence_ordered(), ModelSQL, ModelView, MatchMixin):
    'Carrier Formula Price List'
    __name__ = 'carrier.formula_price_list'
    carrier = fields.Many2One('carrier', 'Carrier', required=True, select=True)
    sequence = fields.Integer('Sequence', required=True)
    formula = fields.Char('Formula', required=True,
        help=('Python expression that will be evaluated. Eg:\n'
            'getattr(record, "total_amount") > 0'))
    price = fields.Numeric('Price', required=True, digits=(16, DIGITS))

    @classmethod
    def __setup__(cls):
        super(FormulaPriceList, cls).__setup__()
        cls._order.insert(0, ('sequence', 'ASC'))

    @classmethod
    def __register__(cls, module_name):
        TableHandler = backend.get('TableHandler')

        super(FormulaPriceList, cls).__register__(module_name)

        table_h = TableHandler(cls, module_name)

        # Migration from 4.1
        table_h.not_null_action('sequence', 'remove')

    @staticmethod
    def default_formula():
        return 'getattr(record, "total_amount") > 0'

    @staticmethod
    def default_price():
        return Decimal(0)

    @classmethod
    def validate(cls, lines):
        super(FormulaPriceList, cls).validate(lines)
        for line in lines:
            line.check_formula()

    def check_formula(self):
        '''
        Check formula
        '''
        return True

    def match(self, pattern):
        return super(FormulaPriceList, self).match(pattern)

    def get_unit_price(self):
        return self.price
