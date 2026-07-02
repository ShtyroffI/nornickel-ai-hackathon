from app.services.analytics.service import AnalyticsService
from app.services.search.service import SearchFilters, SearchService


def test_search_returns_dict():
    res = SearchService().search("никель", SearchFilters(geography="Россия"))
    assert res["query"] == "никель"
    assert res["filters"]["geography"] == "Россия"


def test_analytics_review_and_gaps():
    a = AnalyticsService()
    review = a.generate_review("тема", ["method"])
    assert review["topic"] == "тема"
    gaps = a.find_gaps(["никель"], ["выщелачивание"], ["холодный климат"])
    assert len(gaps) == 1
