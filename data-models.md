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

# AbstractUser vs AbstractBaseUser
AbstractUser , largely for the added built in security of inheriting from PermissionsMixin and the scope not needing a remarkably different type of user from the one presented

- username made email , easier to recover for user , harder to face recycle issues causing unintended consequences. 

# Money Type 
- The choice ultimately comes down to interger cent and using the built in DecimalField , I chose Decimal for the following reason , Built in means there is better support and less logic to write myself while Integercent has use cases where it can be faster in this stack where everything is built in python that advantage simply disappears with the additional logic only adding a computational burden. 

decimal places is always 2 with rands , max_digits reliably making 11 digits being a reasonable max size we are a consumer product after all unlikely to ever touch that scale of transfer or account balance internally 
