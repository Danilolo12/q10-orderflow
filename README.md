# Q10 OrderFlow - Senior Event-Driven Microservices Architecture 

Una arquitectura orientada a eventos de nivel Senior construida con **FastAPI**, **React + TypeScript (Vite)**, **RabbitMQ** y **PostgreSQL**. Diseñada para garantizar alta consistencia transaccional, resiliencia contra caídas del broker o de workers, e **idempotencia obligatoria** con bloqueo pesimista en las operaciones de almacén.

---

## 1. Instrucciones de Ejecución Rápida (Docker Compose) 

El proyecto se estructura bajo un esquema **Monorepo**, facilitando el despliegue de toda la topología y dependencias mediante un único comando sin requerir configuraciones locales manuales.

### Levantar Todo el Sistema (Out of the Box)
Abre una terminal en la raíz de `q10-orderflow/` y ejecuta:

```bash
docker compose up -d --build
```

El orquestador levantará en orden gracias a los `healthcheck`:
1. **PostgreSQL** (Puerto `5432`): Crea esquemas y ejecuta el seed inicial de 4 productos de prueba automáticamente a través de `init-db.sql`.
2. **RabbitMQ** (Puertos `5672` AMQP y `15672` Management UI): Con colas duraderas preconfiguradas.
3. **Orders API** (Puerto `8000`): Expone la documentación Swagger en `http://localhost:8000/docs`.
4. **Inventory Worker**: Proceso headless en bucle escuchando eventos de stock.
5. **Frontend React + TypeScript** (Puerto `5173`): Interfaz visual Ultra-Premium accesible en `http://localhost:5173`.

---

### Cómo Ejecutar las Suites de Tests Automatizados 

Las pruebas de integración y unitarias (que verifican la idempotencia transaccional y los fallos en cascada) están escritas en `pytest` y utilizan bases de datos en memoria para máxima velocidad.

Para ejecutar los tests de **Orders API**:
```bash
docker compose exec orders-api pytest
```

Para ejecutar los tests de **Inventory Worker** (Incluye prueba de Idempotencia por llave duplicada):
```bash
docker compose exec inventory-worker pytest
```

---

## 2. Trade-Offs Asumidos ⚖️

Toda decisión de arquitectura involucra compromisos de diseño según el contexto y el tiempo de entrega. Aquí detallo los trade-offs asumidos para este proyecto:

### A. PostgreSQL Compartida con Tablas/Esquemas Separados vs. DB Per Service
* **Decisión:** Se optó por una única instancia de PostgreSQL en Docker pero con separación lógica estricta de responsabilidades (tabla `orders`, tabla `stock`, y tabla `processed_events`).
* **Justificación / Trade-off:** El patrón puro de microservicios aboga por una base de datos física aislada por servicio (*Database per Service*). Sin embargo, en una prueba o MVP de alto nivel, provisionar múltiples contenedores de Postgres aumenta innecesariamente el consumo de RAM, el tiempo de arranque en Docker y la complejidad operativa del examinador. Con esta separación lógica mantenemos la disciplina arquitectónica transaccional sin sobrecargar la infraestructura.

### B. Polling Estricto en el Frontend vs. WebSockets / SignalR / SSE
* **Decisión:** En React, el listado de pedidos implementa **Polling automático cada 3.5 segundos** mediante un hook `setInterval(..., 3500)`.
* **Justificación / Trade-off:** WebSockets o Server-Sent Events (SSE) eliminan la latencia y reducen el tráfico HTTP en arquitecturas con millones de usuarios al empujar los eventos desde el backend. Sin embargo, su implementación en FastAPI implica mantener conexiones persistentes en memoria o usar Redis como Pub-Sub para escalar workers. El **Polling** fue elegido por ser completamente **estateless (sin estado)**, sumamente resistente a desconexiones de red, trivial de balancear horizontalmente con Ngninx y más que suficiente para garantizar una experiencia ágil con tiempos de desarrollo acotados.

---

## 3. Manejo Resiliente de Fallos Documentado 

El sistema fue diseñado preventivamente para tolerar caídas abruptas en cualquiera de sus nodos:

### Caso 1: ¿Qué pasa si RabbitMQ no responde al crear un pedido?
1. Si un usuario intenta crear un pedido en `POST /orders` pero RabbitMQ está inactivo o rechaza la conexión, el servicio **Orders API** captura la excepción de forma transaccional.
2. En lugar de dejar un pedido inconsistente o colgado en el limbo, el estado del pedido en la base de datos se cambia automáticamente a **`Failed - Broker Offline`**.
3. La API retorna un código de estado **`HTTP 500`** acompañado de un mensaje explicativo y claro hacia el frontend.

### Caso 2: ¿Qué pasa si el Inventory Worker se cae o muere de repente?
1. Los pedidos generados por los usuarios continúan siendo atendidos sin problemas en la **Orders API**, quedando almacenados con estado inicial **`Pending`**.
2. Gracias a que el exchange, las colas y los mensajes de RabbitMQ están declarados con alta persistencia (`durable=True` y `delivery_mode=2`), **ningún evento de pedido se pierde**; quedan encolados seguros en el disco del broker.
3. En cuanto el contenedor de **Inventory Worker** se reinicie o se recupere, se reconectará y consumirá inmediatamente a toda velocidad los mensajes pendientes, cambiando el estado del inventario y notificando los nuevos estados (**`Confirmed`** o **`Rejected`**) de regreso a la Orders API.

---

## 4. Garantía de Idempotencia y Concurrencia 

En redes distribuidas, los mensajes de RabbitMQ pueden ser entregados dos veces ante intermitencias (At-least-once delivery).
Para prevenir que un producto descuente doble stock de forma fraudulenta o accidental:
1. **Tabla `processed_events`:** Cada mensaje viaja con un `eventId` (UUID) inmutable. Cuando el worker recibe un evento, abre una transacción soberana de BD e intenta insertar ese UUID en la tabla de idempotencia como llave primaria (`PRIMARY KEY`).
2. **Ignorar Duplicados:** Si se produce un error `IntegrityError` (llave duplicada), el worker detecta de inmediato el re-intento de red, **ignora el descuento de stock silenciosamente** y confirma la recepción (`ACK`) al broker.
3. **Bloqueo Pesimista (`SELECT ... FOR UPDATE`):** Para evitar condiciones de carrera (*race conditions*) donde dos workers simultáneos lean un stock remanente de 1 al mismo tiempo, el worker bloquea la fila SQL de ese producto hasta terminar la transacción.

---

## 5. Sección: "Qué Haría Distinto Con Más Tiempo" 

Para escalar este sistema hacia un entorno Enterprise en producción masiva (ej. Black Friday en e-commerce), implementaría las siguientes mejoras estratégicas:

1. **Patrón Database per Service Físico & Event Sourcing:**
   Desacoplaría físicamente el almacén transaccional con una base de datos propia para Inventario y otra para Pedidos (utilizando AWS RDS por separado). Además, adoptaría un Event Store del que se pueda reconstruir el estado histórico de un pedido ante auditorías algebraicas.

2. **API Gateway & Edge Authentication:**
   Inscripción de un API Gateway (como **Kong**, **Traefik** o AWS API Gateway) delante de los contenedores para delegar tareas de Rate-Limiting, SSL Terminations, enrutamiento estático y verificación de tokens JWT, relevando a los servicios FastAPI de cargas transversales.

3. **Notificaciones en Tiempo Real con SSE o WebSockets:**
   Sustituiría el polling de React por **Server-Sent Events (SSE)** servidos a través de un endpoint dedicado en FastAPI enlazado a Redis Pub/Sub, informando a cada cliente web en el milisegundo exacto en que su pedido es confirmado sin facturación excesiva de peticiones HTTP.

4. **Observabilidad Exhautiva y Distributed Tracing (OpenTelemetry):**
   Integraría OpenTelemetry, Prometheus y Grafana (con traza distribuidas vía Jaeger o AWS X-Ray) inyectando el `TraceId` en los headers de RabbitMQ y las cabeceras HTTP. Esto permitiría tener mapas térmicos de latencia en milisegundos desde que el cliente hace clic en React hasta que se compromete la fila de PostgreSQL en el worker de inventario.

---
*Desarrollado con excelencia técnica por Daniel Ramos.*
