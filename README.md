# Morpheus Shop Manager

A Flask-based shop dashboard for managing products, inventory, customers, and sales. It uses SQLite for persistent storage and includes an in-app notification bell for sales, customer, and stock events.

## Features

- Dashboard and overview summaries calculated from database records.
- Product catalog with product creation and stock status.
- Inventory list with a restock action that adds five units.
- Customer list with customer creation and per-customer sales totals.
- Transaction recording with customer/product selection, stock validation, and automatic stock deduction.
- Sales history and summary totals.
- Persistent in-app notifications with unread counts and mark-as-read actions.
- Responsive layouts, table sorting/search, CSV export, and custom 404/500 pages.

## Requirements

- Python 3.10 or later
- Dependencies listed in `requirments.txt` (the filename is spelled that way in this project)

## Run locally on Windows

Open PowerShell in the project folder:

```powershell
.\env\Scripts\Activate.ps1
pip install -r .\requirments.txt
python .\app.py
```

Or run Flask directly:

```powershell
.\env\Scripts\Activate.ps1
$env:FLASK_APP = "app"
flask run
```

Open <http://127.0.0.1:5000> in your browser.

If you do not have the included virtual environment, create one first:

```powershell
py -m venv env
.\env\Scripts\Activate.ps1
pip install -r .\requirments.txt
```

## Database

The app uses SQLite. On startup, it creates the database tables if they do not exist. The default database is stored at `instance/data.db`.

The app also adds the `is_read` column to an older `notification` table when needed. For a fresh install, the schema is defined by the models in `models.py`.

Current models:

- `Customer`: name, email, and optional phone.
- `Product`: name, SKU, category, price, and stock quantity.
- `Transaction`: customer, product, quantity, and total amount.
- `Notification`: message, timestamp, and read status.
- `User`: model definition only; account registration and login are not implemented.

Back up `instance/data.db` regularly if it contains shop records. Do not delete it to reset the app unless you intend to remove the stored data.

## Pages

| Page | URL | Purpose |
|---|---|---|
| Dashboard | `/` | Store summary, recent sales, inventory, and customers |
| Overview | `/overview` | Sales totals, recent sales, and top products |
| Sales reports | `/sales` | Sales totals and transaction history |
| Stock | `/stock` | Inventory levels and restocking |
| Customers | `/customers` | Customer list and adding customers |
| Products | `/products` | Product catalog and adding products |
| Transactions | `/transactions` | Recording and reviewing sales |

## JSON API

| Method | URL | Purpose |
|---|---|---|
| `GET` | `/api/data` | Sample status response |
| `GET` | `/api/users` | List user IDs, usernames, and emails |
| `GET` | `/api/customers` | List customers |
| `GET` | `/api/products` | List products |
| `GET` | `/api/transactions` | List transactions |
| `GET` | `/api/transactions/<id>` | Get a transaction |
| `GET` | `/api/notifications` | List recent notifications and unread count |
| `POST` | `/api/notifications/<id>/read` | Mark one notification as read |
| `POST` | `/api/notifications/read-all` | Mark all notifications as read |

## Notifications

The bell loads notifications from `/api/notifications` and refreshes while the page is open. Notifications are stored in SQLite and are generated when a customer or product is added, a sale is recorded, stock is restocked, or a product becomes low/out of stock. The low-stock threshold is currently 10 units.

## Current limitations

- This is a single-shop prototype. Login and authorization are not implemented; anyone who can reach the app can access its pages and data.
- Notifications are currently shared by all users because accounts and shop ownership are not implemented.
- Transactions do not currently store their creation date/time or payment method.
- Sales summaries use all-time totals; date-based reporting is not available yet.
- The `User` model is present, but registration, login, password handling, and user-scoped data are not implemented.

## Before deployment

Do not expose Flask's development server or debug mode to the public internet. Before deploying, use a production WSGI server, set a persistent secret key in the `SECRET_KEY` environment variable, disable debug mode, and add authentication and authorization. Back up the database and use a production database appropriate to the hosting environment.
