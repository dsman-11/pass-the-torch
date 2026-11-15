"""Curated department-summary snapshots, NOT a complete catalogue or degree audit.

Sources fetched 2026-11-14. Applicable catalogue, STARS, approvals and advisers
remain authoritative. No student experiences are seeded here.
"""

BASE = "https://www.cs.usc.edu/academic-programs/masters/"
COURSES = {}


def add(codes, units=4):
    for code in codes.split():
        COURSES[code] = (units, code)


add("CSCI402 CSCI445L CSCI455X CSCI520 CSCI522 CSCI526 CSCI529A CSCI529B CSCI535 CSCI538 CSCI544 CSCI545 CSCI561 CSCI563 CSCI566 CSCI567 CSCI570 CSCI571 CSCI572 CSCI576 CSCI577A CSCI577B CSCI580 CSCI585 CSCI587 CSCI616 CSCI617 CSCI619 CSCI644 CSCI653 CSCI659 CSCI662 CSCI675 CSCI677 CSCI678 CSCI685 DSCI531 DSCI551 DSCI553 DSCI554 DSCI558 EE450 EE457 EE546 EE569 EE588 ISE520 ISE633 MATH458 MATH467 CTIN532L CTIN541 CTIN534L")
add("CSCI573 EE519 MATH574 MATH501 MATH502A MATH502B MATH505A MATH601", 3)
add("CSCI590 CSCI591 CTIN503 CTIN510 CTIN544 CTIN593", 2)
add("CSCI599 CTIN590 CTIN599")
for code, name in {
    "CSCI402": "Operating Systems", "CSCI455X": "Introduction to Programming Systems Design",
    "CSCI561": "Foundations of Artificial Intelligence", "CSCI566": "Deep Learning and Its Applications",
    "CSCI567": "Machine Learning", "CSCI570": "Analysis of Algorithms", "CSCI585": "Database Systems",
    "EE450": "Introduction to Computer Networks", "EE457": "Computer Systems Organization",
    "CSCI571": "Web Technologies", "CSCI576": "Multimedia Systems Design",
    "CSCI577A": "Software Engineering", "CSCI577B": "Software Engineering",
    "CSCI580": "3D Graphics and Rendering", "CSCI590": "Directed Research",
    "CSCI591": "Computer Science Research Colloquium", "CSCI599": "Special Topics",
    "CSCI445L": "Foundations of Robotics", "CSCI573": "Probabilistic Reasoning",
    "CSCI678": "Theoretical Machine Learning", "DSCI531": "Fairness in Artificial Intelligence",
    "EE546": "Mathematics of High-Dimensional Data",
    "CSCI535": "Multimodal Probabilistic Learning of Human Communication",
    "CSCI544": "Applied Natural Language Processing", "CSCI644": "Natural Language Dialogue Systems",
    "CSCI662": "Advanced Natural Language Processing", "EE519": "Speech Recognition and Processing for Multimedia",
    "CSCI545": "Robotics", "CSCI677": "Advanced Computer Vision", "EE569": "Introduction to Digital Image Processing",
    "CSCI616": "Interdisciplinary Approaches to Data-Driven Decision-Making",
    "CSCI617": "Machine Learning for/with Mixed-Integer Optimization",
    "CSCI619": "End-to-End Learning and Optimization", "CSCI659": "Introduction to Online Optimization",
    "CSCI675": "Convex and Combinatorial Optimization", "EE588": "Optimization for the Information and Data Sciences",
    "ISE633": "Large Scale Optimization and Machine Learning", "CSCI563": "Building Knowledge Graphs",
    "CSCI587": "Geospatial Data Analysis", "CSCI572": "Information Retrieval and Web Search Engines",
    "CSCI653": "High Performance Computing and Simulations", "CSCI685": "Advanced Topics in Database Systems",
    "DSCI551": "Foundations of Data Management", "DSCI553": "Foundations and Applications of Data Mining",
    "ISE520": "Optimization Theory and Algorithms: Numerical Optimization",
    "MATH467": "Theory and Computational Methods for Optimization", "MATH574": "Applied Matrix Analysis",
    "DSCI554": "Data Visualization", "DSCI558": "Building Knowledge Graphs", "MATH458": "Numerical Methods",
    "MATH501": "Numerical Analysis and Computation", "MATH502A": "Numerical Analysis", "MATH502B": "Numerical Analysis",
    "MATH505A": "Applied Probability", "MATH601": "Optimization Theory and Techniques",
    "CTIN532L": "Interactive Design and Production I", "CTIN541": "Design for Interactive Media",
    "CSCI529A": "Graduate Advanced Game Project", "CSCI529B": "Graduate Advanced Game Project",
    "CSCI520": "Computer Animation and Simulation", "CSCI522": "Game Engine Development",
    "CSCI526": "Advanced Mobile Devices and Game Consoles", "CSCI538": "Augmented, Virtual and Mixed Reality",
    "CTIN503": "Interactive Entertainment, Science, and Healthcare",
    "CTIN510": "Research Methods for Innovation, Engagement, and Assessment",
    "CTIN534L": "Experiments in Interactivity I", "CTIN544": "Experiments in Interactivity II",
    "CTIN590": "Directed Research", "CTIN593": "Integrative Project: Media-based Interventions in Health Care",
    "CTIN599": "Special Topics",
}.items():
    COURSES[code] = (COURSES[code][0], name)

AI_GROUPS = [
    {"label": "Machine learning", "courses": "CSCI573 CSCI678 DSCI531 EE546".split()},
    {"label": "Language and speech", "courses": "CSCI535 CSCI544 CSCI644 CSCI662 EE519".split()},
    {"label": "Vision and robotics", "courses": "CSCI445L CSCI545 CSCI677 EE569".split()},
    {"label": "Decision and optimization", "courses": "CSCI616 CSCI617 CSCI619 CSCI659 CSCI675 EE588 ISE633".split()},
    {"label": "AI + X", "courses": "CSCI563 CSCI587".split()},
]
DS_GROUPS = [
    {"label": "Data systems", "courses": "CSCI572 CSCI587 CSCI653 CSCI685 DSCI551".split()},
    {"label": "Data analysis", "courses": "CSCI567 CSCI573 DSCI553 ISE520 MATH467 MATH574".split()},
]
GAME_ELECTIVES = "CSCI520 CSCI522 CSCI526 CSCI538 CSCI567 CSCI590 CSCI591 CTIN503 CTIN510 CTIN534L CTIN544 CTIN593".split()
PROGRAMS = [
    {"id": "general", "name": "MS CS · General", "url": BASE+"computer-science-general/", "rules": {
        "total": 32, "effective_from": "2024-08", "core": ["CSCI570"],
        "elective_units": 28, "elective_mode": "cs500", "max600": 8,
        "note": "32-unit non-thesis summary for Fall 2024 onward. Earlier cohorts and the thesis option differ. Approved 400-level and non-CS electives require manual review."}},
    {"id": "ai", "name": "MS CS · Artificial Intelligence", "url": BASE+"artificial-intelligence/", "rules": {
        "total": 32, "effective_from": "2026-08", "core": ["CSCI561", "CSCI566", "CSCI567", "CSCI570"],
        "groups": AI_GROUPS, "group_count": 4, "group_diversity": 2, "elective_units": 14,
        "elective_mode": "groups", "max400": 4,
        "note": "Four electives must span at least two groups. If these leave fewer than 32 units, an adviser-approved additional course is needed. Pre-Fall 2026 rules differ; CSCI445L precedes CSCI545."}},
    {"id": "data-science", "name": "MS CS · Data Science", "url": BASE+"data-science/", "rules": {
        "total": 32, "effective_from": "2026-08", "core": ["CSCI561", "CSCI570", "CSCI585"],
        "groups": DS_GROUPS, "group_count": 3, "group_diversity": 2,
        "elective_units": 20, "elective_mode": "data", "max400": 4, "max_dsci": 3,
        "extra": "DSCI554 DSCI558 MATH458 MATH501 MATH502A MATH502B MATH505A MATH601".split(),
        "note": "Three group electives must include both groups; additional electives bring the total to 32. At most three DSCI courses and four 400-level units. Earlier catalogues need review."}},
    {"id": "game", "name": "MS CS · Game Development", "url": BASE+"game-development/", "rules": {
        "total": 32, "effective_from": "2026-08", "core": "CSCI570 CSCI561 CSCI580 CTIN532L CTIN541 CSCI529A CSCI529B".split(),
        "elective_units": 4, "elective_mode": "list", "extra": GAME_ELECTIVES,
        "note": "Core and emphasis courses total 28 units, plus four elective units. Special topics, directed research and historical catalogues need adviser review."}},
    {"id": "scientists-engineers", "name": "MS CS · Scientists and Engineers", "url": BASE+"scientists-and-engineers/", "rules": {
        "total": 33, "effective_from": "2025-08", "prep": ["CSCI455X"],
        "core": ["CSCI402", "CSCI570"], "one_of": ["EE450", "EE457"],
        "elective_units": 21, "elective_mode": "cs500", "max600_count": 1,
        "note": "37 units including four preparatory CSCI455x units; 33 count toward the degree. CSCI455x is required first semester. CSCI402 is recommended second or third semester after 455x. One doctoral course maximum; non-CS electives need approval."}},
]
