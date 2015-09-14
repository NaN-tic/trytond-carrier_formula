========================
Transportistas. Formulas
========================

Añade método de coste basado en una formula.

Se recomienda instalar los módulos stock_origin_purchase o stock_orgin_sale
para que añade el precio de coste de envío en los albaranes.

Ejemplo de formula:

  getattr(record, "total_amount") > 0
  getattr(record, "untaxed_amount") >= 0
