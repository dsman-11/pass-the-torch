# Simulated course evidence

The **Try demo evidence** button changes which review database supplies course
pages, statistics and AI evidence. Real account/profile/review data remains
separate. The default source mode is real; switching is explicit and clears
conversation context. Every fictional review and generated demo answer is labelled.

## Contents

- **10 fictional contributors**, with 18 initial course reviews and two later
  check-ins (20 stored reports, not 20 independent people).
- **CSCI402 + CSCI561:** four contributors, with both comfortable/manageable and
  difficult experiences. Their backgrounds and explanations differ.
- **CSCI402 + CSCI567:** four contributors, including comfortable, manageable,
  difficult and unsustainable experiences in the fictional scenarios.
- **CSCI561 alone** and **CSCI567 alone:** one additional contributor each.
- **CSCI402:** eight contributors total; **561:** five; **567:** five.
- **CSCI566:** no reviews, deliberately.

All student names are Demo Student A–J. Instructor identities are Demo Systems
Instructor, Demo AI Instructor and Demo ML Instructor. No claim is made that
these scenarios reflect actual USC course workload or teaching quality.

Check-ins preserve older written-answer dates while updating workload hours.
The database is created beside the real database as `demo-feedback.sqlite3`.
Set `PASS_THE_TORCH_DEMO_ENABLED=false` to disable it. A custom `PASS_THE_TORCH_DEMO_DB`
path is supported but must differ from the real database path. Never point it
at an existing real database; the seeder refuses an unmarked populated file.
No seeded login credentials or fake reviews are inserted into your real DB.

## A useful recorded demonstration

First show one genuine review you contributed. Then explicitly select the
fictional demo dataset and explain that it lets the judges inspect how the
system handles multiple reports, disagreement, updates, exact combinations and
missing data. Use real Gemini generation over these labelled inputs. Return to
real mode to show that the genuine and simulated records remain distinct.

Compare 402 + 561, then 402 + 567. Ask why the fictional contributors disagreed.
The response should describe those backgrounds and observations, not declare
one pair universally easier. Click its review references. Then ask about 566;
the chatbot should identify missing experience rather than invent it.

The program requirements remain dated department reference data in either mode.
Only student-experience inputs in demo mode are simulated. Course-combination
statistics describe selected exact sets; they are not a trained ML prediction.
