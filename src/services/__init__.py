"""Business logic services used by handlers.

Services are imported lazily by handlers to avoid import-time issues with
dependencies like SQLAlchemy that aren't in the Lambda Powertools layer.
"""

# Do NOT import services here - use lazy loading in handlers instead