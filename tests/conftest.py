import polars as pl
import pytest
from pyflow_engine import build_default_registry


@pytest.fixture(scope="session")
def registry():
    return build_default_registry()


@pytest.fixture
def customers() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "id": [1, 2, 3, 4, 5, 6, 7, 8],
            "name": ["Acme", "Globex", "Initech", "Umbrella", "Hooli", "Stark", "Wayne", "Wonka"],
            "status": [
                "active", "inactive", "active", "active",
                "inactive", "active", "active", "inactive",
            ],
            "region": ["West", "East", "East", "West", "West", "East", "West", "East"],
            "spend": [1200.5, 300.0, 875.25, 5400.0, 50.0, 9800.75, 4200.0, 150.25],
        }
    )


@pytest.fixture
def regions() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "region": ["West", "East", "North"],
            "manager": ["Alice", "Bob", "Carol"],
            "quota": [10000, 8000, 5000],
        }
    )
