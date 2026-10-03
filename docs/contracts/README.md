# Contracts

One file per cross-lane interface: `docs/contracts/<name>.md`. Define it before either side builds against it.

Each contract states: **owner** (lane that implements it), **consumers**, **shape** (request/response, schema, example payload), **status** (draft / agreed / changed), **changelog**.

Change rule: edit via its own small PR, add a changelog line, and note it in your status file so consumers' agents pick it up. Consumers may propose changes by opening a PR or writing in the owner's "Requests to me".
