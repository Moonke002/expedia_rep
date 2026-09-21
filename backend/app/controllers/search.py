"""Search controller coordinates history and price calculation."""

from .database import DatabaseController


class SearchController:
    def __init__(self, database: DatabaseController) -> None:
        self.database = database

    def search(self, hotel_name: str, user_id: str | None) -> dict:
        query = hotel_name.strip()
        count = self.database.record_search(user_id, query) if user_id else 0
        return {
            "query": query,
            "matching_searches_today": count,
            "results": self.database.search_stays(query, count),
        }
