# Restaurant Order Management ER

## Tables

### accounts

| column | constraints |
| :---: | :---: |
| account_uuid | pk, uuid, NOT NULL |
| account_id | INT, NOT NULL |
| account_name | varchar(255), NOT NULL |
| account_email | varchar(255), UNIQUE, NOT NULL |
| account_password | TEXT, NULL |
| account_role | ENUM('employee', 'admin'), NOT NULL |
| created_at | TIMESTAMP, NOT NULL |
| created_by | VARCHAR(255), NOT NULL |
| updated_at | TIMESTAMP, NULL |
| updated_by | VARCHAR(255), NULL |

### menu

| column | constraints |
| :---: | :---: |
| menu_uuid | pk, uuid, NOT NULL |
| menu_id | INT, NOT NULL |
| category | varchar(100), NOT NULL |
| item_name | varchar(255), NOT NULL |
| item_description | TEXT, NULL |
| standard_price | DECIMAL(10,2), NULL |
| small_price | DECIMAL(10,2), NULL |
| large_price | DECIMAL(10,2), NULL |
| created_at | TIMESTAMP, NOT NULL |
| created_by | VARCHAR(255), NOT NULL |
| updated_at | TIMESTAMP, NULL |
| updated_by | VARCHAR(255), NULL |

### orders

| column | constraints |
| :---: | :---: |
| order_uuid | pk, uuid, NOT NULL |
| order_id | INT, NOT NULL |
| order_number | INT, NOT NULL |
| table_name | varchar(255), NOT NULL |
| customer_name | varchar(255), NOT NULL |
| phone_number | varchar(50), NOT NULL |
| payment_method | ENUM('phonepay', 'razorpay'), NOT NULL |
| payment_status | ENUM('success', 'failed', 'cancelled'), NOT NULL |
| payment_transaction_id | varchar(255), NULL |
| total_price | DECIMAL(10,2), NOT NULL |
| created_at | TIMESTAMP, NOT NULL |
| created_by | VARCHAR(255), NOT NULL |
| updated_at | TIMESTAMP, NULL |
| updated_by | VARCHAR(255), NULL |

### order_items

| column | constraints |
| :---: | :---: |
| order_item_uuid | pk, uuid, NOT NULL |
| order_item_id | INT, NOT NULL |
| order_uuid | FK (references orders.order_uuid), NOT NULL |
| menu_uuid | FK (references menu.menu_uuid), NOT NULL |
| selected_size | ENUM('standard', 'small', 'large'), NULL |
| quantity | INT, NOT NULL |
| unit_price | DECIMAL(10,2), NOT NULL |
| line_total | DECIMAL(10,2), NOT NULL |

---

## Relationships

- `orders` 1 ── N `order_items` (one order has many line items)
- `menu` 1 ── N `order_items` (one menu item appears in many line items across orders)
- `orders` N ── M `menu` (resolved through `order_items`)

---

## Sample Data

### accounts Data

| account_uuid | account_id | account_name | account_email | account_password | account_role | created_at | created_by |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| a1b2c3d4... | 1 | Thameem | thameem@restaurant.com | hash_pass_1 | admin | 2026-03-05 10:00:00 | SYSTEM |
| e5f6g7h8... | 2 | Prathick | prathick@restaurant.com | NULL | employee | 2026-03-05 10:15:00 | SYSTEM |

### menu Data

| menu_uuid | menu_id | category | item_name | item_description | standard_price | small_price | large_price |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| m111... | 101 | Hot Luxury Teas | Lavender Earl Grey | Clean, Floral | 140.00 | NULL | NULL |
| m222... | 102 | Cold Brew | Classic Cold Brew | NULL | NULL | 140.00 | 180.00 |
| m333... | 103 | Coffee Beans | Dark Blend Bag | Strong profile | 450.00 | NULL | NULL |

### orders Data

| order_uuid | order_id | order_number | table_name | customer_name | phone_number | payment_method | payment_status | payment_transaction_id | total_price |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| o999... | 5001 | 12 | A1 | Alex | +1234567890 | phonepay | success | txn_abc123 | 320.00 |
| o888... | 5002 | 13 | B2 | Sam | +1987654321 | razorpay | success | txn_xyz789 | 180.00 |

### order_items Data

| order_item_uuid | order_item_id | order_uuid | menu_uuid | selected_size | quantity | unit_price | line_total |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| i111... | 1 | o999... | m111... | NULL | 2 | 140.00 | 280.00 |
| i222... | 2 | o999... | m333... | NULL | 1 | 40.00 | 40.00 |
| i333... | 3 | o888... | m222... | large | 1 | 180.00 | 180.00 |