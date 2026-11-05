# Guion para presentar el proyecto

## Versión de 90 segundos

“Aurora Retail es un caso end-to-end de analítica para una cadena ficticia de
ocho tiendas. El problema era unir ventas de tienda, ecommerce y delivery,
controlar metas y entregar una lectura ejecutiva confiable.

Construí un pipeline en Python que recibe lotes CSV, valida claves, descuentos y
devoluciones, y carga un modelo estrella en SQLite. El proceso es incremental e
idempotente: reconoce archivos por hash y actualiza la venta por identificador de
línea, así que un reintento no duplica datos. También dejé una ruta PostgreSQL
para publicar en Power BI Service con refresh programado.

En Power BI diseñé tres vistas: dirección, comercial y clientes/calidad. El
escenario tiene 91.000 líneas, 52.000 pedidos y 40 millones de pesos en ingresos.
El margen es 33.4 %, la recompra 39.6 % y el cumplimiento de meta 99.4 %. El
hallazgo principal es una base amplia de compradores únicos: 60 % compró una sola
vez, lo que justifica campañas de segunda compra y seguimiento de uplift.

La entrega incluye DDL, ETL, controles de calidad, medidas DAX, tema visual,
automatización en Windows y documentación. La siguiente evolución sería agregar
costos logísticos, inventario y datos reales de satisfacción.”

## Demostración en 5 pasos

1. Abre las tres capturas y presenta el recorrido visual.
2. Muestra `data/warehouse/aurora_retail.db` y el diagrama estrella.
3. Ejecuta `scripts/actualizar_datos.ps1` y explica el registro por hash.
4. Abre el reporte de calidad: todos los controles en cero.
5. Muestra Power BI, las medidas DAX y el refresh programado.

## Bullet para CV

**Analista de Datos / BI · Proyecto Aurora Retail**

- Diseñé un pipeline ETL incremental en Python y un modelo estrella SQL/PostgreSQL
  para 91 mil líneas de venta, con validación automática e idempotencia.
- Construí un tablero Power BI de tres páginas con medidas DAX para margen,
  ticket, recompra, devoluciones, metas y variaciones temporales.
- Automaticé la actualización de datos y documenté el modelo, la calidad y la
  publicación para refresh programado.

## Posibles preguntas

**¿Por qué SQLite y PostgreSQL?**

SQLite hace reproducible la demo sin infraestructura. PostgreSQL demuestra la
ruta de producción y permite que Power BI Service actualice desde la nube.

**¿Cómo evitas duplicados?**

Doble protección: hash del archivo y `upsert` por `sale_line_id`.

**¿Cómo calculas devoluciones?**

Cada devolución es una línea con cantidad negativa; ingresos, costo y margen
quedan netos de forma automática.

**¿Por qué el pedido no se cuenta como filas?**

La tabla tiene granularidad de línea. Para el KPI de pedidos se usa
`DISTINCTCOUNT(order_key)`.

**¿Qué agregarías con datos reales?**

Costo logístico, inventario, campañas, margen por descuento, satisfacción y
metas por responsable comercial.
