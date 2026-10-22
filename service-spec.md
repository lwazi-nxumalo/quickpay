# How the service layer should work 
  ## things to prevent off bat 
  - phantom negative debits 
  - self transfer 
  - locked or frozen accounts doing things 
  - overdrafts
  - debits operations without credits and vice versa completing after a step inbetween crashed with no solution {Individual transaction movement}
  - single entry 
  - nowhere for money to go mid transaction
  - race conidtion 

  # solutions 
  - an if statement that evaluates incoming variables against simple conditional rules 
  - [need a get balance object in my Wsallet model] that needs to be called at this stage
  - transaction.atomic() , is the solution which wraps logic in a BEGIN ... COMMIT block and a seperate method to write the receipt row to the database 
  - an idempotency key is necessary to ensure network errors dont allow the same transaction to go again 
  - we need a master transaction and two seperate create() methods writing in exact decimal types , for a double entry record so that total debits always == total credits keeping the ledger at zero 
  - we need to create a system pool to hold money mid transaction 
  - django offers a mnethod .select_for_update() which i should place inside the atomic transaction 