# Program-rule provenance

Source snapshot collected **November 14, 2026**. These are USC Computer Science
department summaries; the pages themselves defer to the applicable catalogue.
The catalogue link returned HTTP 403 in this workspace, so the rules have **not
been independently checked against the full catalogue**. Do that with advisers
before making a graduation-audit claim or launching beyond a small pilot.

| Track | Department source | Snapshot model |
| --- | --- | --- |
| General | <https://www.cs.usc.edu/academic-programs/masters/computer-science-general/> | 32-unit non-thesis pathway for Fall 2024 onward; CSCI570 core. Counts curated CS graduate electives, with a two-course/eight-unit doctoral cap. Approval-dependent alternatives remain manual. |
| Artificial Intelligence | <https://www.cs.usc.edu/academic-programs/masters/artificial-intelligence/> | Fall 2026 summary: 32 units; four required courses; four group electives covering at least two groups. An extra approved course may be needed if group choices leave a unit shortfall. |
| Data Science | <https://www.cs.usc.edu/academic-programs/masters/data-science/> | 32 units; three core courses; three group electives covering both groups. Curated additional electives, a three-course DSCI cap and four-unit 400-level elective cap. |
| Game Development | <https://www.cs.usc.edu/academic-programs/masters/game-development/> | 32 units: 28 units of core/emphasis and four elective units. Curated listed electives; approval-dependent special topics remain manual. |
| Scientists and Engineers | <https://www.cs.usc.edu/academic-programs/masters/scientists-and-engineers/> | 37 units including four preparatory CSCI455x units. Degree reference uses 33 units: foundation, core and 21 elective units. Counts one of EE450/457 and at most one doctoral elective. |

The seed's `effective_from` is the **earliest cohort supported by this prototype
snapshot**, not a claim that every department rule became effective on that
date. For General and AI, the pages explicitly describe cohort differences.
For the other tracks, earlier cohorts are conservatively flagged for review
because historical catalogues were not retrieved. These fields need catalogue
versioning before deployment.

Course codes, group memberships and unit values are factual seed data in
`app/data.py`. This is a small curated course set, not all USC course offerings.
Some course unit values vary; research courses are represented at two units,
and repeated courses are not supported in this first version. No prerequisite
graph, grade validation, current-term availability or adviser approval is
inferred from the student's course code.

The engine allocates each course once. It conservatively excludes unknown or
approval-dependent items from counted credits. Its group view reports course
counts and breadth for the student to inspect; reaching a unit total never
sets `audit_complete` to true. A course can fit a requirement and still need a
prerequisite or enrollment approval that this prototype has not verified.

## Technical references

- FastAPI testing: <https://fastapi.tiangolo.com/tutorial/testing/>
- OpenAI Responses API: <https://developers.openai.com/api/reference/resources/responses/methods/create>
- OWASP password storage guidance: <https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html>

The model is configured explicitly by the team; no hardcoded model availability
or pricing claim is assumed. `store: false` controls response storage at the API
level; it is not a claim of zero provider retention under every account policy.


## Gemini adapter references (checked November 14, 2026)

- Google generateContent: <https://ai.google.dev/api/generate-content>
- Google API keys: <https://ai.google.dev/gemini-api/docs/api-key>
- Google model pricing / tier availability: <https://ai.google.dev/gemini-api/docs/pricing>

The example model is configurable; inclusion in documentation does not prove
that a particular key has quota or access. The backend preserves the same
evidence constraints and citation checks across providers.

## Walkthrough title additions (checked 2026-11-15 UTC)

Course titles were filled from the same USC department program pages above,
including AI, Data Science, Game Development, and Scientists and Engineers.
EE450 (Introduction to Computer Networks) and EE457 (Computer Systems
Organization) are confirmed on the Scientists and Engineers page and
https://minghsiehece.usc.edu/groups/ceng/curriculum/ .
Titles fill code-only placeholders on existing databases; custom titles and
stored degree rules are not overwritten. Variable units still need confirmation.
