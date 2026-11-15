import re


def calculate_progress(program, history, catalog, start_date):
    """Conservative snapshot check; each course is allocated at most once.

    Completed and projected (completed+current) totals are calculated separately.
    Unmodelled/approval-dependent courses stay in the manual-review bucket.
    """
    rules = program["rules"]
    groups = rules.get("groups", [])
    group_courses = {c for g in groups for c in g["courses"]}
    by_code = {x["course_code"]: x for x in history}
    core = rules["core"]
    one_of = rules.get("one_of", [])
    prep = rules.get("prep", [])
    rows = []

    def state(codes):
        matches = [by_code[c]["status"] for c in codes if c in by_code]
        return "completed" if "completed" in matches else "current" if matches else "remaining"

    for c in prep:
        rows.append({"label": f"{c} · preparatory (excluded from degree units)", "status": state([c]), "courses": [c]})
    for c in core:
        rows.append({"label": c, "status": state([c]), "courses": [c]})
    if one_of:
        rows.append({"label": " or ".join(one_of), "status": state(one_of), "courses": one_of})

    def compute(include_current):
        selected = [h for h in history if h["status"] == "completed" or include_current]
        selected.sort(key=lambda h: (h["status"] != "completed", h["course_code"]))
        accepted, review, elective_units = [], [], 0
        degree_units = units600 = count600 = dsci_count = units400 = 0
        foundation_used = False
        for h in selected:
            code = h["course_code"]
            if code in prep:
                continue
            if code not in catalog:
                review.append({"code": code, "reason": "Outside the curated course snapshot"})
                continue
            units = catalog[code]["units"]
            level = int(re.search(r"\d{3}", code)[0])
            mandatory = code in core or (code in one_of and not foundation_used)
            mode = rules["elective_mode"]
            elective = (mode in ("cs500", "data") and code.startswith("CSCI") and 500 <= level < 700
                        and code not in ("CSCI594A", "CSCI594B", "CSCI594Z", "CSCI599"))
            elective |= code in rules.get("extra", []) or code in group_courses
            reason = "Requires catalogue/adviser review for this track"
            if code in one_of:
                if foundation_used:
                    elective = False
                else:
                    foundation_used = True
            allowed = mandatory or elective
            if not mandatory:
                if level >= 600:
                    if units600+units > rules.get("max600", 1000) or count600+1 > rules.get("max600_count", 1000):
                        allowed, reason = False, "Exceeds the modelled 600-level elective limit"
                if 400 <= level < 500 and units400+units > rules.get("max400", 0):
                    allowed, reason = False, "400-level elective approval or limit needs review"
                if code.startswith("DSCI") and dsci_count+1 > rules.get("max_dsci", 1000):
                    allowed, reason = False, "Exceeds the three-course DSCI limit"
            if not allowed:
                review.append({"code": code, "reason": reason})
                continue
            degree_units += units
            accepted.append(code)
            if not mandatory:
                elective_units += units
                if level >= 600:
                    units600 += units
                    count600 += 1
                if 400 <= level < 500:
                    units400 += units
                if code.startswith("DSCI"):
                    dsci_count += 1
        return {"degree_units": degree_units, "elective_units": elective_units, "accepted": accepted, "manual_review": review}

    completed, projected = compute(False), compute(True)
    group_details = [{"label": g["label"], "courses": g["courses"],
                      "completed": [c for c in g["courses"] if c in completed["accepted"]],
                      "projected": [c for c in g["courses"] if c in projected["accepted"]]} for g in groups]
    warnings = ["Planning reference, not a graduation audit. Grades, prerequisites, offerings, waivers and adviser approvals are not verified.",
                "Course units use a curated snapshot. Variable-unit/repeated courses need manual review."]
    applicable = start_date >= rules["effective_from"]
    if not applicable:
        warnings.insert(0, "Your start date predates this rule snapshot. These totals are illustrative; confirm your applicable catalogue before using them.")
    return {"program": program["name"], "program_id": program["id"], "source_url": program["source_url"],
            "snapshot_date": program["snapshot_date"], "rules_applicable": applicable,
            "target_degree_units": rules["total"], "requirements": rows,
            "completed": completed, "projected": projected,
            "remaining_units_after_completed": max(0, rules["total"]-completed["degree_units"]),
            "group_details": group_details, "required_group_courses": rules.get("group_count", 0),
            "required_group_diversity": rules.get("group_diversity", 0),
            "elective_target": rules["elective_units"], "notes": rules["note"], "warnings": warnings,
            "rule_summary": rules, "audit_complete": False}
