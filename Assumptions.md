
# Not implemented
No versiones, branching, commit strategy
No authentification, rate limit, and cors (I left the config folder to highligh this only) -> assuming expose through API Gateway or similar
No cache?
No Tracing and logging
Added pagination and filtering to all endpoints (regardless not requiere, best practice)

# To improve
Happy path testing, few edge cases only


# Assumptions

Definition that should validated with product team
--> Permisive approach, for example if "description (bank memo)" in the payload is sent as "" or " " (withespace) is supported and stored as null in the database. Consistency can be force.
--> Same for currency, could be a enum
--> Same for amount, could be "0" or negative
"Force" timestamps with and without miliseconds for all date/times 
--> Reject data, not "storing" what pass??? For example, amounts integer and greater than zero (points to be talked out with Product Team)
Fail Fast approach for bulk uploads, validates all the data before start processing them, if a non-valid data found, the request is rejected
Reconciliation -> when confirmed, Confirm Behavior: Update invoice status + reject other candidates for that invoice


# Placeholders
Rate Limiting
Auth
Logging