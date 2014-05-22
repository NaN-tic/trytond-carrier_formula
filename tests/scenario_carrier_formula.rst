========================
Carrier Formula Scenario
========================

=============
General Setup
=============

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from proteus import config, Model, Wizard
    >>> today = datetime.date.today()

Create database::

    >>> config = config.set_trytond()

Install carrier_formula, purchase_shipment_cost and sale_shipment_cost::

    >>> Module = Model.get('ir.module.module')
    >>> modules = Module.find([
    ...         ('name', 'in', ['carrier_formula',
    ...                 'purchase_shipment_cost', 'sale_shipment_cost']),
    ...         ])
    >>> Module.install([x.id for x in modules], config.context)
    >>> Wizard('ir.module.module.install_upgrade').execute('upgrade')

Create company::

    >>> Currency = Model.get('currency.currency')
    >>> CurrencyRate = Model.get('currency.currency.rate')
    >>> Company = Model.get('company.company')
    >>> Party = Model.get('party.party')
    >>> company_config = Wizard('company.company.config')
    >>> company_config.execute('company')
    >>> company = company_config.form
    >>> party = Party(name='Dunder Mifflin')
    >>> party.save()
    >>> company.party = party
    >>> currencies = Currency.find([('code', '=', 'EUR')])
    >>> if not currencies:
    ...     currency = Currency(name='Euro', symbol=u'€', code='EUR',
    ...         rounding=Decimal('0.01'), mon_grouping='[3, 3, 0]',
    ...         mon_decimal_point=',')
    ...     currency.save()
    ...     CurrencyRate(date=today + relativedelta(month=1, day=1),
    ...         rate=Decimal('1.0'), currency=currency).save()
    ... else:
    ...     currency, = currencies
    >>> company.currency = currency
    >>> company_config.execute('add')
    >>> company, = Company.find()

Reload the context::

    >>> User = Model.get('res.user')
    >>> config._context = User.get_preferences(True, config.context)

Create fiscal year::

    >>> FiscalYear = Model.get('account.fiscalyear')
    >>> Sequence = Model.get('ir.sequence')
    >>> SequenceStrict = Model.get('ir.sequence.strict')
    >>> fiscalyear = FiscalYear(name='%s' % today.year)
    >>> fiscalyear.start_date = today + relativedelta(month=1, day=1)
    >>> fiscalyear.end_date = today + relativedelta(month=12, day=31)
    >>> fiscalyear.company = company
    >>> post_move_sequence = Sequence(name='%s' % today.year,
    ...     code='account.move',
    ...     company=company)
    >>> post_move_sequence.save()
    >>> fiscalyear.post_move_sequence = post_move_sequence
    >>> invoice_sequence = SequenceStrict(name='%s' % today.year,
    ...     code='account.invoice',
    ...     company=company)
    >>> invoice_sequence.save()
    >>> fiscalyear.out_invoice_sequence = invoice_sequence
    >>> fiscalyear.in_invoice_sequence = invoice_sequence
    >>> fiscalyear.out_credit_note_sequence = invoice_sequence
    >>> fiscalyear.in_credit_note_sequence = invoice_sequence
    >>> fiscalyear.save()
    >>> FiscalYear.create_period([fiscalyear.id], config.context)

Create chart of accounts::

    >>> AccountTemplate = Model.get('account.account.template')
    >>> Account = Model.get('account.account')
    >>> AccountJournal = Model.get('account.journal')
    >>> account_template, = AccountTemplate.find([('parent', '=', None)])
    >>> create_chart = Wizard('account.create_chart')
    >>> create_chart.execute('account')
    >>> create_chart.form.account_template = account_template
    >>> create_chart.form.company = company
    >>> create_chart.execute('create_account')
    >>> receivable, = Account.find([
    ...         ('kind', '=', 'receivable'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> payable, = Account.find([
    ...         ('kind', '=', 'payable'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> revenue, = Account.find([
    ...         ('kind', '=', 'revenue'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> create_chart.form.account_receivable = receivable
    >>> create_chart.form.account_payable = payable
    >>> create_chart.execute('create_properties')

Create supplier::

    >>> Party = Model.get('party.party')
    >>> supplier = Party(name='Supplier')
    >>> supplier.save()

Create customer::

    >>> Party = Model.get('party.party')
    >>> customer = Party(name='Customer')
    >>> customer.save()

Create category::

    >>> ProductCategory = Model.get('product.category')
    >>> category = ProductCategory(name='Category')
    >>> category.save()

Create product::

    >>> ProductUom = Model.get('product.uom')
    >>> ProductTemplate = Model.get('product.template')
    >>> Product = Model.get('product.product')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> gram, = ProductUom.find([('name', '=', 'Gram')])
    >>> product = Product()
    >>> template = ProductTemplate()
    >>> template.name = 'Product'
    >>> template.category = category
    >>> template.default_uom = unit
    >>> template.type = 'goods'
    >>> template.salable = True
    >>> template.list_price = Decimal('20')
    >>> template.cost_price = Decimal('8')
    >>> template.account_revenue = revenue
    >>> template.formula = 250
    >>> template.formula_uom = gram
    >>> template.save()
    >>> product.template = template
    >>> product.save()
    >>> carrier_product = Product()
    >>> carrier_template = ProductTemplate()
    >>> carrier_template.name = 'Carrier Product'
    >>> carrier_template.category = category
    >>> carrier_template.default_uom = unit
    >>> carrier_template.type = 'service'
    >>> carrier_template.salable = True
    >>> carrier_template.list_price = Decimal('3')
    >>> carrier_template.cost_price = Decimal('3')
    >>> carrier_template.account_revenue = revenue
    >>> carrier_template.save()
    >>> carrier_product.template = carrier_template
    >>> carrier_product.save()

Create carrier::

    >>> Carrier = Model.get('carrier')
    >>> FormulaPriceList = Model.get('carrier.formula_price_list')
    >>> carrier = Carrier()
    >>> party = Party(name='Carrier')
    >>> party.save()
    >>> carrier.party = party
    >>> carrier.carrier_product = carrier_product
    >>> carrier.carrier_cost_method = 'formula'
    >>> carrier.formula_currency = currency
    >>> for sequence, formula, price in (
    ...         (10, 'sale.total_amount > 100', Decimal(25)),
    ...         (10, 'sale.total_amount > 50', Decimal(10)),
    ...         (10, 'sale.total_amount > 0', Decimal(5)),
    ...         ):
    ...     line = FormulaPriceList(sequence=sequence, formula=formula, price=price)
    ...     carrier.formula_price_list.append(line)
    >>> carrier.save()
