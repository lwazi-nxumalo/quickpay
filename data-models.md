### Sign up data models

# Fields: 
- name, surname, ID number, email, phone, residential address, password (stored as a hash). Birthday is your call.
# Unique: 
- email, phone, ID number.
# One status field: 
- pending_kyc, active, locked, suspended, deleted.
# A new account starts as pending_kyc: 
-  it can access the app, upload KYC documents and delete itself, but can’t search or transact.
# Soft deletion rules
- user accounts are not deleted , access is simply revoked
- when user attempts to open same account with the same details allow them but require verification as normal and prevent seeing any data before deletion. 