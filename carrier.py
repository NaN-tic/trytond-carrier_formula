#This file is part carrier_formula module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
from decimal import Decimal
import tokenize
from StringIO import StringIO
from trytond.model import ModelSQL, ModelView, fields
from trytond.pyson import Eval, Bool
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.tools import safe_eval
from trytond.config import config as config_
DIGITS = int(config_.get('digits', 'unit_price_digits', 4))

__all__ = ['Carrier', 'FormulaPriceList']
__metaclass__ = PoolMeta

# code snippet taken from http://docs.python.org/library/tokenize.html
def decistmt(s):
    """Substitute Decimals for floats in a string of statements.

    >>> from decimal import Decimal
    >>> s = 'print +21.3e-5*-.1234/81.7'
    >>> decistmt(s)
    "print +Decimal ('21.3e-5')*-Decimal ('.1234')/Decimal ('81.7')"

    >>> exec(s)
    -3.21716034272e-007
    >>> exec(decistmt(s))
    -3.217160342717258261933904529E-7
    """
    result = []
    # tokenize the string
    g = tokenize.generate_tokens(StringIO(s).readline)
    for toknum, tokval, _, _, _ in g:
        # replace NUMBER tokens
        if toknum == tokenize.NUMBER and '.' in tokval:
            result.extend([
                (tokenize.NAME, 'Decimal'),
                (tokenize.OP, '('),
                (tokenize.STRING, repr(tokval)),
                (tokenize.OP, ')')
            ])
        else:
            result.append((toknum, tokval))
    return tokenize.untokenize(result)


class Carrier:
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
    formula_price_list = fields.One2Many('carrier.formula_price_list', 'carrier',
        'Price List',
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
    def default_formula_currency_digits():
        Company = Pool().get('company.company')
        company = Transaction().context.get('company')
        if company:
            return Company(company).currency.digits
        return 2

    def on_change_with_formula_currency_digits(self, name=None):
        if self.formula_currency:
            return self.formula_currency.digits
        return 2

    @staticmethod
    def round_price_formula(number, digits):
        quantize = Decimal(10) ** -Decimal(digits)
        return Decimal(number).quantize(quantize)

    def compute_formula_price(self, formula):
        "Compute price based on formula"
        for line in self.formula_price_list:
            if safe_eval(decistmt(line.formula), Transaction().context):
                return line.price
        return Decimal(0)

    def get_sale_price(self):
        # Designed to get shipment price with a current sale (default)
        # or calculate prices for a hipotetic order (sale cart).
        # Second case, we add in context a carrier and simulate a sale in record
        # to evaluate (safe eval) in carrier formula.

        # Example:
        # sale = Sale()
        # sale.untaxed_amount = untaxed_amount
        # sale.tax_amount = tax_amount
        # sale.total_amount = total_amount
        # context = {}
        # context['record'] = sale 
        # context['carrier'] = carrier

        price, currency_id = super(Carrier, self).get_sale_price()
        if self.carrier_cost_method == 'formula':
            price = Decimal(0)
            currency_id = self.formula_currency.id
            carrier = Transaction().context.get('carrier', None)
            sale = Transaction().context.get('record', None)

            if carrier:
                for formula in carrier.formula_price_list:
                    price = self.compute_formula_price(formula)
            elif sale:
                if sale.carrier:
                    sale.untaxed_amount = Decimal(0)
                    for line in sale['lines']:
                        if hasattr(line, 'shipment_cost') and line.shipment_cost:
                            continue
                        if line.amount and line.type == 'line':
                            sale.untaxed_amount += line.amount
                    sale.tax_amount = sale.get_tax_amount()
                    sale.total_amount = sale.untaxed_amount + sale.tax_amount

                    for formula in sale['carrier'].formula_price_list:
                        price = self.compute_formula_price(formula)
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
            purchase = Transaction().context.get('record', None)
            if purchase:
                if purchase.carrier:
                    purchase.untaxed_amount = Decimal(0)
                    for line in purchase['lines']:
                        if not line.shipment_cost and line.amount and line.type == 'line':
                            purchase.untaxed_amount += line.amount
                    purchase.tax_amount = purchase.get_tax_amount()
                    purchase.total_amount = purchase.untaxed_amount + purchase.tax_amount

                    for formula in purchase['carrier'].formula_price_list:
                        price = self.compute_formula_price(formula)
                else:
                    price = self.carrier_product.list_price
            else:
                price = self.carrier_product.list_price

        price = self.round_price_formula(price, self.formula_currency_digits)
        return price, currency_id


class FormulaPriceList(ModelSQL, ModelView):
    'Carrier Formula Price List'
    __name__ = 'carrier.formula_price_list'
    carrier = fields.Many2One('carrier', 'Carrier', required=True, select=True)
    sequence = fields.Integer('Sequence', required=True)
    formula = fields.Char('Formula', required=True,
        help=('Python expression that will be evaluated. Eg:\n'
            'record.total_amount > 0'))
    price = fields.Numeric('Price', required=True, digits=(16, DIGITS))

    @classmethod
    def __setup__(cls):
        super(FormulaPriceList, cls).__setup__()
        cls._order.insert(0, ('sequence', 'ASC'))
        cls._error_messages.update({
                'invalid_formula': ('Invalid formula "%(formula)s" in price '
                    'list line "%(line)s".'),
                })

    @staticmethod
    def default_sequence():
        return 1

    @staticmethod
    def default_formula():
        return 'record.total_amount > 0'

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
