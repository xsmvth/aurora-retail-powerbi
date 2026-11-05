# Construcción del tablero en Power BI

## 1. Preparación

1. Instala Power BI Desktop.
2. Ejecuta `scripts/actualizar_datos.ps1` una vez. Esto genera `data/export/`.
3. Abre Power BI Desktop y crea un archivo llamado `Aurora_Retail.pbix`.
4. En **Ver > Temas > Buscar temas**, carga `powerbi/AuroraRetail_Theme.json`.
5. Configura el lienzo en 16:9 y el fondo de página en `#F4F7F9`.

## 2. Importar las tablas

Usa **Obtener datos > Texto/CSV** para importar estas tablas desde
`data/export/`:

- `fact_sales.csv`
- `fact_targets.csv`
- `dim_date.csv`
- `dim_month.csv`
- `dim_customer.csv`
- `dim_product.csv`
- `dim_store.csv`
- `dim_channel.csv`

No importes los archivos `vw_*.csv` para el modelo principal. Son tablas de
consulta para validación rápida y se pueden usar como fuente de apoyo.

En **Transformar datos**:

- Usa origen de archivo UTF-8 y coma como delimitador.
- Convierte `date`, `month_start`, `signup_date` y `opening_date` a Fecha.
- Convierte `revenue`, `cost`, `gross_profit`, `unit_price`, `list_price`,
  `unit_cost`, `discount_pct` y `target_revenue` a número decimal.
- Convierte `is_return`, `is_active` y `is_weekend` a Verdadero/Falso.
- En `fact_targets`, deja `target_month` como Texto (`YYYY-MM`).
- Cambia los nombres mostrados de las columnas al español si lo deseas, pero
  conserva los nombres técnicos usados en las medidas.

Después de cargar, en la vista **Modelo** marca `dim_date` como tabla de fechas
usando la columna `date`.

## 3. Relaciones

El modelo es en estrella y debe quedar así:

| Desde | Hacia | Cardinalidad | Filtro |
|---|---|---|---|
| `dim_date[date_key]` | `fact_sales[date_key]` | 1 a muchos | Sencillo |
| `dim_customer[customer_key]` | `fact_sales[customer_key]` | 1 a muchos | Sencillo |
| `dim_product[product_key]` | `fact_sales[product_key]` | 1 a muchos | Sencillo |
| `dim_store[store_key]` | `fact_sales[store_key]` | 1 a muchos | Sencillo |
| `dim_channel[channel_key]` | `fact_sales[channel_key]` | 1 a muchos | Sencillo |
| `dim_date[month_key]` | `dim_month[month_key]` | Muchos a uno | Sencillo |
| `dim_month[month_key]` | `fact_targets[target_month]` | 1 a muchos | Sencillo |
| `dim_store[store_key]` | `fact_targets[store_key]` | 1 a muchos | Sencillo |
| `dim_channel[channel_key]` | `fact_targets[channel_key]` | 1 a muchos | Sencillo |

No crees relaciones directas desde `dim_date` a `fact_targets`: el calendario
diario llega al mes mediante `dim_month`.

Oculta de la vista de informe todas las claves técnicas (`*_key`) y la columna
`Nota` de `_Medidas`.

## 4. Medidas

1. Crea una tabla calculada con **Modelado > Nueva tabla**:

```DAX
_Medidas = ROW("Nota", "Carpeta de medidas del modelo")
```

2. Copia las medidas de `powerbi/medidas.dax` a esa tabla.
3. Aplica el formato:
   - Moneda RD$ sin decimales: ingresos, costos, utilidad, tickets, metas y brecha.
   - Porcentaje con un decimal: márgenes, cumplimiento, recompra, devolución y variaciones.
4. Comprueba los valores con `data/export/executive_summary.json`.

## 5. Páginas del informe

### Página 1 · Resumen ejecutivo

Encabezado: título, logo textual y período. Añade cinco tarjetas KPI:
`Ingresos netos`, `Margen bruto %`, `Pedidos`, `Ticket promedio` y
`Cumplimiento de meta`.

Visuales:

- Gráfico de líneas: eje `dim_date[month_start]`, valores `Ingresos netos` y
  `Meta de ingresos`. Activa el eje secundario solo si la escala lo requiere.
- Donut: leyenda `dim_channel[channel_name]`, valores `Ingresos netos`.
- Barras horizontales: eje `dim_product[category]`, valores `Ingresos netos`.
- Cuadro de texto con el pico del período y la categoría líder.

Segmentaciones: rango `dim_date[date]`, `dim_store[region]`,
`dim_channel[channel_name]` y `dim_customer[segment]`.

### Página 2 · Rendimiento comercial

Visuales:

- Barras horizontales por `dim_store[store_name]` con `Ingresos netos` y
  `Margen bruto %` como información secundaria.
- Barras agrupadas por canal: ingresos y margen.
- Matriz de categorías con `Ingresos netos`, `Margen bruto %`,
  `Unidades netas` y participación.
- Donut de `fact_sales[payment_method]`.
- Tarjeta con `Cumplimiento de meta`.

### Página 3 · Clientes y calidad

Visuales:

- Tarjetas: `Clientes activos`, `Tasa de recompra`, `Pedidos por cliente` y
  `Tasa de devolución`.
- Barras por `dim_customer[segment]` con ingresos.
- Barras por categoría con `Tasa de devolución`.
- Embudo o barras con activos, recurrentes y compradores de una sola vez.
- Tarjeta de calidad con estado `PASS` y 0 incidencias.

## 6. Detalles de interacción

- Activa **Filtros de fecha** y limita el período disponible a los datos cargados.
- En cada visual, activa título y subtítulo con la misma jerarquía de las capturas.
- Usa `#0F766E` para valores principales, `#2F80ED` para comparaciones,
  `#F26B5B` para alertas y `#F4B942` para objetivos.
- Configura **Editar interacciones** para que las segmentaciones afecten todos
  los visuales relevantes.
- Crea una vista móvil con las tarjetas KPI arriba y las tendencias después.
- Añade una página oculta `_Validación` con imágenes de
  `data/quality/data_quality_report.md` o una tabla de estado si lo deseas.

## 7. Publicación y actualización automática

### Opción recomendada: PostgreSQL accesible

Esta opción permite que Power BI Service actualice sin mantener una computadora
encendida.

1. Crea PostgreSQL local con `database/docker-compose.yml` o un servicio cloud
   PostgreSQL.
2. Ejecuta `database/schema_postgres.sql`.
3. Configura `DATABASE_URL` en `.env` o como variable de entorno.
4. Instala `pipeline/requirements.txt`.
5. Ejecuta `pipeline/run_pipeline.py`.
6. En Power BI, usa **Obtener datos > PostgreSQL** para importar las tablas.
7. Publica el informe en un área de trabajo.
8. En el conjunto de datos, **Configuración > Credenciales de origen de datos**
   y guarda credenciales.
9. En **Actualización programada**, activa la frecuencia diaria y una hora
   posterior al ETL, por ejemplo 06:30.

### Opción local: CSV o SQLite

Power BI Desktop puede actualizar manualmente desde los CSV. Para actualizar
desde Power BI Service necesitas un **gateway de datos local** con acceso a la
carpeta o a la base de datos. Programa el ETL al menos 30 minutos antes del
refresh del dataset.

## 8. Checklist antes de publicar

- [ ] Las relaciones muestran cardinalidad 1:* sin ambigüedad.
- [ ] `dim_date` está marcada como tabla de fechas.
- [ ] Las medidas se ven en RD$ y porcentaje con el formato correcto.
- [ ] Los KPIs coinciden con `executive_summary.json`.
- [ ] El informe responde a las segmentaciones.
- [ ] La vista móvil está revisada.
- [ ] La actualización programada se ejecutó al menos una vez correctamente.
- [ ] Las credenciales no están escritas en archivos versionados.
