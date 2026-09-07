# Soroco House — API Documentation

Machine-readable spec: [`design/openapi.yaml`](./openapi.yaml).
WebSocket endpoints are documented here (OpenAPI cannot express WebSocket).

---

## 1. Base URL

```
http://localhost:8000/api/v1
```

- Every path below is prefixed with the base URL. The frontend never writes `/api/v1`
  in code — its `VITE_API_BASE_URL` / `VITE_WS_BASE_URL` already carry it.
- All prices are in ₹ (INR), server-computed — never trust client-sent totals.

## 2. Authentication

- Public routes: no auth.
- Staff routes: `Authorization: Bearer <JWT>` header.
- The JWT carries the `role` (`admin` | `employee`) and is issued by
  `POST /auth/login` or `POST /auth/signup`.
- Route matrix:

| Route | Public | employee | admin |
|---|---|---|---|
| `GET /health` | ✔ | ✔ | ✔ |
| `GET /menu`, `POST /payment` | ✔ | ✔ | ✔ |
| `POST /menu`, `DELETE /menu/{id}`, `GET /orders` | ✖ | ✔ | ✔ |
| `/auth/*` (login, check-email, signup, me) | login/signup public; `me` = staff | ✔ | ✔ |
| `GET /admin/employees`, `POST /admin/employees`, `DELETE /admin/employees/{id}` | ✖ | ✖ | ✔ |
| `GET /order-history`, `GET /order-history/export.csv` | ✖ | ✖ | ✔ |

## 3. Response envelope (every endpoint)

**Success**

```json
{
  "status": "success",
  "code": 200,
  "message": "Orders retrieved successfully",
  "data": { },
  "errors": [],
  "timestamp": "2026-09-07T10:37:00.123Z",
  "request_id": "req-0a1b2c3d-4e5f-4a6b-9c7d-8e9f0a1b2c3d"
}
```

**Error** (`data` is always `null`)

```json
{
  "status": "error",
  "code": 400,
  "message": "Payment cancelled",
  "data": null,
  "errors": [
    { "field": "gateway.status", "code": "PAYMENT_CANCELLED", "message": "Payment was cancelled. No amount was charged. Please try again." }
  ],
  "timestamp": "2026-09-07T10:36:20.123Z",
  "request_id": "req-7c8d9e0f-1a2b-4c3d-8e4f-5a6b7c8d9e0f"
}
```

**Error codes**

| HTTP | Meaning |
|---|---|
| `200 / 201` | Success |
| `400` | Bad request (incl. payment `failed`/`cancelled`) |
| `401` | `UNAUTHORIZED` — missing/invalid/expired token or bad login |
| `403` | `FORBIDDEN` / `ADMIN_ROLE_REQUIRED` / `SIGNUP_PENDING` |
| `404` | Not found (`ACCOUNT_NOT_FOUND`, `ORDER_REF_NOT_FOUND`, …) |
| `409` | Conflict (`EMAIL_ALREADY_EXISTS`, `ACCOUNT_ALREADY_SIGNED_UP`, `ADMIN_DELETE_FORBIDDEN`) |
| `422` | `VALIDATION_ERROR` — malformed/missing fields |
| `500` | `INTERNAL_ERROR` |

---

## 4. Endpoint reference

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/health` | — | Health check |
| `GET` | `/menu` | — | Menu grouped by category |
| `POST` | `/menu` | emp/admin | Add menu item |
| `DELETE` | `/menu/{menu_uuid}` | emp/admin | Remove menu item |
| `POST` | `/payment` | — | Pay — one endpoint, two calls (below) |
| `GET` | `/orders` | emp/admin | Kitchen board, FIFO |
| `POST` | `/auth/login` | — | Login → JWT + role |
| `POST` | `/auth/check-email` | — | Signup step 1: is this email a staff account? |
| `POST` | `/auth/signup` | — | Set password for pre-created account → JWT |
| `GET` | `/auth/me` | bearer | Current user + role |
| `GET` | `/admin/employees` | admin | List employees |
| `POST` | `/admin/employees` | admin | Create employee (name + email) |
| `DELETE` | `/admin/employees/{account_uuid}` | admin | Delete employee |
| `GET` | `/order-history?from=&to=` | admin | Orders by date range |
| `GET` | `/order-history/export.csv?from=&to=` | admin | CSV export of the range |

### 4.1 `GET /health`

No request. `data = { "checks": { "server": "ok" } }`.

### 4.2 `GET /menu`

```
GET /api/v1/menu
```

Response `data`:

```json
{
  "categories": [
    {
      "category": "Hot Luxury Teas",
      "items": [
        {
          "menu_uuid": "m1111111-1111-1111-1111-111111111111",
          "menu_id": 101,
          "item_name": "Lavender Earl Grey",
          "item_description": "Clean, Floral",
          "image_url": null,
          "prices": { "standard_price": 140.00, "small_price": null, "large_price": null }
        }
      ]
    }
  ]
}
```

- Availability is **not** returned — it is frontend-only state (toggled by staff and
  streamed over `WS /ws/menu`).

### 4.3 `POST /menu` (staff: employee/admin)

Add a new item. At least **one** price is required.

```json
{
  "item_name": "Lavender Earl Grey",
  "category": "Hot Luxury Teas",
  "item_description": "Clean, Floral",
  "standard_price": 140.00,
  "small_price": null,
  "large_price": null
}
```

`201` → `data` = the created item (same shape as above). Broadcast to menu viewers over WS.

### 4.4 `DELETE /menu/{menu_uuid}` (staff)

```
DELETE /api/v1/menu/m1111111-1111-1111-1111-111111111111
```

`200` → `data: null`. `404` if the item does not exist. Broadcast over WS.

### 4.5 `POST /payment` — ONE endpoint, TWO calls

The single payment route. The backend is the source of truth for the total.

**Call 1 — INITIATE** (customer taps Pay):

```json
{
  "payment_method": "razorpay",
  "table_name": "A1",
  "customer_name": "Alex",
  "phone_number": "+919876543210",
  "items": [
    { "menu_uuid": "m2222222-2222-2222-2222-222222222222", "selected_size": "large", "quantity": 2 },
    { "menu_uuid": "m1111111-1111-1111-1111-111111111111", "selected_size": null, "quantity": 1 }
  ]
}
```

`200` → payment session created. **No order rows are written yet.**

```json
{
  "status": "success",
  "code": 200,
  "message": "Payment session created",
  "data": {
    "order_ref": "or_abc123def456",
    "amount": 460.00,
    "checkout": {
      "provider": "razorpay",
      "key_id": "rzp_test_xxxx",
      "order_id": "order_OacTl8ME3gwMWP"
    }
  },
  "errors": [],
  "timestamp": "2026-09-07T10:35:00.123Z",
  "request_id": "req-5a6b7c8d-9e0f-4a1b-8c2d-3e4f5a6b7c8d"
}
```

For **phonepay**, `checkout` is instead:

```json
{ "provider": "phonepay", "redirect_url": "https://mercury-t2.phonepe.com/v3/render/pg?token=abcdef" }
```

- Razorpay → frontend opens client-side Razorpay checkout with `key_id` + `order_id`.
- PhonePe → frontend redirects the customer to `redirect_url` (sandbox).

**Call 2 — CONFIRM** (customer returns from the gateway):

```json
{
  "order_ref": "or_abc123def456",
  "gateway": { "status": "success", "transaction_id": "pay_PkF21XS9mup1b9" }
}
```

- **`success`** → order header + items inserted, bill SMS sent to `phone_number`,
  order broadcast to the kitchen. `200`:

```json
{
  "status": "success",
  "code": 200,
  "message": "Order placed successfully",
  "data": { "order_number": 12, "total_price": 460.00, "payment_method": "razorpay" },
  "errors": [],
  "timestamp": "2026-09-07T10:36:12.123Z",
  "request_id": "req-6b7c8d9e-0a1f-4b2c-9d3e-4f5a6b7c8d9e"
}
```

- **`failed` / `cancelled`** → **no DB rows**, `400` with a friendly message
  (cart stays intact), e.g.:

```json
{
  "status": "error",
  "code": 400,
  "message": "Payment cancelled",
  "data": null,
  "errors": [
    { "field": "gateway.status", "code": "PAYMENT_CANCELLED", "message": "Payment was cancelled. No amount was charged. Please try again." }
  ],
  "timestamp": "2026-09-07T10:36:20.123Z",
  "request_id": "req-7c8d9e0f-1a2b-4c3d-8e4f-5a6b7c8d9e0f"
}
```

Idempotency: confirming the same `order_ref` twice returns the existing order — never a duplicate.

### 4.6 `GET /orders` (staff: employee/admin)

Kitchen board. Response `data.orders` is **oldest first (FIFO)**. No status field
(status In-Queue/Preparing/Prepared is frontend-only).

```json
{
  "orders": [
    {
      "order_uuid": "o9999999-9999-9999-9999-999999999999",
      "order_number": 12,
      "table_name": "A1",
      "customer_name": "Alex",
      "phone_number": "+919876543210",
      "payment_method": "razorpay",
      "total_price": 460.00,
      "placed_at": "2026-09-07T10:36:12.123Z",
      "items": [
        { "item_name": "Classic Cold Brew", "selected_size": "large", "quantity": 2, "unit_price": 180.00, "line_total": 360.00 }
      ]
    }
  ]
}
```

### 4.7 `POST /auth/login`

```json
{ "email": "thameem@restaurant.com", "password": "supersecret123" }
```

`200` →

```json
{
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 480,
    "role": "admin",
    "user": { "account_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "name": "Thameem", "email": "thameem@restaurant.com", "role": "admin" }
  }
}
```

Errors: `401 INVALID_CREDENTIALS`, `403 SIGNUP_PENDING` (account has no password yet —
direct the user to `/signup`).

### 4.8 `POST /auth/check-email` (signup step 1)

```json
{ "email": "prathick@restaurant.com" }
```

- `200` → `data: { "email_exists": true }` — frontend reveals the password fields.
- `404` → `errors[0].code = "ACCOUNT_NOT_FOUND"`, message
  *"Invalid email address. Ask an admin to add you first."* — frontend shows the friendly error.

### 4.9 `POST /auth/signup`

Password confirm is **client-side only** (not sent to the API).

```json
{ "email": "prathick@restaurant.com", "password": "password@123" }
```

`200` → same shape as login (JWT with role `employee`). Errors:
`404 ACCOUNT_NOT_FOUND`, `409 ACCOUNT_ALREADY_SIGNED_UP`, `422` (password < 8 chars).

### 4.10 `GET /auth/me`

`200` → `data: { "account_uuid", "name", "email", "role" }`. `401` without a valid token.

### 4.11 `GET /admin/employees` (admin)

`200` →

```json
{
  "employees": [
    { "account_uuid": "e5f6g7h8-9012-3456-7890-abcdef123456", "name": "Prathick", "email": "prathick@restaurant.com", "role": "employee", "has_password": false, "created_at": "2026-03-05T10:15:00.000Z" }
  ]
}
```

`has_password` tells the admin who still needs to complete `/signup`.

### 4.12 `POST /admin/employees` (admin)

```json
{ "name": "Prathick", "email": "prathick@restaurant.com" }
```

`201` → created account (role `employee`, `has_password: false`).
`409 EMAIL_ALREADY_EXISTS`, `422` when fields invalid.

### 4.13 `DELETE /admin/employees/{account_uuid}` (admin)

```
DELETE /api/v1/admin/employees/e5f6g7h8-9012-3456-7890-abcdef123456
```

`200` → `data: null`. `404` not found. `409 ADMIN_DELETE_FORBIDDEN` if the target is an admin.

### 4.14 `GET /order-history?from=&to=` (admin)

```
GET /api/v1/order-history?from=2026-09-07T00:00:00Z&to=2026-09-07T23:59:59Z
```

The frontend’s Today / Yesterday / Custom presets are converted into `from`/`to`.
Response `data.orders` = same order shape as `GET /orders` plus `payment_status`.

### 4.15 `GET /order-history/export.csv?from=&to=` (admin)

Same range query. Returns `text/csv` with `Content-Disposition: attachment`.
Columns:

```
order_number, placed_at, table_name, customer_name, phone_number, items, total_price, payment_method, payment_status
12,2026-09-07T10:36:12.123Z,A1,Alex,+919876543210,"2x Classic Cold Brew (large)",460.00,razorpay,success
```

---

## 5. WebSockets

Base WebSocket URL: `ws://localhost:8000/api/v1`

```
WS  /ws/menu      (public — customers and staff listen)
WS  /ws/orders    (?token=<JWT>, role employee/admin)
```

### 5.1 `WS /ws/menu` (public)

Staff menu changes are broadcast here so customer menus update live with **no
refresh**. Message types (all `application/json`, server → client):

| `event` | Payload |
|---|---|
| `menu_added` | `{ "item": { menu_uuid, item_name, category, item_description, image_url, prices:{standard_price, small_price, large_price} } }` |
| `menu_removed` | `{ "menu_uuid": "..." }` |
| `menu_availability` | `{ "menu_uuid": "...", "available": false }` — frontend-only toggle broadcast from the staff UI; never persisted |

Client does not send messages; it only applies these events to the menu state
(grey-out + disable `+` when `available: false`).

### 5.2 `WS /ws/orders` (staff: employee/admin)

Authenticated by **query parameter on connect**:

```
ws://localhost:8000/api/v1/ws/orders?token=<JWT>
```

The server validates the token + role on the handshake; unauthorized connects are
rejected. Message type (server → client):

| `event` | Payload |
|---|---|
| `new_order` | the order object (same shape as an entry in `GET /orders` at §4.6) — append to the FIFO kitchen list |

When the order page loads, fetch the existing FIFO list from `GET /orders`, then
append `new_order` events as they arrive.

### 5.3 Reconnect behavior

- Client auto-reconnects with backoff.
- On `WS /ws/menu` reconnect: re-fetch `GET /menu` (state is cheap).
- On `WS /ws/orders` reconnect: re-fetch `GET /orders` (do not trust the gap).

---

## 6. Notes for implementers

- **Never trust the client** for prices/totals; recompute server-side at payment init.
- **Backend must validate the JWT + role on every staff write** (`POST /menu`,
  `DELETE /menu/...`, `/orders`, `/admin/*`, `/order-history`, `/order-history/export.csv`).
- Payment keys are **sandbox only** (`DEV_` prefix in the backend `.env`), SMS is
  Fast2SMS free key (`DEV_FAST2SMS_API_KEY`, `DEV_SMS_MOCK` toggle).
- Order number is the customer-facing number shown on the success screen and SMS bill.