import datetime

def get_next_wednesday(after_date):
    # Wednesday is weekday() == 2
    days_ahead = 2 - after_date.weekday()
    if days_ahead <= 0:  # Target day already passed this week
        days_ahead += 7
    return after_date + datetime.timedelta(days=days_ahead)

def highlight_empty(val):
    return 'background-color: yellow' if val == "EMPTY" else ''

def highlight_random(val):
    # make light blue if val starts with [R]
    return 'background-color: darkblue' if val.startswith("[R]") else ''