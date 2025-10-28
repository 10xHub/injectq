from injectq import ScopeType
from injectq.core.container import InjectQ


from injectq import InjectQ


class Database:
    def __init__(self, db_url: str):
        self.db_url = db_url


container = InjectQ()
container.bind("db_url", "postgresql://localhost/mydb")


# Factory with DI - parameter is injected
def create_database(db_url: str):
    return Database(db_url)


container.bind_factory(Database, create_database)

# Get instance - factory called automatically with injected deps
db = container[Database]
print(db.db_url)  # Output: postgresql://localhost/mydb
# or
db = container.get(Database)
print(db.db_url)  # Output: postgresql://localhost/mydb
