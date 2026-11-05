# Cómo agregar datos o usar datos reales

## Agregar un lote nuevo

Copia el archivo en `data/landing/sales/` con un nombre descriptivo, por ejemplo
`sales_2026_11_semana_1.csv`, y ejecuta:

```powershell
.\scripts\actualizar_datos.ps1
```

Columnas obligatorias:

| Columna | Ejemplo | Regla |
|---|---|---|
| `sale_line_id` | `SL009999999` | Único por línea |
| `order_id` | `O0009999` | Agrupa líneas del pedido |
| `order_date` | `2026-11-03` | ISO `YYYY-MM-DD` |
| `customer_id` | `C00125` | Debe existir en `customers.csv` |
| `product_id` | `P0034` | Debe existir en `products.csv` |
| `store_id` | `T001` | Debe existir en `stores.csv` |
| `channel_id` | `CH02` | Debe existir en `channels.csv` |
| `quantity` | `2` o `-1` | Negativo solo en devolución |
| `unit_price` | `249.99` | Mayor o igual a cero |
| `discount_pct` | `0.10` | Proporción entre 0 y 0.95 |
| `unit_cost` | `145.00` | Mayor o igual a cero |
| `is_return` | `0` | `0` venta, `1` devolución |
| `payment_method` | `Tarjeta` | Texto controlado |

Si un cliente, producto, tienda o canal es nuevo, primero agrégalo al CSV de
referencia. El pipeline actualiza las dimensiones antes de cargar ventas.

## Reemplazar con datos de una empresa

1. Conserva el contrato de columnas o modifica `REQUIRED_SALES_COLUMNS` y el
   mapeo dentro de `pipeline/run_pipeline.py`.
2. Anonimiza identificadores y elimina datos personales que no necesites.
3. Ajusta `database/schema_sqlite.sql` si agregas campos.
4. Regenera el modelo y actualiza las medidas DAX si cambia la granularidad.
5. Vuelve a ejecutar el análisis y valida las cifras contra el sistema de origen.

## Reglas de negocio

- Los descuentos se expresan como proporción (`0.10` significa 10 %).
- Las devoluciones llevan cantidad negativa e `is_return = 1`.
- La moneda del proyecto es peso dominicano (`DOP`).
- El pedido se identifica con `order_id`; no se suma `COUNT` de líneas.
- La meta se informa a nivel mes, tienda y canal.

## Corrección de rechazos

Revisa:

- `data/quality/rejected_rows.csv`
- `data/quality/data_quality_report.md`
- `data/quality/data_quality_report.json`

Corrige el origen y vuelve a colocar el archivo. Si el hash cambia, el ETL lo
procesará como una nueva versión y actualizará las mismas líneas por su clave.
