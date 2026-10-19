## Quick Pay

1. # Problem Framing 
 This project is a portfolio piece to demonstrate backend engineering skill by building a simplified P2P payment app (Cashapp style).
  Current assumptions are : 
  - money transfer between two accounts is simply subtract from account A , add to account B 
  - these transactions need to be safe and secure and should have no risk of accidental repitition due to network error
  - this type of app must follow FICA regulations (where possible for a demo style project)


2. # User path 
 
 ## Happy Path [P2P Transfer]

 ### Step 1: Sign-up
 ### Step 2: identity Verification (KYC)
 ### Step 3: Login
 ### Step 4: Load money into account 
 ### Step 5: Verify successful load 
 ### Step 6: Search for target account 
 ### Step 7: Verify target account 
 [needs a code from recieving account for first transfer]
 ### Step 8: Select transfer amount 
 ### Step 9: Verify the transfer can happen
 ### Step 10: Final verification for target account [are both the accounts active/valid]
 ### Step 11: Confirm transfer 
 ### Step 12: Transfer 
 ### Step 13: Verify Successful transfer with details 
 

3. # Data model

4. # Consistency / Failure events
## Happy Path [P2P Transfer]

### Step 1: Sign up
    - Duplicate sign-up (email/phone)
    - malformed email 
    - weak password

### Step 2: Identity Verification (KYC)
    - ID verification fails
    - ID verification rejected
    - user abandons mid-verification

### Step 3: Login
    - Wrong credentials 
    - Account locked/ Suspended
    - Session expiry mid-use

### Step 4: Load money into account
    - Funding source declined
    - Network timeout mid-load
    - Partial load (crash between source and app balance)
    - Source declined [We do not accept from this source]

### Step 5: Verify successful load 
    - Load appears successful on client but failed server-side
    - balance shown is stale

### Step 6: Search for target account
    - No matching account found
    - Multiple matches 
    - deleted or deactivated account 

### Step 7: Verify target account 
    - Account exists but is not eligable to recieve (unverified)
    - Account exists but is not eligable to recieve (restricted)
    - No transaction request from recieving account or transaction history 

### Step 8: Select transfer amouunt 
    - Amount exceeeds sender's balance 
    - Amount is malformed 
    - Amount exceeds a transfer limit

### Step 9: Verify transfer can happen
    - Insufficent funds
    - sender account itself is frozen or restricted 
    - there is an active transfer already 

### Step 10: Final Verification
    - Target account changed state between step 7 and now 
    - Senders authZ/ session invalidated between step 3 and now
    - Two transfers initiated concurrently from the same sender 
        [a noted redundancy incase step 9 verification fails]

### Step 11: Confirm transfer
    - user double taps confirm 
    - client retries after a timeout unsure if the first click worked 

### Step 12: Transfer
    - Crash/failure mid-execution (debited sender but no credited reciever)
    - concurrent transfer from recievers end (two transfers trying to write before the either can be verified so they write over the stale amount)

### Step 13: Verify successful transfer 
    - Transfer successful but confirmation notification failed to reach user 

5. ### Fail Fixes
 ## Happy Path [P2P Transfer]

 ### Step 1: Sign-up
 - Duplicate sign-up (email/phone)
  # Initial assumption
    Check the database for an existing email/phone before creating the account reject if found
  # Problem found:
    This check-then-write approach has a race condition [a system flaw where output depends on the contrallable timing or sequence of events between multiple competing
    threads or processes] in our case two sign-up requests from the same email/phone number can both pass the check before either has finished writing , resulting in two accounts with the same email. 
  # Research Notes:
    Databases support declaring a column with a UNIQUE constraint enforced atomically as part of the write itself, meaning only one of two simultaneous insert attempts can succeed , guarenteed by the database not by application logic.
  # Fix: 
    dual layer fix , app-level pre-check: query for existing email or number , before attempting write and reject early with a friendly modal error.
                     database level unique constraint: app must catch unique constraint violation from the INSERT attempt and only when write is complete the modal recieves a success message 
    - malformed email 
      # Initial assumption:
      Basic format validation is sufficient at sign-up 
      # Problem found:
      None , initial instict held
      # Research Notes:
      Format validations only job is to catch obvious typos before a KYC attempt is wasted on them. better to use existing libaries/plugins (django-phonenumber-field[phonenumbers] , email-validator)
      # Fix:
      Sign-up performs format + plausibility validation only [valid pattern + structure] not reachability that is proven in step 2 with a OTP

    - weak password
      # Initial assumption:
      A weak password should be flagged on NIST SP 800-63B guidance.
      # Problem found:
      None on the choice itself but necessary to ensure that the standard can be met without creating security vulnerabilities. 
      # Research Notes:
      breach checking should use HIBP Api via K-anonymity so that the full password never leaves the client/server unmasked.
      zxcvbn estimates guessability by pattern detecting complementary to meeting the NIST SP 800-63B
      # Fix:
      password policy enforces 12 as a minimum length , combined with a real-time feedback on strength via zxcvbn and a breach check via pwned-passwords-django. 

 ### Step 2: identity Verification (KYC)


- ID verification fails
  # Initial assumption:
  D verification is a single check against a Home Affairs API , either it works or it doesn't, handled with a simple retry.

  # Problem found:
  "No result" isn't one failure mode , it splits into timeout (no response at all), vendor error response, and vendor unreachable — each with different confidence about whether anything actually happened.
  
  The naive fix ("try a second KYC provider on failure") was scope creep relative to this project's actual goals , it doubles integration surface to solve a UX problem that has a cheaper fix.

  KYC is actually two dependent operations, not one: an ID-number lookup (against the population register) and a face-match and the face-match has no input to compare against until the ID lookup returns a photo, so ordering is forced, not a preference.
  
  Storing the user's selfie/video during the multi-day retry window raises real data-sensitivity questions (biometric data) that couldn't be resolved yet, since no data model exists.

  # Research Notes:
  - The DHA API is a gated, authorised third-party channel — realistic architecture is a commercial KYC vendor mediating the Home Affairs lookup, not a direct government integration.

  - ID-number lookup returns identity fields + (where available) the official DHA photo; face-match is a separate step comparing a live selfie against that returned photo — it is not part of the government lookup itself.

  - A cheap local face-check (selfie vs. the photo printed on the physical ID card) is a legitimate complementary check — catches "wrong person entirely" fast and cheaply — but does not prove the document itself is authentic/unforged, which is what the DHA-photo match is for. Neither one alone is sufficient; together they cover different fraud vectors.

  - POPIA (SA's data protection law) is directly relevant to biometric data retention and likely imposes stricter rules than general data , flagged for future research, not yet resolved.

  # Fix:
  1. *Retry policy:* on no response, retry the same vendor (with backoff) rather than integrating a second vendor — cheaper, avoids reconciling two vendors' data formats, doesn't expand scope beyond the project's stated goals.

  2. *User-facing flow on retry exhaustion:* account moves into a new sandboxed state, pending_kyc — full profile/setup access, but no search and no transaction ability of any kind, to prevent any auth-error creep toward unverified users interacting with verified ones.

  3. *Escalation timeline:* Day 1 — if still unresolved, prompt an admin for manual KYC review. If that fails, prompt the user to retry. Day 3 — hard deadline; if still unresolved, final "couldn't verify" failure.

  4. *Check sequencing:* local selfie-vs-ID-card-photo match runs first (cheap, no vendor call needed, single user capture reused). ID-number lookup follows; if it succeeds, the returned DHA photo enables the vendor-mediated selfie-vs-DHA-photo match. ID lookup must precede DHA face-match, since the latter's input depends on the former's output.

  5. *Biometric data retention:* raw selfie/video is retained only for the duration of the verification attempt (up to the 3-day window) and deleted on any outcome — success or failure. Only the outcome record persists long-term: verification result (pass/fail), timestamp, and failure reason where applicable.

  6. *Open item (deferred):* exact storage/encryption approach for the transient selfie/video during the active window — depends on data model design, not yet finalized. Likely a temporary, encrypted, isolated model rather than storage alongside standard account fields.
  
- ID verification rejected
  # Initial assumption: 
  A fuzzy-match threshold (70% similarity) could allow automatic retry on near-miss names.
  # Problem found:
  A similarity-based auto-approval on the exact check designed to catch identity fraud is a security hole , it doesn't just forgive typos, it also waves through genuinely different but similarly-named people, silently lowering the system's own bar with no human judgment involved.
  # Research Notes:
  A legal name isn't a fluid value the way an address might be , there's no legitimate reason for it to vary, so exact-match (post-normalization) is a reasonable standard rather than a probabilistic one. Forgiveness for a genuine typo doesn't require fuzzy-matching; a limited number of retries serves the same purpose without weakening the check itself.
  # Fix:
  1. Input normalization runs before comparison: lowercase, strip whitespace. removes formatting-noise false positives (e.g. "John Smith" vs "johnsmith"), but does not address genuine typos.
  2. Name comparison is exact-match only, post-normalization , no similarity/fuzzy-matching.
  3. On mismatch, user gets up to 3 retry attempts to correct their submitted name.
  4. The retry counter is tied to the account's verification attempt and does not reset not by elapsed time, not by session.
  5. On exhausting 3 attempts, the account locks from further automatic retry and escalates to manual verification review.


- user abandons mid-verification
  # Initial assumption:
  If a user has already submitted everything needed for verification, just complete it and notify them afterward.
  # Problem found:
  That only covers abandonment after full submission. It doesn't address a user opening the KYC flow, doing part of it (or none of it), and leaving , since checks can't run on incomplete input, this isn't a "finish it for them" case, it's an account sitting in limbo with no verification attempt to complete.
  # Research Notes:
  Verification submission is gated on having all required inputs (ID photo + selfie) captured client-side first so there's no server-side "half-submitted verification" state to design around. The only real gap is the account sitting in a pre-KYC state indefinitely if the user never submits at all.
  # Fix:
  1. Client batches KYC captures locally and only pushes to the server once the full set is ready ; avoids any incomplete-submission state server-side.
  2. Server-side, the account retains a small authoritative record of KYC status (started, expires-at) not the biometric captures themselves, which are handled separately per  the earlier retention decision.
  3. If verification is never submitted, the account's pending KYC window expires after 24 hours, with a reminder notification sent hourly during that window.
  4. If the full set is submitted before expiry, verification proceeds as designed (retry/escalation logic from the earlier resolution); if it's submitted and completes while the user isn't actively watching, they're notified of the result via notification/email the original instinct, now scoped correctly to the case it actually fits.
  5. Hourly reminders stop once the user resumes/submits : no reminder should fire after the process has already moved past the abandonment state.

 ### Step 3: Login

- Wrong credentials
  # Initial assumption:
  3 wrong-password attempts before offering a reset; additionally, a "sub-30% match" from a new IP would force 2FA + security questions, as an early fraud signal.
  # Problem found:
  The similarity-threshold idea is technically impossible given proper password hashing a hashed password can only be checked for exact match, not compared for "closeness" to the real one, since the real password is never stored or retrievable in plaintext. The underlying goal (catch fraud early, before someone brute-forces in) was legitimate; the mechanism to catch it was not.
  # Research Notes:
  Login fraud detection doesn't operate on password content it operates on context signals around the attempt (IP/geolocation, device recognition, whether this device/IP has been seen on the account before). This is a separate axis from "was the password correct," not a variant of it. A correct password from an unrecognized IP is still a legitimate fraud scenario (stolen/phished credentials) and wouldn't trip a wrong-password counter at all — so context-based step-up needs to run independently of password correctness, not only as an escalation after failed attempts.
  # Fix:
  1. Password correctness axis: 3 wrong-password attempts → account is offered a password reset flow (not locked outright reset is the resolution path).
  2. Context axis (independent): login from an unrecognized IP/device triggers mandatory 2FA + security questions before access is granted, applies regardless of whether the password entered was correct, since this check targets stolen-credential scenarios that a correct password wouldn't otherwise catch.
  3. These two checks are not sequential or dependent a login can trip context-based step-up on the very first attempt (new IP, correct password) with zero wrong-password attempts involved.

- Account locked/ Suspended
  # Initial assumption:
  Lock and suspension both need a defined path back to normal account access, independent of what caused either state.
  # Problem found
  Initially conflated "what triggers a lock/suspension" with "how is it resolved", these are separate questions; this resolution deliberately addresses only the second, regardless of cause.
  # Research Notes:
  None required resolution mechanics follow directly from the severity/reversibility distinction already established (lock = temporary/self-resolving, suspension = higher bar/manual-only), and reuse the admin-review pattern already built for KYC manual escalation rather than inventing a new one.
  # Fix:
  1. Lock resolution (self-service): user re-authenticates via the same OTP → security questions → facial-recognition chain built for 2FA-fail. Success lifts the lock automatically , no admin involvement, consistent with lock being a temporary, low-severity state.
  2. Suspension resolution (manual-only): requires human review , no self-service or automated path exists, regardless of the suspension's original cause. Reuses the same admin-review queue/approve-deny pattern already established for KYC escalation, rather than building a separate mechanism.
  3. Shared infrastructure note: one admin-review component serves every manual-resolution state in this system (KYC escalation, name-mismatch lockout, suspension) , this should be built once, not duplicated per case.

- Session expiry mid-use
  # Initial assumption:
  simply need to ensure , the same state is maintained on client and server side with no mismatch 
  # Problem found:
  # Research Notes:
  # Fix:


 ### Step 4: Load money into account


- Funding source declined
  # Initial assumption:
  # Problem found:
  # Research Notes:
  # Fix:
- Network timeout mid-load
  # Initial assumption:
  # Problem found:
  # Research Notes:
  # Fix:
- Partial load (crash between source and app balance)
  # Initial assumption:
  # Problem found:
  # Research Notes:
  # Fix:
- Source declined [We do not accept from this source]
  # Initial assumption:
  # Problem found:
  # Research Notes:
  # Fix:

 ### Step 5: Verify successful load

- Load appears successful on client but failed server-side
  # Initial assumption:
  # Problem found:
  # Research Notes:
  # Fix:

- balance shown is stale
  # Initial assumption:
  # Problem found:
  # Research Notes:
  # Fix:


 ### Step 6: Search for target account


- No matching account found
  # Initial assumption:
  # Problem found:
  # Research Notes:
  # Fix:
- Multiple matches
  # Initial assumption:
  # Problem found:
  # Research Notes:
  # Fix: 
- deleted or deactivated account
  # Initial assumption:
  # Problem found:
  # Research Notes:
  # Fix: 

 ### Step 7: Verify target account 
 [needs a code from recieving account for first transfer]

- Account exists but is not eligable to recieve (unverified)
  # Initial assumption:
  # Problem found:
  # Research Notes:
  # Fix:
- Account exists but is not eligable to recieve (restricted)
  # Initial assumption:
  # Problem found:
  # Research Notes:
  # Fix:
- No transaction request from recieving account or transaction history 
  # Initial assumption:
  # Problem found:
  # Research Notes:
  # Fix:

 ### Step 8: Select transfer amount 

- Amount exceeeds sender's balance
  # Initial assumption:
  # Problem found:
  # Research Notes:
  # Fix:

- Amount is malformed
  # Initial assumption:
  # Problem found:
  # Research Notes:
  # Fix:

- Amount exceeds a transfer limit
  # Initial assumption:
  # Problem found:
  # Research Notes:
  # Fix:


 ### Step 9: Verify the transfer can happen

- Insufficent funds
  # Initial assumption:
  # Problem found:
  # Research Notes:
  # Fix:
- sender account itself is frozen or restricted
  # Initial assumption:
  # Problem found:
  # Research Notes:
  # Fix: 
- there is an active transfer already
  # Initial assumption:
  # Problem found:
  # Research Notes:
  # Fix: 

 ### Step 10: Final verification for target account [are both the accounts active/valid]


- Target account changed state between step 7 and now
  # Initial assumption:
  # Problem found:
  # Research Notes:
  # Fix: 
- Senders authZ/ session invalidated between step 3 and now
  # Initial assumption:
  # Problem found:
  # Research Notes:
  # Fix:
- Two transfers initiated concurrently from the same sender 
        [a noted redundancy incase step 9 verification fails]
  # Initial assumption:
  # Problem found:
  # Research Notes:
  # Fix:

 ### Step 11: Confirm transfer 

- user double taps confirm
  # Initial assumption:
  # Problem found:
  # Research Notes:
  # Fix: 
- client retries after a timeout unsure if the first click worked
  # Initial assumption:
  # Problem found:
  # Research Notes:
  # Fix: 

 ### Step 12: Transfer 

- Crash/failure mid-execution (debited sender but no credited reciever)
  # Initial assumption:
  # Problem found:
  # Research Notes:
  # Fix:
- concurrent transfer from recievers end (two transfers trying to write before the either can be verified so they write over the stale amount)
  # Initial assumption:
  # Problem found:
  # Research Notes:
  # Fix:

 ### Step 13: Verify Successful transfer with details 

- Transfer successful but confirmation notification failed to reach user
  # Initial assumption:
  # Problem found:
  # Research Notes:
  # Fix: 
 

6. # Auth & Security notes
   - Deleted/Deactivated accounts remain discoverable by search (existence + deactivated status)
     regardless of the searchers transaction history with that account to support users building fraud cases independently or
     without prima facie evidence. This is a deliberate deviation from stricter privacy defaults.Not exposed: transaction history , 
     balance , other linked accounts , reason for deactivation. 

7. # API/architecture sketch

7. # Gap (Demo to Prod)