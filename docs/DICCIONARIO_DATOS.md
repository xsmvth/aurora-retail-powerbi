# Diccionario de datos

## Granularidad

`fact_sales` tiene una fila por **línea de pedido**. La devolución se representa
con cantidad negativa e `is_return = true`. Los ingresos son netos de descuento y
devoluciones.

`fact_targets` tiene una fila por **mes, tienda y canal**.

## `fact_sales`

| Campo | Tipo | Descripción |
|---|---|---|
| `sale_line_key` | texto | Identificador único de la línea. Clave de idempotencia. |
| `order_key` | texto | Pedido; `DISTINCTCOUNT` produce el KPI de pedidos. |
| `date_key` | entero | Clave de fecha `YYYYMMDD`. |
| `customer_key` | texto | Cliente que realizó la compra. |
| `product_key` | texto | Producto de la línea. |
| `store_key` | texto | Tienda asociada a la operación. |
| `channel_key` | texto | Canal: tienda física, ecommerce o delivery. |
| `quantity` | entero | Unidades; negativo para devoluciones. |
| `unit_price` | decimal | Precio antes de descuento. |
| `discount_pct` | decimal | Descuento como proporción entre 0 y 0.95. |
| `revenue` | decimal | `quantity × unit_price × (1 - discount_pct)`. |
| `cost` | decimal | `quantity × unit_cost`. |
| `gross_profit` | decimal | `revenue - cost`. |
| `is_return` | booleano | Indica devolución. |
| `payment_method` | texto | Medio de pago. |
| `loaded_at` | timestamp | Fecha y hora UTC de carga. |

## `fact_targets`

| Campo | Tipo | Descripción |
|---|---|---|
| `target_month` | texto | Mes `YYYY-MM`. |
| `store_key` | texto | Tienda objetivo. |
| `channel_key` | texto | Canal objetivo. |
| `target_revenue` | decimal | Meta de ingresos netos. |

## `dim_date`

| Campo | Tipo | Descripción |
|---|---|---|
| `date_key` | entero | Clave `YYYYMMDD`, única. |
| `date` | fecha | Fecha completa para time intelligence. |
| `year` | entero | Año. |
| `quarter` | entero | Trimestre 1–4. |
| `month_number` | entero | Mes 1–12. |
| `month_name` | texto | Nombre del mes en español. |
| `month_short` | texto | Abreviatura del mes. |
| `month_start` | fecha | Primer día del mes. |
| `month_key` | texto | Mes `YYYY-MM`. |
| `week_number` | entero | Semana ISO. |
| `weekday_name` | texto | Día de la semana en español. |
| `is_weekend` | booleano | Indica sábado o domingo. |

## `dim_month`

Vista única por mes. Sirve de puente entre el calendario diario y las metas:
`dim_date[month_key] → dim_month[month_key] → fact_targets[target_month]`.

## `dim_customer`

| Campo | Tipo | Descripción |
|---|---|---|
| `customer_key` | texto | Identificador anonimizado. |
| `customer_name` | texto | Etiqueta ficticia. |
| `segment` | texto | Frecuente, ocasional, nuevo o empresarial. |
| `region` | texto | Región del cliente. |
| `city` | texto | Ciudad. |
| `signup_date` | fecha | Fecha de alta simulada. |
| `is_active` | booleano | Estado. |

## `dim_product`

| Campo | Tipo | Descripción |
|---|---|---|
| `product_key` | texto | Identificador de producto. |
| `product_name` | texto | Nombre del producto. |
| `category` | texto | Categoría comercial. |
| `subcategory` | texto | Subcategoría. |
| `list_price` | decimal | Precio de lista. |
| `unit_cost` | decimal | Costo unitario. |
| `is_active` | booleano | Estado. |

## `dim_store`

| Campo | Tipo | Descripción |
|---|---|---|
| `store_key` | texto | Identificador de tienda. |
| `store_name` | texto | Nombre de tienda. |
| `region` | texto | Región comercial. |
| `city` | texto | Ciudad. |
| `store_type` | texto | Urbana, regional o turística. |
| `opening_date` | fecha | Fecha de apertura. |

## `dim_channel`

| Campo | Tipo | Descripción |
|---|---|---|
| `channel_key` | texto | Identificador de canal. |
| `channel_name` | texto | Nombre del canal. |

## Vistas de validación

- `vw_sales_enriched`: línea de venta con atributos descriptivos.
- `vw_monthly_kpis`: ingresos, margen, pedidos, ticket y clientes por mes.
- `vw_store_performance`: agregado por tienda.
- `vw_category_performance`: agregado por categoría.
