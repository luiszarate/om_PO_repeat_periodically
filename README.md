# Repetición periódica de órdenes de compra — Odoo 14 CE

Este addon permite usar una orden de compra como plantilla para crear nuevas
órdenes en borrador con una periodicidad configurable.

## Funcionamiento

1. Abra una solicitud de presupuesto u orden de compra.
2. En la pestaña **Repetición periódica**, indique el intervalo, la unidad
   (días, semanas, meses o años) y la siguiente fecha de creación.
3. Active **Repetir periódicamente**.
4. Una acción planificada diaria creará la nueva orden cuando llegue la fecha y
   adelantará automáticamente la próxima fecha.

El botón **Generar ahora** permite crear una orden inmediatamente sin modificar
la siguiente fecha programada. El botón estadístico **Órdenes generadas**
muestra todas las órdenes creadas desde la plantilla.

## Copia segura

El addon no utiliza una copia indiscriminada del registro. Transfiere una lista
explícita de campos estándar de la orden y sus líneas y, adicionalmente, detecta
en tiempo de ejecución todos los campos obligatorios (`required=True`) aportados
por cualquier otro módulo. Esto permite crear la réplica aunque otro addon haya
agregado datos custom obligatorios. La orden generada:

- queda en borrador;
- recibe un número nuevo mediante la secuencia normal de Odoo;
- conserva proveedor, moneda, responsable, entrega, condiciones, notas y líneas;
- conserva en las líneas productos, cantidades, unidades, precios, impuestos y
  analítica estándar cuando esos campos existen;
- ajusta las fechas previstas de las líneas manteniendo su diferencia respecto
  a la fecha de la orden original;
- referencia la orden plantilla para mantener trazabilidad;
- queda marcada explícitamente como una instancia generada;
- no hereda la configuración de repetición.

Las instancias generadas no pueden habilitarse como plantillas ni utilizar el
botón **Generar ahora**. El cron también exige que la orden no tenga marca ni
orden de origen, evitando cadenas de repeticiones de repeticiones.

Al actualizar desde la versión anterior, una migración marca automáticamente
las réplicas existentes que ya tengan una orden de origen.

## Instalación

Copie el directorio del addon dentro de un `addons_path`, actualice la lista de
aplicaciones e instale **Purchase Order Periodic Repetition**. Requiere el módulo
estándar `purchase` de Odoo 14.

## Consideraciones

- La acción planificada procesa como máximo una ocurrencia por plantilla cada
  día. Si el servidor estuvo detenido, irá recuperando las fechas pendientes en
  ejecuciones posteriores sin crear muchas órdenes de golpe.
- Si una plantilla no se puede generar, el error queda registrado en el log y
  las demás plantillas continúan procesándose. La fecha de la plantilla fallida
  no avanza, por lo que se vuelve a intentar en la siguiente ejecución.
- Una orden cancelada no genera nuevas órdenes, aunque conserve activada la
  opción de repetición.
- Los usuarios pueden programar o generar órdenes únicamente conforme a sus
  permisos existentes sobre órdenes de compra; el addon no agrega permisos.
