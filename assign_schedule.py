import datetime
import csv
import random

import gsheet_utils as gs

seed = 0
random.seed(seed)

names = gs.get_participants_list()

def get_next_n_wednesdays(n=16):
    """Return a list of the next n Wednesday dates (as strings)."""
    dates = []
    today = datetime.date.today()
    # Move to the next Wednesday
    while today.weekday() != 2:  
        today += datetime.timedelta(days=1)
    # Collect the next n Wednesdays
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
    Create a schedule with only presenters:
      - 4-week gap for presenters (by default).
      - Single usage metric for fairness:
          usage = (#presenter) * presentation_weight
      - 'fixed_assignments' lets you hardcode presenters for certain week indices.

    :param n_weeks: total weeks to schedule
    :param min_presenter_gap: how many weeks must pass before a person can present again
    :param presentation_weight: how many 'usage points' a single presentation is worth
    :param fixed_assignments: dict keyed by week index, e.g.:
        {
          0: {"presenters": ["Gary", "Cher-Tian"]},
          5: {"presenters": ["Jackie", "Marta"]}
        }
    """
    if fixed_assignments is None:
        fixed_assignments = {}

    # usage_count[p] = number of times someone has presented
    usage_count = {name: 0 for name in names}
    # track last week index someone presented
    last_presented = {name: -999 for name in names}

    wednesdays = get_next_n_wednesdays(n_weeks)

    with open("schedule.csv", "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Date", "Presenter 1", "Presenter 2"])

        for week_index, date in enumerate(wednesdays):
            # Check if this week is pre-assigned
            if week_index in fixed_assignments:
                fa = fixed_assignments[week_index]
                presenters = fa.get("presenters", [])
                # If presenters are not explicitly given, pick them
                if not presenters:
                    presenters = pick_presenters(
                        usage_count,
                        last_presented,
                        week_index,
                        min_presenter_gap,
                        presentation_weight,
                        number=2,
                    )
            else:
                # Normal assignment
                presenters = pick_presenters(
                    usage_count,
                    last_presented,
                    week_index,
                    min_presenter_gap,
                    presentation_weight,
                    number=2,
                )

            # Update usage counters
            for p in presenters:
                usage_count[p] += 1
                last_presented[p] = week_index

            # Write to CSV
            writer.writerow([date, presenters[0], presenters[1]])

    print("Schedule CSV generated: schedule.csv")

def pick_presenters(
    usage_count, last_presented, current_week,
    min_presenter_gap, presentation_weight,
    number=2
):
    """
    Pick 'number' presenters subject to:
      1. Not presenting within the last 'min_presenter_gap' weeks.
      2. Minimizing usage = (#presenter) * presentation_weight.
      3. Random tie-break before sorting.
    """
    items = list(usage_count.items())
    random.shuffle(items)  # break alphabetical ties among same usage

    # Filter by gap first
    valid_candidates = []
    for person, usage in items:
        if current_week - last_presented[person] >= min_presenter_gap:
            valid_candidates.append((person, usage))

    # If we have fewer valid candidates than needed, relax the gap
    if len(valid_candidates) < number:
        valid_candidates = items  # everyone is valid if we can't fill with min gap

    # Sort valid candidates by their usage: usage * presentation_weight
    valid_candidates.sort(key=lambda x: x[1] * presentation_weight)

    chosen = []
    for person, _ in valid_candidates:
        chosen.append(person)
        if len(chosen) == number:
            break

    return chosen

if __name__ == "__main__":
    # Example usage:
    fixed_assignments = {
        0: {"presenters": ["Cher-Tian", "Gary"]},
    }

    assign_roles(
        n_weeks=16,
        min_presenter_gap=6,
        presentation_weight=4,  # 1 presentation = 4 usage points
        fixed_assignments=fixed_assignments
    )
