# SOROCO HOUSE — Restaurant Order Management System | Full Development Prompt

> Hand this document to any engineer or AI coding agent. It is a complete, self-contained specification of the business, the product behavior, the data model, and the endpoints. Reading this alone must be enough to start building.

---

## 1. Project Overview

Build a **QR-menu ordering system** for **Soroco House**, a specialty coffee café brand. Customers scan a QR code at their table, browse the menu, add/remove items, pay via **UPI (PhonePe / Razorpay sandbox)**, and the kitchen receives the order in real time. Restaurant staff log in to a protected kitchen/admin UI.

The reference website is **https://www.soroco.coffee/** — replicate its visual look and feel for the customer-facing menu page (see Section 3).

- **Backend:** Python + FastAPI (+ WebSocket). SQL database.
- **Frontend:** React (Vite). Mobile-first (customers use phones).
- **Auth:** JWT session tokens with a role (`admin`|`employee`).
- **Payments:** PhonePe or Razorpay **sandbox only** (no live money).
- **Real-time:** WebSocket for kitchen order streaming and menu change streaming.
- **Food item images:** placeholders for now; real images will be added later.

---

## 2. Roles & Who Uses What

| Role | Access |
|---|---|
| **Customer** (no login) | `/menu`, `/cart`, `/payment` — browses, orders, pays. |
| **Employee** (login) | Everything the customer has, PLUS menu admin controls at `/menu`, the kitchen board at `/orders`. |
| **Admin** (login) | Everything the employee has, PLUS `/admin` (employee management + order history). |

- Customers do **not** have accounts. There is no customer signup.
- Accounts in the DB represent **staff only** (`employee` or `admin`). Employees are pre-created by an admin (name + email) and then set their own password via the signup flow.
- **Rule:** Admin can never be deleted via the UI.

---

## 3. Brand & UI Reference (REPLICATE soroco.coffee)

Fetch and study **https://www.soroco.coffee/** and **https://www.soroco.coffee/menus** before designing any page. Replicate this identity:

- **Logo:** "Soroco House" wordmark + logo mark (top-left).
- **Colors:** earthy, warm, minimalist tones (coffee browns, cream/off-white, warm greys). Calm, cozy, "aesthetic" feel.
- **Typography:** clean, light, modern sans-serif; large elegant headings ("Sip the Specialty", "Good to the Last Sip").
- **Layout language:** generous whitespace, hero section, image-forward gallery, cards.
- **Contact/footer:** phone, email (`enquiry@majofoods.in`), address, and a newsletter strip **"Stay in the Loop"** (email subscribe).
- **Menu style:** grouped by **category** (e.g. Coffee, Cold Brew, Hot Luxury Teas), item names with descriptions and prices in ₹ (`₹200`).
- **Cafés:** the brand has multiple locations (Nungambakkam, OMR, Anna Nagar). Keep the menu UI styled consistently regardless of café.

**Customer menu page (`/menu`) is the replica target.** Build it mobile-first: category sections, item photo placeholder, `₹` prices, and a bottom cart bar. The app pages (cart, login, kitchen, admin) follow the same warm/minimal design language.

---

## 4. Frontend Pages & Exact Behavior

### 4.1 `/menu` — Customer menu (public)

- Browse menu grouped by category. Each item card shows: **image placeholder**, **name**, **description**, **price(s)** (standard / small / large if applicable).
- Customers **add/remove items entirely in the frontend**:
  - `+` increments quantity of that item, `-` decrements.
  - Quantity 0 removes the item card control for that item.
  - No backend write happens here; this is local cart state (Context/Redux + localStorage).
- A **bottom sticky cart bar** shows item count + running total with a **downward arrow / chevron**. Clicking it navigates to `/cart`.
- **Available/Unavailable:** if an item is marked unavailable (see §4.1.1), it renders **greyed out**, labeled "Unavailable", and its `+` is disabled (cannot be added to cart).
- Live updates: menu changes broadcast by staff arrive over the WebSocket and re-render the menu **without a refresh** (Section 8).

#### 4.1.1 Staff extra controls on `/menu` (employee/admin only)

If the session JWT exists **and** the role is `employee` or `admin`, the same menu page shows extra controls:

- **"Add New Item"** button at the top → modal with **name, price, description** (image left for later) → `POST` to backend → new menu item saved to DB → broadcast over WS.
- **Remove item:** long-press (or left-swipe) an item card → popup **"Are you sure?"** → confirm → `DELETE` item from DB → broadcast over WS.
- **Availability dropdown / toggle** (Available ⇄ Unavailable) per item:
  - **Frontend-only state. No DB write.** Toggling to Unavailable greys the card out for everyone (customers included) via WS broadcast.
- Menu items disabled for customers must still be visible to staff (so they can re-enable).
- **Security:** every one of these staff actions **must be re-validated against the JWT on the backend** — never trusted from the client. `DELETE`/`POST` are blocked server-side, not just hidden in the UI.

### 4.2 `/cart` — Customer cart

- Lists every selected item: name, size (if any), quantity, line total.
- Shows **grand total bill**.
- **Payment method selection while scrolling down** (a section further down the cart page): select **PhonePe** or **Razorpay**.
- Button **"Pay"** → shows input form: **table name, customer name, phone number**.
  - Validate phone number (10-digit Indian / E.164).
- Clicking **"Proceed to Pay"** calls the backend `/payment` endpoint (Section 6).
- **On payment failure/cancel:** the customer is returned to the cart and a **user-friendly error message** is shown in the cart section (e.g. "Payment was cancelled. No amount was charged. Please try again."). Cart contents are **not** lost.
- **On success:** backend places the order and sends the bill SMS → customer sees a success screen ("Order placed! Order #12") and the cart is cleared.

### 4.3 `/payment` — (backend-driven page/redirect)

- Triggered from the cart. The backend creates a sandbox payment session; the customer is redirected to the gateway (or gateway checkout is opened) and the result is received back.
- Result handling defined in Section 7.

### 4.4 `/login` — Staff sign-in (protected routes only)

- Only reachable when a protected page redirects here.
- Fields: **email, password**.
- Backend validates credentials, and on success **issues a JWT with the role** from the DB → redirect to the originally requested page (`/orders` or `/admin`).
- Below the password field: **"Don't have an account? Please signup."** → link to `/signup`.
- Wrong credentials → friendly inline error.

### 4.5 `/signup` — Staff account password setup

- Staff accounts are **pre-created by admin (name + email only)**. Signup only *completes* an account by setting its password.
- Step 1: enter **email address** → click "Next".
  - If the email **exists** in the `accounts` table → show **Password** + **Confirm password** fields.
  - If it does **not** exist → user-friendly error, e.g. **"Invalid email address. Ask an admin to add you first."**
- Step 2: enter matching password + confirm → backend **hashes** it and stores it → redirect to `/orders`.
- Password min length ≥ 8; confirm must match.

### 4.6 `/orders` — Kitchen board (protected: employee/admin)

- **Protected.** No/invalid JWT → redirect to `/login`. After login, return to `/orders`.
- Displays incoming orders in **FIFO order** (oldest placed first), **live** via WebSocket (Section 8).
- Each order card: order number, table name, customer name, items with quantity/size, total, placed time, phone (for verification).
- **Status buttons per order — default `In-Queue`:** `In-Queue` → `Preparing` → `Prepared`.
  - **Frontend-only state. No DB transaction.** Statuses are kept in memory/UI; on a page refresh they reset to `In-Queue`. This is intentional per spec.
- Completed orders can be collapsed or cleared from the view (client-side).

### 4.7 `/admin` — Admin dashboard (protected: admin only)

- **Only `admin` role.** If an `employee` tries to access:
  - They see **"Unauthorized"** and stay on the page (no redirect to login).
- If **no session** → redirect to sign-in, then back to `/admin`.
- Two buttons/sections:
  1. **Employee**
  2. **Order History**

### 4.8 `/admin/employee` — Employee management (protect: admin only)

- Shows all employee details (name, email, role, created date).
- **Search bar** to filter employees; on its right side a **`+` icon**.
  - `+` → modal: **name + email** → `POST` → creates a new account in `accounts` (role `employee`, **password NULL**) → the new employee can then sign up (set their password) at `/signup`.
- **Delete employee:** long-press (or slide the record left) → popup **"Are you sure you want to delete the employee?"** → confirm → `DELETE` → account removed from DB.
- The user account of the currently logged-in admin cannot be deleted.

### 4.9 `/order-history` — (protect: admin only)

- Shows **all orders placed so far**, from the `orders` table (header + items).
- **Filters:** Today / Yesterday / **Custom date range**.
- **Export button** → downloads the currently filtered orders as a **CSV file** (columns: order no., date/time, table, customer, phone, items/quantities, total, payment method, status).

### 4.10 Route protection summary

| Route | Public | employee | admin |
|---|---|---|---|
| `/menu` | ✔ (customer) + staff controls if JWT role ∈ {employee, admin} | ✔ | ✔ |
| `/cart`, `/payment` | ✔ | ✔ | ✔ |
| `/orders` | login redirect | ✔ | ✔ |
| `/admin`, `/admin/employee`, `/order-history` | login redirect | ❌ "Unauthorized" stays | ✔ |

---

## 5. Data Model

The canonical schema is in **`define/er-diagram.md`** (and `define/er-diagram.mmd`). Summary:

### `accounts` (staff only; no customer accounts)
`account_uuid` PK · `account_id` · `account_name` · `account_email` **UNIQUE** · `account_password` **NULL until signup** · `account_role` ENUM(`employee`,`admin`) · `created_at/by` · `updated_at/by`

### `menu`
`menu_uuid` PK · `menu_id` · `category` · `item_name` · `item_description` · `standard_price` · `small_price` · `large_price` (all DECIMAL(10,2), nullable) · audit columns

### `orders` (transaction header)
`order_uuid` PK · `order_id` · `order_number` (customer-facing) · `table_name` · `customer_name` · `phone_number` · `payment_method` ENUM(`phonepay`,`razorpay`) · `payment_status` ENUM(`success`,`failed`,`cancelled`) · `payment_transaction_id` (gateway ref) · `total_price` · audit columns

### `order_items` (line items — one row per menu line)
`order_item_uuid` PK · `order_item_id` · `order_uuid` **FK→orders.order_uuid** · `menu_uuid` **FK→menu.menu_uuid** · `selected_size` ENUM(`standard`,`small`,`large`) NULL · `quantity` · `unit_price` (price **snapshot at order time**) · `line_total`

**Relationships:**
- `orders` 1 ── N `order_items`
- `menu` 1 ── N `order_items`
- `orders` N ── M `menu` (resolved through `order_items`)

> Note: kitchen status (In-Queue/Preparing/Prepared) is **NOT persisted**. Menu "availability" is **NOT persisted**. No `order_status` column, no `is_available` column.

---

## 6. Backend API Endpoints (FastAPI)

All JSON unless noted. Protected = requires `Authorization: Bearer <JWT>`; roles in parentheses.

| Method | Endpoint | Protection | Purpose |
|---|---|---|---|
| `GET` | `/api/menu` | public | List menu grouped by category |
| `POST` | `/api/menu` | **protected** (employee/admin) | Add menu item {name, price, description, category, prices} |
| `DELETE` | `/api/menu/{menu_uuid}` | **protected** (employee/admin) | Remove menu item |
| `POST` | `/api/payment/init` | public | Create sandbox payment session from cart + {table_name, customer_name, phone_number, payment_method} → returns gateway checkout/redirect |
| `GET/POST` | `/api/payment/callback` | public (gateway callback) | Receive gateway result (success/fail/cancel) |
| `GET` | `/api/payment/status/{order_ref}` | public | Frontend polls/validates payment outcome |
| `POST` | `/api/orders` | public (server-invoked on payment success) | Persist order header + order_items, enqueue bill SMS, broadcast to kitchen WS |
| `GET` | `/api/orders` | **protected** (employee/admin) | Orders for kitchen (FIFO) |
| `POST` | `/api/auth/login` | public | {email, password} → JWT {token, role} |
| `POST` | `/api/auth/signup` | public | {email, password, confirm} → validates email exists in accounts, sets hash → JWT |
| `GET` | `/api/auth/me` | protected | Current user + role |
| `GET` | `/api/admin/employees` | **protected** (admin) | All employees |
| `POST` | `/api/admin/employees` | **protected** (admin) | Create employee {name, email} (password NULL) |
| `DELETE` | `/api/admin/employees/{account_uuid}` | **protected** (admin) | Delete employee |
| `GET` | `/api/order-history?from=&to=` | **protected** (admin) | Orders by date range |
| `GET` | `/api/order-history/export.csv?from=&to=` | **protected** (admin) | CSV download of filtered orders |
| `WS` | `/ws/orders` | **token required** (employee/admin) | Live order stream to kitchen |
| `WS` | `/ws/menu` | public (read updates) | Live menu change stream (add/remove/availability) to all viewers |

**Always enforce on the backend:** the /menu staff actions, /orders, /admin*, /order-history must validate the JWT and role. Do not rely on the frontend hiding buttons.

---

## 7. Payment Flow (PhonePe / Razorpay SANDBOX only)

- Use **sandbox/test credentials** — no live transactions.
- **PhonePe:** set up a sandbox merchant; call "PG Create Payment" to get `redirectUrl`; the customer pays on the PhonePe sandbox page; PhonePe calls our callback with `x-callback` and `redirect` flags in `transactionId`/`status`.
- **Razorpay:** test mode keys (`rzp_test_*`); standard checkout with `RazorpayCheckout`; SDK's `onSuccess` / `onDismiss` (cancel) / error handlers.

**State machine per order payment:**

```
cart → init (creates order ref PENDING) → gateway sandbox redirect/checkout
   → success  → persist order + items → SMS bill → kitchen WS broadcast → show success screen
   → failed   → return to /cart → friendly error, cart preserved
   → cancelled → return to /cart → friendly "cancelled, no charge" error, cart preserved
```

- On **success**, the backend is the source of truth: it validates the gateway response, **then inserts `orders` + `order_items`** (pricing recomputed from DB prices & quantities; `unit_price` snapshot), stores `payment_transaction_id`, sets `payment_status='success'`.
- **Failure/cancellation must NOT create order rows.**
- Also handle gateway callback idempotency (do not double-insert if the callback/status is hit twice).

---

## 8. Real-time Streaming (FastAPI WebSocket)

1. **`/ws/menu`** — staff add/remove/availability changes are broadcast to every connected menu viewer (including the staff's own menu). Customers see updates without refresh ("no defects"). Availability & add/remove are pushed instantly.
2. **`/ws/orders`** — when a payment succeeds and the order is persisted (Section 7), the backend broadcasts the new order to all connected kitchen boards. Kitchen renders **FIFO** (oldest first).

Design: WebSocket connection per page; small manager in FastAPI (`ConnectionManager`) with `connect/disconnect/broadcast`. Menu WS is public; orders WS authenticates the token on connect with role check.

---

## 9. SMS — Bill Delivery

- On successful order placement, generate a **bill message** (order number, items w/ qty+size, line & total, payment method, table name) and send it via SMS to `phone_number` captured at payment.
- Wrap SMS in a service with a **mock/dev adapter** (log to console) and a pluggable real provider (e.g. Fast2SMS / Twilio / MSG91) behind env config. The bill format can be a plain-text friendly message.

---

## 10. Seed Data & Environment

### 10.1 Seed Data

- Seed one **admin** account (e.g. thameem@restaurant.com / hashed password) and one **employee** (email only, password NULL so it can be exercised through `/signup`).
- Seed a sample menu with categories & prices in ₹ matching the reference site (Coffee, Cold Brew, Hot Luxury Teas, Coffee Beans).
- Food images: use **placeholders** (branded color/grey boxes). A clear seam (one field/URL on the menu model or asset folder) must exist so real images can be dropped in later.

### 10.2 Backend `.env` (FastAPI)

| Variable | Example | Purpose |
|---|---|---|
| `APP_NAME` | `restaurant-api` | App identity |
| `APP_ENV` | `development` | `development` / `staging` / `production` |
| `HOST` / `PORT` | `0.0.0.0` / `8000` | Uvicorn bind |
| `DATABASE_URL` | `postgresql+psycopg://user:pass@localhost:5432/restaurant` | DB driver/DSN (or SQLite `sqlite:///./restaurant.db` locally) |
| `JWT_SECRET_KEY` | `change-me-strong-secret` | HMAC signing secret for JWT |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `JWT_EXPIRE_MINUTES` | `480` | Token lifetime (8h work shift) |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Comma-separated allowed frontend origins |
| `PAYMENT_PROVIDER` | `razorpay` | `phonepay` or `razorpay` (switch in dev) |
| `PHONEPE_MERCHANT_ID` | `MERCHANTUAT` (sandbox) | PhonePe sandbox merchant id |
| `PHONEPE_BASE_URL` | `https://api-preprod.phonepe.com/apis/pg-sandbox` | PhonePe sandbox PG endpoint |
| `PHONEPE_SALT_KEY` | (sandbox key) | PhonePe salt for checksum |
| `PHONEPE_SALT_INDEX` | `1` | Salt index |
| `PHONEPE_CALLBACK_URL` | `http://localhost:8000/api/payment/callback` | Where gateway returns the result |
| `RAZORPAY_KEY_ID` | `rzp_test_xxxx` | Razorpay test-mode key id |
| `RAZORPAY_KEY_SECRET` | (test secret) | Razorpay test-mode key secret |
| `RAZORPAY_WEBHOOK_SECRET` | (test) | Good-to-have for server-side validation |
| `SMS_PROVIDER` | `mock` | `mock` (dev) / `fast2sms` / `twilio` / `msg91` |
| `SMS_MOCK` | `true` | `true` → print bill to console, never send |
| `FAST2SMS_API_KEY` | (key) | Used when `SMS_PROVIDER=fast2sms` |
| `FAST2SMS_SENDER_ID` | `SOROCO` | Sender id for Fast2SMS |
| `TWILIO_ACCOUNT_SID` | (sid) | Used when `SMS_PROVIDER=twilio` |
| `TWILIO_AUTH_TOKEN` | (token) | Twilio auth token |
| `TWILIO_FROM_NUMBER` | `+1XXXXXXXXXX` | Twilio sender number |
| `MSG91_AUTH_KEY` | (key) | Used when `SMS_PROVIDER=msg91` |
| `SMS_SENDER_ID` | `SOROCO` | Generic sender id for SMS gateways |

```dotenv
# backend/.env sample
APP_NAME=restaurant-api
APP_ENV=development
HOST=0.0.0.0
PORT=8000
DATABASE_URL=sqlite:///./restaurant.db
JWT_SECRET_KEY=change-me-strong-secret
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=480
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
PAYMENT_PROVIDER=razorpay
RAZORPAY_KEY_ID=rzp_test_xxxx
RAZORPAY_KEY_SECRET=test-secret
RAZORPAY_WEBHOOK_SECRET=test-webhook-secret
SMS_PROVIDER=mock
SMS_MOCK=true
```

### 10.3 Frontend `.env` (React/Vite — only `VITE_*` are exposed)

| Variable | Example | Purpose |
|---|---|---|
| `VITE_APP_NAME` | `Soroco House` | Brand name shown in UI |
| `VITE_API_BASE_URL` | `http://localhost:8000` | REST API origin (no trailing slash) |
| `VITE_WS_BASE_URL` | `ws://localhost:8000` | WebSocket origin (same backend) |
| `VITE_RAZORPAY_KEY_ID` | `rzp_test_xxxx` | Razorpay checkout key id (client-side) — same test key as backend |
| `VITE_PAYMENT_METHODS` | `phonepay,razorpay` | Which methods to render in the cart (comma-separated) |
| `VITE_IMAGE_BASE_URL` | `/images` | Where food item images are served/uploaded; placeholder when empty |

```dotenv
# frontend/.env.development sample
VITE_APP_NAME=Soroco House
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
VITE_RAZORPAY_KEY_ID=rzp_test_xxxx
VITE_PAYMENT_METHODS=phonepay,razorpay
VITE_IMAGE_BASE_URL=/images
```

> **Rules:** never commit real secrets (`.env` in `.gitignore`, provide `.env.example` files). Vite exposes **only** variables prefixed `VITE_`. Keep the same `RAZORPAY_KEY_ID` client & server-side; PhonePe is entirely server-side so no PhonePe keys appear in the frontend.

---

## 11. Role & Permission Rules (recap / non-negotiable)

1. `/orders` → JWT with role `employee` or `admin`, else login.
2. `/admin*` + `/order-history` → **admin only**. Employee sees "Unauthorized" and stays.
3. /menu staff controls → token re-validated on every backend call.
4. No customer accounts. Customer identity only via the pay-time form.
5. Kitchen status buttons and menu availability are UI-only; never written to DB.
6. Order total/unit prices are computed server-side at payment success.
7. Payment sandbox only — never switch to live keys in this build.

---

## 12. Definition of Done / Acceptance Checks

- [ ] Customer browses `/menu`, + /− works locally, cart bar shows count + total.
- [ ] `/cart` shows items, total, PhonePe/Razorpay selection; Pay asks table/name/phone.
- [ ] Sandbox payment: success lands the order + SMS; cancel/fail returns friendly error with cart intact and **no DB order**.
- [ ] `/orders` blocks unauthenticated → `/login`; login returns JWT with role; kitchen stream is live and FIFO; status buttons cycle In-Queue → Preparing → Prepared (reset on refresh).
- [ ] Staff menu controls add/remove/availability update over WS for all connected menu viewers; backend rejects these without a valid token.
- [ ] `/admin` allows admin; employee gets "Unauthorized", persists on page.
- [ ] Admin can create employee (email-only) then that email can complete `/signup` and log in.
- [ ] Admin can delete employee after confirm dialog.
- [ ] `/order-history` filters today/yesterday/custom and exports CSV.
- [ ] UI mirrors the soroco.coffee warm, minimalist style (mobile-first).
- [ ] Backend tests + `ruff` clean; frontend `lint` clean.