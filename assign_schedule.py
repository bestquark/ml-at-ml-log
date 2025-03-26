import datetime
import csv
import random

import google_utils as gu

seed = 0
random.seed(seed)


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


# def assign_roles(
#     n_weeks=16, min_presenter_gap=4, presentation_weight=4, fixed_assignments=None
# ):
#     """
#     Create a schedule with only presenters:
#       - 4-week gap for presenters (by default).
#       - Single usage metric for fairness:
#           usage = (#presenter) * presentation_weight
#       - 'fixed_assignments' lets you hardcode presenters for certain week indices.

#     :param n_weeks: total weeks to schedule
#     :param min_presenter_gap: how many weeks must pass before a person can present again
#     :param presentation_weight: how many 'usage points' a single presentation is worth
#     :param fixed_assignments: dict keyed by week index, e.g.:
#         {
#           0: {"presenters": ["Gary", "Cher-Tian"]},
#           5: {"presenters": ["Jackie", "Marta"]}
#         }
#     """
#     if fixed_assignments is None:
#         fixed_assignments = {}

#     # usage_count[p] = number of times someone has presented
#     usage_count = {name: 0 for name in names}
#     # track last week index someone presented
#     last_presented = {name: -999 for name in names}

#     wednesdays = get_next_n_wednesdays(n_weeks)

#     with open("schedule.csv", "w", newline="", encoding="utf-8") as csvfile:
#         writer = csv.writer(csvfile)
#         writer.writerow(["Date", "Presenter 1", "Presenter 2"])

#         for week_index, date in enumerate(wednesdays):
#             # Check if this week is pre-assigned
#             if week_index in fixed_assignments:
#                 fa = fixed_assignments[week_index]
#                 presenters = fa.get("presenters", [])
#                 # If presenters are not explicitly given, pick them
#                 if not presenters:
#                     presenters = pick_presenters(
#                         usage_count,
#                         last_presented,
#                         week_index,
#                         min_presenter_gap,
#                         presentation_weight,
#                         number=2,
#                     )
#             else:
#                 # Normal assignment
#                 presenters = pick_presenters(
#                     usage_count,
#                     last_presented,
#                     week_index,
#                     min_presenter_gap,
#                     presentation_weight,
#                     number=2,
#                 )

#             # Update usage counters
#             for p in presenters:
#                 if p not in names:
#                     continue
#                 usage_count[p] += 1
#                 last_presented[p] = week_index

#             # Write to CSV
#             if week_index not in fixed_assignments:
#                 writer.writerow([date, "[R] " + presenters[0], "[R] " + presenters[1]])
#             else:
#                 writer.writerow([date, presenters[0], presenters[1]])

#     print("Schedule CSV generated: schedule.csv")


# def pick_presenters(
#     usage_count,
#     last_presented,
#     current_week,
#     min_presenter_gap,
#     presentation_weight,
#     number=2,
# ):
#     """
#     Pick 'number' presenters subject to:
#       1. Not presenting within the last 'min_presenter_gap' weeks.
#       2. Minimizing usage = (#presenter) * presentation_weight.
#       3. Random tie-break before sorting.
#     """
#     items = list(usage_count.items())
#     random.shuffle(items)  # break alphabetical ties among same usage

#     # Filter by gap first
#     valid_candidates = []
#     for person, usage in items:
#         if current_week - last_presented[person] >= min_presenter_gap:
#             valid_candidates.append((person, usage))

#     # If we have fewer valid candidates than needed, relax the gap
#     if len(valid_candidates) < number:
#         valid_candidates = items  # everyone is valid if we can't fill with min gap

#     # Sort valid candidates by their usage: usage * presentation_weight
#     valid_candidates.sort(key=lambda x: x[1] * presentation_weight)

#     chosen = []
#     for person, _ in valid_candidates:
#         chosen.append(person)
#         if len(chosen) == number:
#             break

#     return chosen


def assign_roles(
    names,
    n_weeks=16,
    min_presenter_gap=4,
    presentation_weight=4,
    fixed_assignments=None,
):
    """
    Create a schedule with presenters:
      - Ensures a minimum gap between presentations.
      - Uses a usage metric for fairness:
          usage = (#presentations) * presentation_weight
      - 'fixed_assignments' allows hardcoding presenters for certain week indices.

    :param names: List of presenter names.
    :param n_weeks: Total weeks to schedule.
    :param min_presenter_gap: Minimum weeks between presentations.
    :param presentation_weight: Weight assigned to each presentation.
    :param fixed_assignments: Dict keyed by week index with fixed presenters.
    """
    if fixed_assignments is None:
        fixed_assignments = {}

    # Initialize usage metrics
    usage_count = {name: 0 for name in names}
    last_presented = {name: -min_presenter_gap for name in names}
    future_assignments = {week: [] for week in range(n_weeks)}

    with open("schedule.csv", "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Week", "Presenter 1", "Presenter 2"])

        for week_index in range(n_weeks):
            presenters = []

            # Check for fixed assignments
            if week_index in fixed_assignments:
                # Include only valid presenters from fixed assignments
                presenters = [
                    p for p in fixed_assignments[week_index]["presenters"] if p in names
                ]

            # If additional presenters are needed, select them
            if len(presenters) < 2:
                additional_presenters = pick_presenters(
                    names,
                    usage_count,
                    last_presented,
                    future_assignments,
                    week_index,
                    min_presenter_gap,
                    presentation_weight,
                    n_weeks,
                    number=2 - len(presenters),
                )
                presenters.extend(additional_presenters)

            # Update usage metrics
            for presenter in presenters:
                usage_count[presenter] += 1
                last_presented[presenter] = week_index
                # Record future assignments
                for future_week in range(
                    week_index + 1, min(week_index + min_presenter_gap, n_weeks)
                ):
                    future_assignments[future_week].append(presenter)

            # Write to CSV with [P] prefix for algorithm-assigned presenters
            writer.writerow(
                [
                    week_index + 1,
                    f"[P] {presenters[0]}" if presenters[0] not in fixed_assignments.get(week_index, {}).get("presenters", []) else presenters[0],
                    f"[P] {presenters[1]}" if presenters[1] not in fixed_assignments.get(week_index, {}).get("presenters", []) else presenters[1],
                ]
            )

    print("Schedule CSV generated: schedule.csv")


def pick_presenters(
    names,
    usage_count,
    last_presented,
    future_assignments,
    current_week,
    min_presenter_gap,
    presentation_weight,
    n_weeks,
    number=2,
):
    """
    Select presenters ensuring:
      1. They haven't presented within the last 'min_presenter_gap' weeks.
      2. They aren't scheduled to present in the upcoming 'min_presenter_gap' weeks.
      3. Fair distribution based on usage metrics.
    """
    candidates = []

    for name in names:
        if (
            current_week - last_presented[name] >= min_presenter_gap
            and all(
                name not in future_assignments[week]
                for week in range(
                    current_week + 1, min(current_week + min_presenter_gap, n_weeks)
                )
            )
        ):
            candidates.append((name, usage_count[name]))

    # Sort candidates by usage and randomize to break ties
    random.shuffle(candidates)
    candidates.sort(key=lambda x: x[1] * presentation_weight)

    selected_presenters = [candidate[0] for candidate in candidates[:number]]

    return selected_presenters

def fill_df_random(weeks_in_adv=16):

    names_dict = gu.get_participants_list()
    names = [n["Name"] for n in names_dict]

    schedule = gu.get_schedule_df()
    fixed_assignments = {}

    for i, row in schedule.iterrows():
        p1 = row["Presenter 1"] if row["Presenter 1"] != "EMPTY" else None
        p2 = row["Presenter 2"] if row["Presenter 2"] != "EMPTY" else None
        presenters = [p for p in [p1, p2] if p]
        # remove repeated presenters
        # presenters = list(set(presenters))
        if len(presenters) == 0:
            continue
        fixed_assignments[i] = {"presenters": presenters}
    print(fixed_assignments)
    
    min_week_filled = len(fixed_assignments)

    assign_roles(
        names,
        n_weeks=min_week_filled + weeks_in_adv,
        min_presenter_gap=7,
        presentation_weight=4,  # 1 presentation = 4 usage points
        fixed_assignments=fixed_assignments,
    )

if __name__ == "__main__":
    # Example usage:
    # fixed_assignments = {
    #     0: {"presenters": ["Cher-Tian", "Gary"]},
    #     1: {"presenters": ["Alessandro", "EMPTY"]},
    #     2: {"presenters": ["Maria Luiza", "Samantha"]},
    #     3: {"presenters": ["Marko", "Marta"]},
    #     4: {"presenters": ["Pan", "Zijian"]},
    #     5: {"presenters": ["Yuchi (Allan)", "Kourosh"]},
    # }

    # get fixed assignments from google sheet


    names_dict = gu.get_participants_list()
    names = [n["Name"] for n in names_dict]

    schedule = gu.get_schedule_df()

    fixed_assignments = {}

    for i, row in schedule.iterrows():
        p1 = row["Presenter 1"] if row["Presenter 1"] != "EMPTY" else None
        p2 = row["Presenter 2"] if row["Presenter 2"] != "EMPTY" else None
        presenters = [p for p in [p1, p2] if p]
        # remove repeated presenters
        # presenters = list(set(presenters))
        if len(presenters) == 0:
            continue
        fixed_assignments[i] = {"presenters": presenters}
    print(fixed_assignments)

    assign_roles(
        names,
        n_weeks=32,
        min_presenter_gap=7,
        presentation_weight=4,  # 1 presentation = 4 usage points
        fixed_assignments=fixed_assignments,
    )
