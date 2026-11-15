from .progress import calculate_progress


def exploration(db, program, history, start_date):
    catalog = {r["code"]: dict(r) for r in db.execute("SELECT * FROM courses")}
    progress = calculate_progress(program, history, catalog, start_date)
    requirements = [{"id": f"required-{i}", **r} for i, r in enumerate(progress["requirements"])]
    for i, g in enumerate(progress["group_details"]):
        requirements.append({"id": f"group-{i}", "label": g["label"], "status": "elective option",
                             "courses": g["courses"], "detail": "Group options; satisfy the course-count and breadth rules together."})
    core = set(program["rules"]["core"]+program["rules"].get("one_of", [])+program["rules"].get("prep", []))
    elective_codes = []
    for code in catalog:
        if code in core:
            continue
        test = calculate_progress(program, [{"course_code": code, "status": "completed"}], catalog, start_date)
        if code in test["completed"]["accepted"]:
            elective_codes.append(code)
    requirements.append({"id": "electives", "label": "Elective choices", "status": "elective option", "courses": elective_codes,
                         "detail": f"{progress['elective_target']} elective units in this summary. Course limits and approvals still apply."})
    baseline = set(progress["projected"]["accepted"])
    existing = {c["course_code"]: c for c in history}
    candidates = []
    relevant = {code for r in requirements for code in r["courses"]}
    for code in sorted(relevant):
        if code not in catalog:
            continue
        option = dict(catalog[code])
        if code in existing:
            option.update(option_status=existing[code]["status"], option_reason="Already in your course history")
        else:
            trial = calculate_progress(program, history+[{"course_code": code, "status": "current"}], catalog, start_date)
            accepted = set(trial["projected"]["accepted"])
            problems = [r["reason"] for r in trial["projected"]["manual_review"] if r["code"]==code]
            displaced = baseline-accepted
            available = (code in accepted or code in program["rules"].get("prep", [])) and not displaced
            labels = [r["label"] for r in requirements if code in r["courses"]]
            reason = "An option for "+("your remaining elective units" if labels == ["Elective choices"] else " / ".join(labels))
            if displaced:
                reason = "Would displace counted credit for "+", ".join(sorted(displaced))+" under a track limit"
            elif problems:
                reason = problems[0]
            option.update(option_status="remaining" if available else "needs_review", option_reason=reason)
        option["requirement_labels"] = [r["label"] for r in requirements if code in r["courses"]]
        candidates.append(option)
    by_code = {c["code"]: c for c in candidates}
    for r in requirements:
        r["options"] = [by_code[c] for c in r["courses"] if c in by_code]
    return {"progress": progress, "requirements": requirements, "courses": candidates}
