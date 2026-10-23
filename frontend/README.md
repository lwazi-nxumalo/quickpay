# QuickPay frontend

A plain HTML, CSS and JavaScript client for the QuickPay API. It has no build step and no dependencies, and it doesn't change the Django backend.

## Run it

Start the backend from `quikpay/`:

```bash
python manage.py runserver
```

Start the frontend from `frontend/`:

```bash
python serve.py
```

Then open http://127.0.0.1:8080.

`serve.py` serves the page and forwards API requests (`/api/...`, `/transfer/`, `/deposit/`, `/balance/`, `/history/`) to Django at `http://127.0.0.1:8000`. The backend has no CORS configuration, so the page and the API have to share one origin. To use other ports, set `QUICKPAY_API` and `PORT`.

## What it does

- **Create account and sign in.** Tokens are kept in `sessionStorage` and refreshed automatically when the access token expires.
- **Add money and send money.** The recipient can be an email address or a mobile number, local (`082…`) or international (`+27…`).
- **Idempotency.** Each payment attempt gets one key. Resubmitting the same details reuses that key, so a double click or a retry after a dropped connection cannot pay twice. The key changes once a payment succeeds or the details change.
- **Amounts** are sent as strings (`"35.50"`) and summed as integer cents. They are never handled as floats.
- **Balance and history** load from `/balance/` and `/history/` when you sign in, after every payment, and when you press Refresh.
- **KYC.** A `403` or `404` from the wallet endpoints shows the "awaiting verification" state.

## Limits set by the current API

- History entries don't name the other party. The page shows "Sent to …" only for payments made from this browser.
- The profile response doesn't include `status`. Verification state is inferred from the wallet endpoints.
