from app.geo import haversine_km

def test_same_point_zero():
    assert haversine_km(31.25,34.79,31.25,34.79) == 0

def test_reasonable_distance():
    d=haversine_km(31.25,34.79,31.30,34.79)
    assert 5 < d < 6
