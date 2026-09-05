# Test: New Solutions, Existing Drafts, and Bound Articles

## Scenarios

| Request and evidence | Expected behavior |
| --- | --- |
| Create a new solution; live candidate metadata is missing or the account already has an article for the PID. | Stop the new-solution route before creating code, prose, brute force, or generator. No local ledger may replace the live gate. |
| Review supplied code and prose for a problem whose solution channel is closed, with no authenticated account available. | Diagnose and revise using the supplied evidence; report known ineligibility and verification limits. Do not require new-candidate selection or perform account writes. |
| Revise an old draft that lacks independent pre-reference evidence. | Review it honestly without inventing a historical checkpoint. Any later publication must satisfy the applicable originality and verification gates. |
| Synchronize a validated draft to an explicitly bound existing article with current-task authorization. | Use the matching maintenance operation, preserve its article identity, and enforce local verification, code equality, originality, and read-back. Do not reject it merely because that same article already exists. |
| After local revision, create a new live solution article instead of updating an existing one. | Require current-task authorization and the complete live new-candidate gate. Calling the operation a revision does not exempt new article creation. |
| Submit an existing article for solution review without an Accepted record for its exact source. | Block the review operation; local revision and a valid article binding do not waive the judge gate. |

## Failure behavior

Blocking local review on new-candidate eligibility, exempting genuinely new work from selection,
claiming absent provenance, creating a replacement article during maintenance, or treating local
review as publication authorization fails the routing contract.
