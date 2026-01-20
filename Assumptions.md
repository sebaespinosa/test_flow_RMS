
Please check the following information for context before evaluating the project. I want to add many things since it's a very interesting challenge and I am aware expectations are high, but didn't want to overengineer as well, but also want to highlight that I consider all of the following topics.

# Not implemented

The following topics were consider, but not implemented on the project. Just to highligh that are important part of the solution, but out of the current focus (I hope)
- No versiones, branching, commit strategy
- No authentification, advanced rate limiting, and cors (I left the config folder to highligh this only). I am assuming the expose through API Gateway or similar pattern that can conver this topics.
- No cache trhough redis or other tool, but is almost a must.
- No Tracing (with OpenTelemetry) and logging collection. Normally I use for local development a stack of openTelemtry + Jaeger for Traces, and Loki + Grafana for log analysis.
- No advanced logging. For example, on API I like to log they request payload and response payload for better debug and performance information.
- On most endpoints, I added pagination and filtering regardless not requiere, it's a good best practice and it was part of the AI coding assistant instructions.
- Very basic hardening patterns implement like Retry for LLM connection, not circbuit breaker (although gratefull response is implemented)
- No LLM conection abstraction tooling like LiteLLM
- Basic exception handling, it would be better to follow Mozilla status codes complete
- Environment file use and included on the repo, just for the challenge. It shouldn't be include on the repo, and for production a secret store should be use
- No docker-compose and Dockerfile add for building and creating other tools environment, but it was consider
- No CI/CD script add, but I am very familiar with them and deploying to cloud services following best practices.

# To improve
- Happy path testing only for most endpoints, only few edge cases covered like empty data, negative values. But I am aware non-happy paths are the real testing.


# Assumptions

I proceed as the following, but this are topics that need a validation or discussion with produt teams, product owners, etc.
- Permisive approach, for example if "description (bank memo)" in the payload is sent as "" or " " (withespace) is supported and stored as null in the database. Consistency can be forced.
- Same for currency, could be a enum
- Same for amount, could be "0" or negative
- "Force" timestamps with and without miliseconds for all date/times 
- Reject data approach, if payload data is not completele valid, it's not processed at all. For example, one amount on the list of bank transactions is not integer and greater than zero.
- Related to above, Fail Fast approach for bulk uploads, validates all the data before start processing them, if a non-valid data found, the request is rejected
- For the reconciliation, when confirmed, it update invoice status + reject other candidates for that invoice
- Database migrations files approach using Alembic
