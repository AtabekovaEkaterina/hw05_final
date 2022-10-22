import datetime as dt


def year(request):
    now_year = dt.datetime.now().year
    return {
        'year': now_year
    }
