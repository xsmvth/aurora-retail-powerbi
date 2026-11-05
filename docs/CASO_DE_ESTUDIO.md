# Caso de estudio · Aurora Retail

## Problema

La dirección comercial necesitaba una lectura única de ventas provenientes de
tienda física, ecommerce y delivery. Los reportes estaban separados, el cálculo
de margen no incluía devoluciones de forma consistente y el seguimiento de metas
se hacía manualmente en hojas de cálculo.

## Objetivo

Crear una solución BI reproducible que:

1. recibiera nuevos lotes de venta sin duplicar información;
2. validara la calidad antes de cargar;
3. centralizara ventas, clientes, productos, tiendas y metas;
4. permitiera analizar margen, recompra y desviación contra objetivo;
5. actualizara el informe con una frecuencia diaria.

## Solución

Se diseñó un pipeline en Python con tres capas:

- **Landing:** archivos CSV por trimestre y referencias maestras.
- **Warehouse:** modelo estrella en SQLite, con cinco dimensiones, ventas y metas.
- **Consumo:** exportaciones atómicas para Power BI y ruta PostgreSQL para refresh
  programado desde la nube.

La carga es incremental por hash de archivo y se puede repetir sin duplicar
ventas. Antes de insertar, el ETL valida claves, tipos, descuentos y devoluciones.
Los errores se aíslan y quedan trazables.

## Modelo

```text
dim_date  ─┐
dim_customer├─→ fact_sales ←─ dim_product
dim_store  │                 ←─ dim_channel
dim_channel┘

dim_date → dim_month → fact_targets ← dim_store, dim_channel
```

La granularidad de venta es una línea de pedido. Las devoluciones se almacenan
con cantidad negativa, de modo que ingresos, costo y margen son netos.

## Tablero

### Dirección

- Ingresos netos, margen, pedidos, ticket y cumplimiento de meta.
- Tendencia mensual contra objetivo.
- Mezcla por canal y categorías líderes.

### Comercial

- Ranking de tiendas.
- Contribución y margen por canal.
- Detalle de categorías.
- Métodos de pago.

### Clientes y calidad

- Clientes activos y recompra.
- Compradores de una sola vez.
- Tasa de devolución por categoría.
- Estado de controles del pipeline.

## Conclusiones

- El negocio simulado genera **RD$ 40.1 M** y un margen bruto de **33.4 %**.
- Diciembre 2025 fue el pico de ingresos con **RD$ 2.6 M**.
- La tienda Aurora Naco es la de mayor contribución.
- Cuidado personal es la categoría principal, con 18.1 % de los ingresos.
- El 60 % de los compradores registró una sola compra, lo que abre una
  oportunidad clara de campañas de segunda compra.
- El cumplimiento global de meta es 99.4 %, pero la lectura debe hacerse por
  tienda y canal para localizar desviaciones.

## Decisiones de diseño

- **Import mode** en Power BI para mejor rendimiento; la actualización se
  resuelve desde PostgreSQL o gateway.
- **Modelo estrella** para relaciones simples y medidas consistentes.
- **Idempotencia** en dos niveles para tolerar reintentos.
- **Controles antes de carga** para evitar que errores de origen lleguen al BI.
- **Anonimización** y datos ficticios para publicar el proyecto sin exponer
  información personal.

## Próximos pasos

- Integrar inventario y costo logístico.
- Añadir campañas y atribución para medir realmente el uplift de recompra.
- Incorporar alertas de desviación y suscripciones en Power BI Service.
- Migrar la orquestación a un scheduler corporativo o Airflow en producción.
