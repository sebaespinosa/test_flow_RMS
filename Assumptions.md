
No versiones, branching, commit strategy
No authentification, rate limit, and cors (I left the config folder to highligh this only) -> assuming expose through API Gateway or similar
No cache?
No Tracing and logging


Added pagination and filtering to all endpoints (regardless not requiere, best practice)
Happy path testing, few edge cases only
--> Permisive approach, for example if "description (bank memo)" in the payload is sent as "" or " " (withespace) is supported and stored as null in the database. Consistency can be force.
--> Same for currency, could be a enum
--> Same for amount, could be "0" or negative
"Force" timestamps with and without miliseconds for all date/times 