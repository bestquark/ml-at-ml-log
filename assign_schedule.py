import datetime
import csv
import random

names = [
    "Abdul", "Alastair", "Alessandro", "Andres", "Austin",
    "Changhyeok", "Cher-Tian", "Ella", "Gary", "Jackie", "Jorge",
    "Juan", "Luca", "Luis", "Mahdi", "Marko", "Marta", "Pan",
    "Samantha", "Sean", "Shi Xuan", "Yuchi (Allan)", "Yuma", "Zijian"
]

def get_next_n_wednesdays(n=16):
    """Return a list of the next n Wednesday dates (as strings)."""
    dates = []
    today = datetime.date.today()
    while today.weekday() != 2:  # move to next Wednesday
        today += datetime.timedelta(days=1)
    for _ in range(n):
        dates.append(today.strftime("%Y-%m-%d"))
        today += datetime.timedelta(days=7)
    return dates

def assign_roles(
    n_weeks=16,
    min_presenter_gap=4,
    presentation_weight=4,
    fixed_assignments=None
):
    """
    Create a schedule with:
      - 4-week gap for presenters (by default).
      - Single 'usage' metric for fairness:
          usage = (#presenter * presentation_weight) + (#journal * 1).
        The higher your total usage, the less likely you are picked again soon.
      - No same-day overlap: if you're presenting, you can't journal that day.
      - 'fixed_assignments' lets you hardcode presenters/journals for certain week indices.

    :param n_weeks: total weeks to schedule
    :param min_presenter_gap: how many weeks must pass before a person can present again
    :param presentation_weight: how many 'usage points' a single presentation is worth
    :param fixed_assignments: dict keyed by week index, e.g.:
        {
          0: {"presenters": ["Gary", "Cher-Tian"], "journals": ["Luis", "Marko"]},
          5: {"presenters": ["Jackie", "Marta"]}  # only presenters fixed for week 5
        }
    """
    if fixed_assignments is None:
        fixed_assignments = {}

    # usage_count[p] = {"presenter": #, "journal": #}
    usage_count = {name: {"presenter": 0, "journal": 0} for name in names}
    last_presented = {name: -999 for name in names}  # track last week index someone presented

    wednesdays = get_next_n_wednesdays(n_weeks)

    with open("schedule.csv", "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Date", "Presenter 1", "Presenter 2", "Journal 1", "Journal 2"])

        for week_index, date in enumerate(wednesdays):
            # Check if this week is pre-assigned
            if week_index in fixed_assignments:
                fa = fixed_assignments[week_index]
                presenters = fa.get("presenters", [])
                journals = fa.get("journals", [])

                # If presenters or journals are not explicitly given, pick them
                if not presenters:
                    presenters = pick_presenters(
                        usage_count, last_presented, week_index,
                        min_presenter_gap, presentation_weight, number=2
                    )
                if not journals:
                    journals = pick_journalers(
                        usage_count, exclude=set(presenters),
                        presentation_weight=presentation_weight, number=2
                    )

            else:
                # Normal assignment
                presenters = pick_presenters(
                    usage_count, last_presented, week_index,
                    min_presenter_gap, presentation_weight, number=2
                )
                journals = pick_journalers(
                    usage_count, exclude=set(presenters),
                    presentation_weight=presentation_weight, number=2
                )

            # Update usage counters
            for p in presenters:
                usage_count[p]["presenter"] += 1
                last_presented[p] = week_index
            for j in journals:
                usage_count[j]["journal"] += 1

            writer.writerow([date, presenters[0], presenters[1], journals[0], journals[1]])

    print("Schedule CSV generated: schedule.csv")

def pick_presenters(
    usage_count, last_presented, current_week,
    min_presenter_gap, presentation_weight,
    number=2
):
    """
    Pick 'number' presenters subject to:
      1. Not presenting within the last 'min_presenter_gap' weeks.
      2. Minimizing combined usage = (#presenter * presentation_weight) + (#journal).
      3. Random tie-break before sorting.
    """
    items = list(usage_count.items())
    random.shuffle(items)  # break alphabetical ties among same usage

    # Filter by gap first
    valid_candidates = []
    for person, roles in items:
        if current_week - last_presented[person] >= min_presenter_gap:
            valid_candidates.append((person, roles))

    # If we have fewer valid candidates than needed, we'll need to relax the gap
    if len(valid_candidates) < number:
        valid_candidates = items  # everyone is valid if we can't fill with min gap

    # Sort valid candidates by their combined usage
    # usage = #presenter * weight + #journal
    valid_candidates.sort(
        key=lambda x: x[1]["presenter"] * presentation_weight + x[1]["journal"]
    )

    chosen = []
    for person, _ in valid_candidates:
        chosen.append(person)
        if len(chosen) == number:
            break

    return chosen

def pick_journalers(
    usage_count, exclude,
    presentation_weight, number=2
):
    """
    Pick 'number' journalers subject to:
      1. Not being in `exclude` (same-day presenters).
      2. Minimizing combined usage = (#presenter * presentation_weight) + (#journal).
      3. Random tie-break before sorting.
    """
    items = list(usage_count.items())
    random.shuffle(items)  # break alphabetical ties

    # Filter out the excluded folks
    candidates = [(p, roles) for (p, roles) in items if p not in exclude]

    # Sort by same combined usage function
    candidates.sort(
        key=lambda x: x[1]["presenter"] * presentation_weight + x[1]["journal"]
    )

    chosen = []
    for person, _ in candidates:
        chosen.append(person)
        if len(chosen) == number:
            break

    return chosen

if __name__ == "__main__":
    # Example usage:
    fixed_assignments = {
        0: {"presenters": ["Gary", "Cher-Tian"], "journals": ["Luis", "Marko"]},
    }

    assign_roles(
        n_weeks=16,
        min_presenter_gap=6,
        presentation_weight=4,  # 1 presentation = 4 journals
        fixed_assignments=fixed_assignments
    )
