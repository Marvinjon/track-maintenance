from app.services.traccar import hours_to_ms, km_to_meters, meters_to_km, ms_to_hours


def test_meters_to_km():
    assert meters_to_km(123_456_789) == 123456.8
    assert meters_to_km(0) == 0.0


def test_ms_to_hours():
    assert ms_to_hours(3_600_000) == 1.0
    assert ms_to_hours(5_400_000) == 1.5


def test_roundtrip():
    assert km_to_meters(meters_to_km(15_000_000)) == 15_000_000
    assert hours_to_ms(ms_to_hours(7_200_000)) == 7_200_000
