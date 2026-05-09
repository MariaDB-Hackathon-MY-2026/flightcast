"""
Shared fixtures for all test levels.
Integration tests require MARIADB_TEST_URL env var and a live DB.
"""
import os
import pytest
import pandas as pd
import numpy as np


@pytest.fixture(scope="session")
def sample_routes_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "route_id": [1, 2, 3],
            "src_airport": ["KUL", "SIN", "BKK"],
            "dst_airport": ["SIN", "BKK", "HKG"],
            "hub_degree_src": [300, 400, 250],
            "hub_degree_dst": [400, 250, 350],
            "hemisphere": ["N", "N", "N"],
        }
    )


@pytest.fixture(scope="session")
def rng() -> np.random.Generator:
    return np.random.default_rng(42)
