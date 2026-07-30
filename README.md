# Q10 OrderFlow - Senior Event-Driven Microservices Architecture 🚀

Una arquitectura orientada a eventos (*Event-Driven Architecture*) de nivel Senior construida con **FastAPI**, **React + TypeScript (Vite)**, **RabbitMQ** y **PostgreSQL**. Diseñada para garantizar alta consistencia transaccional, resiliencia contra caídas del broker o de workers, e **idempotencia estricta** con bloqueo pesimista en las operaciones de almacén e inventario.

---

## 1. Instrucciones de Ejecución Rápida (Out of the Box) 📦

El proyecto se estructura bajo un esquema **Monorepo**, facilitando el despliegue de toda la topología, bases de datos y dependencias mediante un único comando en **Docker Compose** sin requerir configuraciones locales manuales.

### Levantar Todo el Sistema
Abre una terminal en la raíz de `q10-orderflow/` y ejecuta:

```bash
docker compose up -d --build
```

El orquestador levantará los servicios de forma ordenada gracias a los `healthcheck`:
1. **PostgreSQL** (Puerto `5432`): Crea esquemas e inyecta el seed inicial de 4 productos de prueba automáticamente (`init-db.sql`).
2. **RabbitMQ** (Puertos `5672` AMQP y `15672` Management UI): Inicializa el broker de mensajería asíncrona con alta persistencia.
3. **Orders API** (Puerto `8000`): Servicio FastAPI de gestión de pedidos. Expone documentación interactiva Swagger en `http://localhost:8000/docs`.
4. **Inventory Worker**: Worker en background (sin servidor HTTP) en bucle continuo consumiendo eventos y gestionando el stock con bloqueo pesimista.
5. **Frontend React + TypeScript** (Puerto `5173`): Interfaz visual Ultra-Premium accesible en `http://localhost:5173`.

---

## 2. Suites de Tests Automatizados (Pytest) 🧪

El proyecto incluye suites de pruebas exhaustivas escritas con `pytest` y bases de datos en memoria (SQLite in-memory y Mocks de RabbitMQ) para verificar la **lógica crítica**: transiciones de estado, validaciones de negocio y garantía de idempotencia.

### Ejecutar Tests de Orders API (5 Tests Críticos)
Para ejecutar la suite de pruebas del servicio de pedidos dentro del contenedor Docker:
```bash
docker compose exec orders-api pytest -v
```

**Cobertura del servicio Orders API (`test_orders.py`):**
* `test_01_create_order_pending_transition`: Valida la creación transaccional del pedido en estado inicial `Pending` y la publicación exitosa del evento `OrderCreated` a RabbitMQ.
* `test_02_order_validation_rules_and_not_found`: Valida reglas estrictas de negocio (rechazo de cantidades nulas/negativas o mayores a 100, rechazo de clientes con nombre vacío y rechazo con error 404 para SKUs no existentes en el catálogo).
* `test_03_rabbitmq_broker_offline_fallback`: Valida el manejo de fallos crítico cuando RabbitMQ está caído al intentar publicar: el pedido no queda en el limbo y pasa al estado resiliente `Failed - Broker Offline` devolviendo un HTTP 500 explicativo.
* `test_04_status_consumer_transitions_confirmed_and_rejected`: Valida las **transiciones de estado** finales (`Pending -> Confirmed` o `Pending -> Rejected`) cuando el consumidor de la API recibe las respuestas del worker de inventario por RabbitMQ.
* `test_05_consumer_idempotency_duplicate_status_events`: Valida la **idempotencia del consumidor** de estados ante reintentos de red del broker (at-least-once delivery) sin alterar ni corromper los registros en BD.

### Ejecutar Tests de Inventory Worker (3 Tests Críticos)
Para ejecutar la suite de pruebas del worker de inventario e idempotencia:
```bash
docker compose exec inventory-worker pytest -v
```

**Cobertura del servicio Inventory Worker (`test_worker.py`):**
* `test_01_process_order_stock_reservation_success`: Valida el descuento exacto de stock transaccional, registro en la tabla de idempotencia y emisión de respuesta `Confirmed`.
* `test_02_idempotency_duplicate_event_no_double_subtraction`: **Prueba Crítica de Idempotencia**: Simula la llegada de un mismo mensaje dos veces (re-entrega por error de red). Verifica que el segundo intento es interceptado por llave duplicada (`IntegrityError`), **no descuenta stock nuevamente** (el stock permanece intacto) y confirma el ACK.
* `test_03_process_order_insufficient_stock_rejected`: Valida el rechazo ordenado (`Rejected`) sin saldo negativo al solicitar más unidades que el stock disponible.

---

## 3. Decisiones de Arquitectura y Trade-Offs Asumidos ⚖️

Toda decisión arquitectónica involucra compromisos de diseño según el contexto y el tiempo de entrega del proyecto:

### A. Desacoplamiento Asíncrono con RabbitMQ vs. Llamadas HTTP Síncronas (REST/gRPC)
* **Decisión:** Comunicación 100% basada en eventos (*Event-Driven*) mediante colas de mensajería RabbitMQ para coordinar Pedidos e Inventario.
* **Justificación / Trade-off:** En una arquitectura síncrona (donde Orders API llama por HTTP al servicio de Inventario), un pico masivo de tráfico o un cuello de botella en el almacén bloquea los hilos del servidor de pedidos y provoca fallos en cascada. Al adoptar un diseño asíncrono, ganamos alta disponibilidad, tolerancia a fallos y desacoplamiento extremo, a cambio de **consistencia eventual**: el usuario recibe respuesta inmediata con estado `Pending`, y la sincronización se completa de forma invisible en background (habitualmente en <100 ms).

### B. PostgreSQL Compartida con Tablas Separadas vs. DB Per Service
* **Decisión:** Se utilizó una única instancia de PostgreSQL en Docker pero con estricta separación lógica (tablas `orders`, `stock` y `processed_events`).
* **Justificación / Trade-off:** El patrón puro de microservicios estipula una base de datos física aislada por servicio (*Database per Service*). Sin embargo, en una prueba técnica o MVP, provisionar múltiples contenedores de PostgreSQL aumenta innecesariamente el consumo de memoria RAM y la complejidad operativa al ejecutar el sistema de forma local. Con la separación lógica mantenemos la disciplina transaccional sin sobrecargar la infraestructura del evaluador.

### C. Polling Estricto en el Frontend vs. WebSockets / SSE (Server-Sent Events)
* **Decisión:** En la interfaz de React, el listado de pedidos implementa **Polling automático cada 3.5 segundos** mediante un hook especializado.
* **Justificación / Trade-off:** WebSockets o SSE permiten empujar los cambios desde el servidor con latencia cero en aplicaciones en tiempo real. Sin embargo, en un entorno con múltiples réplicas del backend y workers asíncronos, implementar WebSockets requeriría integrar Redis Pub/Sub o mantener conexiones TCP persistentes y costosas en memoria. El **Polling** fue elegido por ser completamente **sin estado (stateless)**, inmune a desconexiones intermitentes de red, trivial de balancear y suficiente para ofrecer una excelente experiencia de usuario en este alcance.

---

## 4. Manejo Explícito de Fallos y Resiliencia 🛡️

El sistema fue construido pensando en que las fallas operativas no son la excepción, sino la regla. Así se comporta ante incidentes en los nodos de la topología:

### ¿Qué pasa con el pedido si el Broker RabbitMQ está caído?
1. Si un usuario intenta crear un pedido en `POST /orders` pero el servidor RabbitMQ se encuentra desconectado o inalcanzable, la **Orders API** captura la excepción de conexión (`AMQPConnectionError` / `Exception`) durante el bloque transaccional.
2. En lugar de dejar un pedido inconsistente en la base de datos o colgado sin saber su destino, el servicio actualiza de inmediato el estado en PostgreSQL a **`Failed - Broker Offline`**.
3. La API retorna un código de error **`HTTP 500`** al frontend acompañado de un mensaje detallado explicando que el sistema de cola está indisponible temporalmente.

### ¿Qué pasa con el pedido si el servicio Inventory no responde (o se cae abruptamente)?
1. La **Orders API** sigue operando al 100% de capacidad e interrumpe ningún flujo: recibe los pedidos de los usuarios y los guarda con éxito en estado **`Pending`**.
2. Al estar las colas, exchanges y mensajes de RabbitMQ configurados con **alta persistencia en disco** (`durable=True` y `delivery_mode=2`), **ningún evento de pedido se pierde ni se descarta**. Los mensajes quedan almacenados de forma segura en las colas del broker esperando ser procesados.
3. El pedido permanecerá visible para el cliente como `Pending`. Tan pronto como el contenedor de **Inventory Worker** se reinicie, se reponga tras el fallo o se escalen nuevas réplicas en caliente, el worker se conectará y consumirá inmediatamente a toda velocidad los mensajes retenidos en orden cronológico, emitiendo de regreso los estados **`Confirmed`** o **`Rejected`** sin la menor intervención manual.

---

## 5. Garantía de Idempotencia y Concurrencia (Bloqueo Pesimista) 🔒

En redes distribuidas, los mensajes de un broker pueden ser entregados dos veces ante reinicios o cortes intermitentes de red (*At-least-once delivery*). Para evitar distorsiones como el doble descuento de inventario para un único pedido, el sistema implementa tres barreras blindadas:

1. **Tabla de Idempotencia (`processed_events`):** Cada mensaje de evento viaja con un identificador inmutable (`eventId`). Cuando el worker de inventario recibe un evento, abre una transacción de base de datos y trata de insertar este UUID como llave primaria (`PRIMARY KEY`).
2. **Rechazo Silencioso de Duplicados:** Si un mensaje es reenviado por RabbitMQ pero ya fue procesado antes, PostgreSQL arroja una excepción de integridad (`IntegrityError` por llave duplicada). El worker intercepta esta excepción al instante, **aborta el descuento adicional del stock preservando el saldo exacto**, y emite una confirmación `ACK` al broker para eliminar la tarea redundante.
3. **Bloqueo Pesimista Transaccional (`SELECT ... FOR UPDATE`):** Si múltiples workers intentan procesar compras para un producto al mismo tiempo, la consulta al stock incluye un candado pesimista de fila a nivel de motor SQL. Esto serializa el acceso a esa fila específica, impidiendo condiciones de carrera (*Race Conditions*) al verificar si queda saldo suficiente antes de restar.

---

## 6. Sección: "Qué Haría Distinto Con Más Tiempo" 💡

Para escalar este sistema de un MVP robusto hacia una plataforma Enterprise apta para soportar tráfico masivo y continuo (ej. un Black Friday en e-commerce), adoptaría las siguientes evoluciones arquitectónicas:

1. **Patrón Outbox Transaccional (Outbox Pattern & CDC Debezium):**
   Actualmente existe una pequeña ventana teórica de fallo entre hacer el `commit()` en PostgreSQL y publicar el mensaje en RabbitMQ. Para eliminar por completo este riesgo (garantía *Exactly-Once Publishing*), implementaría el **Outbox Pattern**, insertando el evento en una tabla `outbox` dentro de la misma transacción SQL del pedido y usando un servicio CDC (*Change Data Capture*) como **Debezium** para retransmitirlo de forma fiable al broker.

2. **Database per Service Físico & Event Sourcing:**
   Separaría físicamente los motores transaccionales (ej. instancias independientes de AWS RDS/Aurora para Pedidos e Inventario). Para el inventario, evaluaría adoptar un **Event Store** (*Event Sourcing*), almacenando el histórico de deltas del stock (+10, -2, -1) en lugar de sobrescribir una única celda de saldo, lo cual permitiría auditorías temporales exactas y re-construcción completa del estado anterior.

3. **Notificaciones Push en Tiempo Real (SSE + Redis Pub/Sub):**
   Reemplazaría el mecanismo de Polling cada 3.5s por **Server-Sent Events (SSE)** o **WebSockets**. Cada nueva solicitud en React se conectaría a un canal por pedido apoyado en un clúster de **Redis Pub/Sub**, notificando a la interfaz en el exacto milisegundo en que llega el estado final `Confirmed` o `Rejected`, eliminando consultas HTTP repetitivas.

4. **Observabilidad Integral & Trazabilidad Distribuida (OpenTelemetry):**
   Implementaría observabilidad avanzada integrando **OpenTelemetry**, **Prometheus** (métricas HTTP y latencias de cola) y **Grafana** (tableros visuales). Mediante la inyección de un header `TraceId` desde las cabeceras HTTP entrantes hacia las propiedades del mensaje en RabbitMQ (y hasta las consultas del worker), obtendríamos mapas de trazabilidad distribuidos vía **Jaeger / AWS X-Ray** para monitorear el recorrido completo de cada transacción entre microservicios.

5. **API Gateway & Rate Limiting (Kong / Traefik):**
   Inscribiría una capa de API Gateway al frente de los microservicios para gestionar transversalmente terminación SSL, Rate Limiting (protección contra DDoS) y verificación y decodificación de tokens JWT, liberando al backend de cargas transversales ajenas al negocio.

---
*Desarrollado con excelencia técnica por Daniel Ramos.*
