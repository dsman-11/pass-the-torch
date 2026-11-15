"""Source retrieval and transparent descriptive statistics; no synthetic reviews."""
import json
import re
from collections import Counter
from datetime import datetime, timezone
from .privacy import redact
from .aliases import canonical


def question_courses(question, explicit):
    codes = list(explicit)
    for dept, number, suffix in re.findall(r"\b(CSCI|DSCI|CTIN|MATH|ISE|EE)?\s*(\d{3})([a-zA-Z]{0,2})\b", question, re.I):
        code = canonical((dept or "CSCI").upper()+number+suffix.upper())
        if code not in codes:
            codes.append(code)
    return codes[:5]


def retrieve(db, codes, term="", instructor="", simulated=False):
    result = []
    for code in codes:
        code = canonical(code)
        query = "SELECT e.*,a.name FROM experiences e JOIN accounts a ON a.id=e.account_id WHERE e.course_code=?"
        values = [code]
        if term:
            query += " AND lower(e.term)=lower(?)"
            values.append(term)
        if instructor:
            query += " AND lower(e.instructor)=lower(?)"
            values.append(instructor)
        rows = db.execute(query+" ORDER BY e.submitted_at DESC,e.id DESC", values).fetchall()
        # Exactly one latest report per person within this filtered course view.
        # Past versions remain on disk for provenance, not additional votes.
        people = {}
        for row in rows:
            people.setdefault(row["account_id"], row)
        entries, hours, drivers, pairs = [], Counter(), Counter(), {}
        for row in people.values():
            a = json.loads(row["answers_json"])
            hours[a[0]["value"]] += 1
            drivers.update(a[1]["value"])
            pair = a[3]["value"]
            if pair["courses"] and pair["balance"] != "Not assessed / only course":
                key = tuple(sorted([code]+pair["courses"]))
                pairs.setdefault(key, Counter())[pair["balance"]] += 1
            entries.append({"id": row["id"], "citation": f"R:{row['id']}", "course_code": code,
                            "contributor_name": row["name"], "term": row["term"], "instructor": row["instructor"],
                            "enrollment_status": row["enrollment_status"], "submitted_at": row["submitted_at"],
                            "review_kind": "follow-up" if row["previous_id"] else "initial",
                            "age_days": max(0, (datetime.now(timezone.utc)-datetime.fromisoformat(row["submitted_at"])).days),
                            "verification": "simulated" if simulated else "self-reported", "is_simulated": simulated, "answers": a})
        topics = Counter()
        for r in db.execute("SELECT course_codes,section FROM information_requests"):
            if code in json.loads(r["course_codes"]):
                topics[r["section"]] += 1
        result.append({"course_code": code, "is_simulated": simulated, "unique_contributors": len(people), "total_checkins": len(rows),
                       "retrieved_checkins": min(len(entries), 12), "reviews": entries[:12],
                       "hours_distribution": dict(hours), "workload_drivers": dict(drivers),
                       "combinations": [{"courses": list(k), "contributors": sum(v.values()), "balance": dict(v)} for k, v in pairs.items()],
                       "requested_topics": dict(topics),
                       "terms": sorted({r["term"] for r in rows}), "instructors": sorted({r["instructor"] for r in rows}),
                       "scope_note": "Latest report per contributor under the chosen filters. Different instructors and terms may be present; inspect source context. Counts are descriptive, not predictions."})
    return result


def evidence_answer(bundles, progress):
    paragraphs = ["Direct evidence view. AI synthesis is unavailable; the sources below are not a generated answer to your question."]
    for b in bundles:
        code = b["course_code"]
        if not b["reviews"]:
            paragraphs.append(f"{code}: no matching reviews yet. Workload, preparation and combination advice remain unknown.")
            continue
        paragraphs.append(f"{code}: {b['unique_contributors']} distinct contributor(s). Hours outside class: "+", ".join(f"{k}: {v} report(s)" for k, v in b["hours_distribution"].items())+". These are observations, not workload predictions.")
        for r in b["reviews"][:3]:
            a = r["answers"]
            paragraphs.append(f"[{r['citation']}] {r['term']}, {r['instructor']}; {r['enrollment_status']}. Preparation: {a[2]['value']} Learning experience: {a[4]['value']} Advice: {a[5]['value']}")
    if len(bundles) > 1:
        paragraphs.append("Separate course reports do not establish the manageability of a combination. Only explicit reports of the exact course set support combination observations.")
    if progress:
        paragraphs.append(f"[P:profile] Your calculated progress: {progress['completed']['degree_units']} completed degree units; {progress['projected']['degree_units']} including current courses.")
        paragraphs.append(f"[S:{progress['program_id']}] {progress['program']}: {progress['target_degree_units']}-unit target. Department-summary planning reference, not a graduation audit.")
        if not progress["rules_applicable"]:
            paragraphs.append("Your cohort predates the loaded rules. Confirm your applicable catalogue.")
    return "\n\n".join(paragraphs)


def model_evidence(bundles):
    fields = ["hours_outside_class", "workload_drivers", "expected_prior_background",
              "exact_combination_and_balance", "learning_experience", "advice_before_registering"]
    return [{**{k: v for k, v in b.items() if k != "reviews"},
             "reviews": [{**{k: v for k, v in r.items() if k not in ("contributor_name", "answers")},
                          "feedback": {field: r["answers"][i] for i, field in enumerate(fields)}}
                         for r in b["reviews"]]} for b in bundles]


def combination_evidence(db, codes, term="", instructor="", simulated=False):
    """Deduplicate the exact selected combination across course review sets."""
    wanted = set(codes)
    if len(wanted) < 2:
        return {"courses": sorted(wanted), "unique_contributors": 0, "balance": {}, "reviews": [], "is_simulated": simulated}
    marks = ",".join("?" for _ in wanted)
    query = f"SELECT e.*,a.name FROM experiences e JOIN accounts a ON a.id=e.account_id WHERE e.course_code IN ({marks})"
    args = sorted(wanted)
    if term:
        query += " AND lower(e.term)=lower(?)"; args.append(term)
    if instructor:
        query += " AND lower(e.instructor)=lower(?)"; args.append(instructor)
    rows = db.execute(query+" ORDER BY submitted_at DESC,id DESC", args).fetchall()
    seen_context, people = set(), {}
    for row in rows:
        context = (row["account_id"],row["course_code"],row["term"],row["instructor"].casefold())
        if context in seen_context:
            continue
        seen_context.add(context)
        answers = json.loads(row["answers_json"])
        pair = answers[3]["value"]
        if set([row["course_code"]]+pair["courses"]) != wanted or pair["balance"] == "Not assessed / only course":
            continue
        people.setdefault(row["account_id"], (row, answers))
    balance, sources = Counter(), []
    for row, a in people.values():
        balance[a[3]["value"]["balance"]] += 1
        sources.append({"id":row["id"],"citation":f"R:{row['id']}","course_code":row["course_code"],
                        "contributor_name":row["name"],"term":row["term"],"instructor":row["instructor"],
                        "enrollment_status":row["enrollment_status"],"submitted_at":row["submitted_at"],
                        "review_kind":"follow-up" if row["previous_id"] else "initial", "age_days":max(0,(datetime.now(timezone.utc)-datetime.fromisoformat(row["submitted_at"])).days),
                        "verification":"simulated" if simulated else "self-reported", "is_simulated":simulated,"answers":a})
    return {"courses":sorted(wanted),"unique_contributors":len(people),"balance":dict(balance),"reviews":sources[:12],"is_simulated":simulated,
            "scope_note":"One most recent qualifying exact-set report per contributor across the selected courses. Inspect instructor, semester and dates; descriptive observations only."}
