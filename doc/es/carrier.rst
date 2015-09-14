#:inside:carrier/carrier:bullet_list:carrier_cost_method#

* Cálculo (fórmulas)

#:after:carrier/carrier:section:transportistas#

Cálculo (fórmulas)
==================

Al seleccionar en el método de coste la opción "cálculo" en un transportista podemos añadir 
diferentes líneas. En estas líneas podemos realizar cálculos para obtener el precio del coste del envío.

El uso de formulas pueden ser de este estilo:

.. code-block:: python

  getattr(record, "total_amount") > 0
  getattr(record, "untaxed_amount") >= 0

En el siguiente ejemplo es una tarifa de envío que se calcula a partir del precio de la
base de un pedido de venta:

.. code-block:: csv

    "Secuencia","Cálculo","Precio"
    "0","getattr(record, "untaxed_amount") >= 250","0,00"
    "5","getattr(record, "untaxed_amount") >= 150","4,50"
    "7","getattr(record, "untaxed_amount") >= 0","6,50"

El orden de las líneas (secuencia) es importante ya que si en una línea entra en la condición, se obtendrá
el valor de esta y no continuará con las siguientes. También en el momento de diseñar la rejilla
de tarifas de envío, es importante que la última línea sea una condición que sea para todos.
