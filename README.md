# QuickPay

A simplified peer-to-peer payments API (Cash App style) , built as a portfolio piece to show backend engineering.

The one claim this project makes : **money moves once , never twice** , even when the network drops , the user double taps , or two transfers hit the same wallet at the same moment.

Stack : Django 6.1 , Django REST Framework , SimpleJWT , PostgreSQL , Python 3.14

---

## Running it

### 1. Backend

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r quikpay/requirements.txt
```

Create `quikpay/.env` (next to `manage.py`) :

```
SECRET_KEY=your-own-secret-key
DEBUG=True
DATABASE_URL=postgres://USER:PASSWORD@localhost:5432/quickpay_db
```

The Postgres user needs permission to create databases , the test runner makes its own `test_quickpay_db`.

```bash
cd quikpay
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Then in `/admin` create the one **system pool** wallet (account type `System Pool`) , deposits come out of it.

### 2. Frontend

```bash
cd frontend
python serve.py
```

Open http://127.0.0.1:8080. `serve.py` serves the page and forwards API calls to Django [the backend has no CORS setup so the page and API need one origin]. More in [frontend/README.md](frontend/README.md).

### 3. Tests

```bash
cd quikpay
python manage.py test
```

---

## Deploying on Railway

The service sleeps when idle and boots on the next request , so it costs almost nothing sitting in a portfolio.

**Heads up on timing :** Railway's sleep timer isn't configurable. A service sleeps 5 to 10 minutes after its last outbound traffic [not 30] , and the first request after that is a cold boot that can take a few seconds or return a `502` while it wakes.

1. **New project → Deploy from GitHub repo** → pick this repo
2. Service **Settings → Root Directory** : `/quikpay`
3. **New → Database → PostgreSQL** in the same project
4. Service **Variables** :

   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
   | `SECRET_KEY` | a fresh random key , not the local one |
   | `DEBUG` | `False` |
   | `ALLOWED_HOSTS` | your Railway domain , e.g. `quickpay-production.up.railway.app` |
   | `CSRF_TRUSTED_ORIGINS` | the same domain with `https://` in front |
   | `CORS_ALLOWED_ORIGINS` | your portfolio site , e.g. `https://yourname.dev` |

5. **Settings → Build → Custom Build Command** : `python manage.py collectstatic --noinput`
   Leave the start command empty , Railpack detects Django and runs `python manage.py migrate && gunicorn quikpay.wsgi:application` itself
6. **Settings → Networking → Generate Domain** (then put that domain in step 4's variables and redeploy)
7. **Settings → Deploy → Serverless** : on
8. Once it's live , open a shell with the Railway CLI (`railway ssh`) and run `python manage.py createsuperuser` , then log into `/admin` and create the **System Pool** wallet

Calling it from the portfolio : the first request after a sleep can fail , so retry once after a few seconds and show a "waking up the server" message instead of an error.

---

## API

| Method | Path | Who | What |
|---|---|---|---|
| POST | `/api/users/register/` | logged out only | sign up , account starts as `pending_kyc` |
| POST | `/api/users/login/` | anyone | email + password → JWT access & refresh |
| POST | `/api/users/token/refresh/` | anyone | new access token |
| GET | `/api/users/profile/` | logged in | your own details |
| POST | `/deposit/` | KYC approved | load money from the system pool |
| POST | `/transfer/` | KYC approved | send money to an email or phone number |
| GET | `/balance/` | KYC approved | balance worked out from the ledger |
| GET | `/history/` | KYC approved | your ledger entries , newest first |

`/deposit/` and `/transfer/` require an `idempotency_key` , amounts are sent as strings (`"35.50"`).

---

## Key decisions , and why

The full thinking [initial assumption → problem found → research → fix] lives in [webspec.md](webspec.md) , [data-models.md](data-models.md) and [service-spec.md](service-spec.md). The short version :

**Double-entry ledger , balance is never stored**
Every movement is one `Transaction` with two `Entry` rows (a debit and a credit). A balance is worked out from the entries , not kept as a number on the account. A stored number can't tell you where a rand went , a ledger can , and if total debits ever stop matching total credits something broke and you can see it.

**User wallets are liabilities**
Money in a user wallet is money QuickPay owes the user , so balance = credits − debits. The system pool is the other side of every deposit.

**Decimal , not float**
`DecimalField` with 2 decimal places and 11 digits (just under R1 billion , plenty for a consumer product). Integer cents was the other option , but on Django + DRF Decimal is the lighter one , less conversion logic to write myself.

**PostgreSQL , not SQLite**
Row-level locking. Django's `select_for_update()` does nothing on SQLite [it locks the whole database on every write] , and Postgres has a real `NUMERIC` type for exact decimals.

**Transfers are all or nothing**
Debit and credit happen inside one `transaction.atomic()` block. If anything fails between them the whole thing rolls back , no debited-sender-but-uncredited-receiver.

**Locks are taken in wallet ID order**
Both wallets are locked in one query sorted by ID , no matter who is sending to who. Without that , A→B and B→A at the same moment deadlock.

**Idempotency key is required**
Every deposit and transfer carries a unique key from the client. Same key again = the same transaction comes back , nothing new is written. The key column is unique and the create runs inside a savepoint , so two retries racing each other still only make one transaction.

**Sign-up is dual layer**
App level pre-check for duplicate email , phone and ID number for a friendly error , plus database unique constraints as the real guarantee. A race between two identical sign-ups gives one `201` and clean `400`s , never a `500`.

**Custom user , email login**
Built on `AbstractUser` for Django's hashing and permissions. Email over phone as the login [phone numbers get recycled by networks]. SA ID numbers are text not integers [someone born in 2001 starts with a 0] and are validated for date , citizenship digit and the Luhn checksum.

**KYC gates money , not the app**
A `pending_kyc` user can sign up , log in and see their profile , but can't deposit , transfer , or see a balance. The wallet only gets created when an admin approves them (a signal in the transactions app , so `users` never depends on `transactions`).

**No transfer states**
Transfers are synchronous and atomic so a "pending" state never exists. It would only be needed for review limits or external payment rails.

**Lightest version that does the job**
That's the rule I built to. Flexibility only gets added for callers that actually exist.

---

## How I know it works

`python manage.py test` runs 14 tests. The ones that matter most each force a failure on purpose :

| Test | Proves |
|---|---|
| `test_failed_entry_write_rolls_back_transaction` | a crash between the debit and the credit leaves nothing behind |
| `test_idempotency_prevents_duplicate_transfer` | the same request twice only moves money once |
| `test_concurrent_transfers_do_not_overdraw_wallet` | simultaneous sends from one wallet can't overdraw it |
| `test_rejects_overdraft` | you can't send more than you have |
| `test_id_number_is_validated` | bad SA ID numbers never reach the database |

Also checked by hand during the build : 20 transfers fired at once in both directions (no deadlocks , balances exact , debits = credits) , and 6 identical sign-ups at once (one account , five clean errors).

---

## Gap (Demo to Prod)

Designed in the webspec , not built :
- real KYC vendor [currently an admin flips the status in `/admin`]
- real funding source for deposits [currently the system pool just pays out]
- 2FA and new-device checks on login
- lock / suspend recovery flows
- cross-channel OTP account recovery
- notifications
- first-transfer confirmation code from the receiver
- session expiry handling

Known gaps in what is built :
- `/balance/` returns the balance as a JSON number instead of a string , DRF turns the `Decimal` into a float on the way out
- history entries don't name the other party
- the profile response doesn't include KYC status
- `is_active` and `status` on the user overlap , status is the real source of truth
- tests for the sign-up race and two-way deadlock exist as manual checks , not yet in `tests.py`
- no HSTS or forced https redirect configured yet (`check --deploy` warns about both)