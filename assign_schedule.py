import datetime
import random
import pandas as pd

import google_utils as gu

seed = 0
random.seed(seed)

def get_next_n_wednesdays(start_date, n=16):
    """Return a list of the next n Wednesday dates starting from start_date."""
    dates = []
    current_date = start_date
    # Move to the next Wednesday if not already Wednesday
    while current_date.weekday() != 2:
        current_date += datetime.timedelta(days=1)
    # Collect the next n Wednesdays
    for _ in range(n):
        dates.append(current_date.strftime("%Y-%m-%d"))
        current_date += datetime.timedelta(days=7)
    return dates

def assign_roles(
    schedule_df,
    names,
    min_presenter_gap=4,
    presentation_weight=4,
):
    usage_count = {name: 0 for name in names}
    last_presented = {name: -min_presenter_gap for name in names}
    n_weeks = len(schedule_df)
    future_assignments = {week: [] for week in range(n_weeks)}

    schedule_df['Date'] = pd.to_datetime(schedule_df['Date'])
    
    # Calculate cutoff date: 5 months ago from today
    today = datetime.date.today()
    five_months_ago = today - datetime.timedelta(days=150)  # ~5 months (150 days)

    # First pass: Prepopulate future assignments with existing presenters
    for week_index, row in schedule_df.iterrows():
        presentation_date = row['Date'].date()
        presenters = [row['Presenter 1'], row['Presenter 2']]
        for presenter in presenters:
            presenter_clean = presenter.replace("[P] ", "")
            if presenter_clean != 'EMPTY':
                # Update future assignments to avoid collisions
                for future_week in range(
                    week_index + 1, min(week_index + min_presenter_gap, n_weeks)
                ):
                    future_assignments[future_week].append(presenter_clean)

    # Second pass: Fill empty slots considering future assignments
    for week_index, row in schedule_df.iterrows():
        presentation_date = row['Date'].date()
        presenters = [row['Presenter 1'], row['Presenter 2']]

        for i in range(2):
            if presenters[i] == 'EMPTY':
                additional_presenter = pick_presenters(
                    names,
                    usage_count,
                    last_presented,
                    future_assignments,
                    week_index,
                    min_presenter_gap,
                    presentation_weight,
                    n_weeks,
                    number=1,
                )[0]
                presenters[i] = f"[P] {additional_presenter}"

                # Update usage metrics only if within date range
                if presentation_date >= five_months_ago:
                    usage_count[additional_presenter] += 1
                last_presented[additional_presenter] = week_index

                # Update future assignments for the newly picked presenter
                for future_week in range(
                    week_index + 1, min(week_index + min_presenter_gap, n_weeks)
                ):
                    future_assignments[future_week].append(additional_presenter)
            else:
                presenter_clean = presenters[i].replace("[P] ", "")
                if presenter_clean in names:
                    # Update usage metrics only if within date range
                    if presentation_date >= five_months_ago:
                        usage_count[presenter_clean] += 1
                    last_presented[presenter_clean] = week_index

        # Update the DataFrame
        schedule_df.at[week_index, 'Presenter 1'] = presenters[0]
        schedule_df.at[week_index, 'Presenter 2'] = presenters[1]

    return schedule_df

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
    candidates = []

    for name in names:
        # Check both recent and upcoming presentations explicitly
        recently_presented = current_week - last_presented[name] < min_presenter_gap
        upcoming_presentation = any(
            name in future_assignments[week]
            for week in range(current_week + 1, min(current_week + min_presenter_gap, n_weeks))
        )

        if not recently_presented and not upcoming_presentation:
            candidates.append((name, usage_count[name]))

    if len(candidates) < number:
        # Fallback if needed (try to fill anyway without future check)
        candidates = [
            (name, usage_count[name])
            for name in names
            if current_week - last_presented[name] >= min_presenter_gap
        ]

    # Shuffle to break ties randomly, then sort
    random.shuffle(candidates)
    candidates.sort(key=lambda x: x[1] * presentation_weight)

    selected_presenters = [candidate[0] for candidate in candidates[:number]]

    return selected_presenters

def fill_empty_slots(seed=None):
    if seed is not None:
        random.seed(seed)

    # Retrieve participants and schedule from Google Sheets
    names_dict = gu.get_participants_list()
    names = [n["Name"] for n in names_dict]

    schedule_df = gu.get_schedule_df()

    # Fill empty slots in the schedule
    updated_schedule_df = assign_roles(
        schedule_df,
        names,
        min_presenter_gap=7,
        presentation_weight=1,  # 1 presentation = 4 usage points
    )

    return updated_schedule_df

if __name__ == "__main__":
    seed = 0
    updated_df = fill_empty_slots(seed=seed)
    print(updated_df)