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
from trytond.tools import decistmt
from trytond.modules.product import price_digits

__all__ = ['Carrier', 'FormulaPriceList']


class Carrier(metaclass=PoolMeta):
    __name__ = 'carrier'
    formula_currency = fields.Many2One('currency.currency', 'Currency',
        states={
            'invisible': Eval('carrier_cost_method') != 'formula',
            'required': Eval('carrier_cost_method') == 'formula',
            'readonly': Bool(Eval('formula_price_list', [])),
            })
    formula_price_list = fields.One2Many(
        'carrier.formula_price_list', 'carrier', 'Price List',
        states={
            'invisible': Eval('carrier_cost_method') != 'formula',
            })

    @classmethod
    def __setup__(cls):
        super(Carrier, cls).__setup__()
        selection = ('formula', 'Formula')
        if selection not in cls.carrier_cost_method.selection:
            cls.carrier_cost_method.selection.append(selection)

    @staticmethod
    def default_formula_currency():
        Company = Pool().get('company.company')
        company_id = Transaction().context.get('company')
        if company_id is not None and company_id >= 0:
            return Company(company_id).currency.id

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
        # context['record'] = record._save_values()
        # context['record_model'] = 'sale.sale'
        # context['carrier'] = carrier

        price, currency_id = super(Carrier, self).get_sale_price()

        if self.carrier_cost_method == 'formula':
            price = Decimal(0)
            currency_id = self.formula_currency.id
            carrier = Transaction().context.get('carrier', None)
            record = Transaction().context.get('record', None)
            model = Transaction().context.get('record_model', None)

            if not record:
                return price, currency_id

            # is an object that not saved (has not id)
            if isinstance(record, dict):
                if not model:
                    return price, currency_id
                record = Pool().get(model)(**record)
            elif isinstance(record, str):
                model, id = record.split(',')
                record = Pool().get(model)(id)

            if carrier:
                price = self.compute_formula_price(record)
            else:
                if model == 'sale.sale':
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

        price = self.round_price_formula(price, self.formula_currency.digits)
        return price, currency_id

    def get_purchase_price(self):
        price, currency_id = super(Carrier, self).get_purchase_price()

        if self.carrier_cost_method == 'formula':
            price = Decimal(0)
            currency_id = self.formula_currency.id
            record = Transaction().context.get('record', None)
            model = Transaction().context.get('record_model', None)

            if not record:
                return price, currency_id

            # is an object that not saved (has not id)
            if isinstance(record, dict):
                if not model:
                    return price, currency_id
                record = Pool().get(model)(**record)
            else:
                model, id = record.split(',')
                record = Pool().get(model)(id)

            if model == 'purchase.purchase':
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

        price = self.round_price_formula(price, self.formula_currency.digits)
        return price, currency_id


class FormulaPriceList(sequence_ordered(), ModelSQL, ModelView, MatchMixin):
    'Carrier Formula Price List'
    __name__ = 'carrier.formula_price_list'
    carrier = fields.Many2One('carrier', 'Carrier', required=True)
    sequence = fields.Integer('Sequence', required=True)
    formula = fields.Char('Formula', required=True,
        help=('Python expression that will be evaluated. Eg:\n'
            'getattr(record, "total_amount") > 0'))
    price = fields.Numeric('Price', required=True, digits=price_digits)

    @classmethod
    def __setup__(cls):
        super(FormulaPriceList, cls).__setup__()
        cls._order.insert(0, ('sequence', 'ASC'))

    @classmethod
    def __register__(cls, module_name):
        super(FormulaPriceList, cls).__register__(module_name)

        table_h = backend.TableHandler(cls, module_name)

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
