# Hallazgos del tablero

> Dataset simulado con fines de portafolio. Período: 2025-01-01 a 2026-10-01.

## Resumen ejecutivo

- Ingresos netos: **RD$ 40,124,079**.
- Utilidad bruta: **RD$ 13,396,349** con margen de **33.4%**.
- Pedidos: **51,864**; ticket promedio: **RD$ 774**.
- Variación de ingresos año contra año comparable: **+3.4%**.
- Cumplimiento global de meta: **99.4%**.
- Clientes activos: **32,289**; tasa de recompra: **39.6%**.

## Qué muestran los datos

1. **La estacionalidad es material.** 2025-12 fue el mes de mayor ingreso
   (RD$ 2,608,454); conviene planificar inventario, personal y campañas con antelación.
2. **La tienda líder concentra la operación.** Aurora Naco aporta
   RD$ 6,452,234 y un margen de 33.2%.
3. **Categoría principal.** Cuidado personal lidera en ingresos
   (RD$ 7,247,989); Panadería tiene el mejor margen
   (52.2%) y Abarrotes el menor
   (19.6%).
4. **Canal de venta.** Tienda física representa la mayor contribución
   (RD$ 22,404,966). La mezcla de canal debe leerse junto con ticket y margen,
   no solo con volumen.
5. **Calidad comercial.** La tasa de líneas devueltas es 2.3%;
   el tablero permite segmentar devoluciones por producto, tienda y canal.

## Recomendaciones accionables

- Revisar precios y promociones en Abarrotes para mejorar rentabilidad sin perder volumen.
- Fortalecer campañas de recompra para clientes con una sola compra y medir el efecto en ticket promedio.
- Usar el cumplimiento por tienda/canal como tablero operativo semanal; reservar la lectura mensual para dirección.
- Incorporar costo logístico y unidades devueltas cuando la empresa disponga de esas fuentes para ampliar el análisis.

## Nota metodológica

Los ingresos son netos de descuentos y devoluciones. El pedido se cuenta con `DISTINCTCOUNT(order_key)`;
la granularidad de venta es una línea de pedido. El modelo usa dimensiones de fecha, cliente, producto,
tienda y canal, con hechos de venta y metas.
