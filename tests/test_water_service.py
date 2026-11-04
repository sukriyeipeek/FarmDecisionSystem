import pytest

from app.services.product_catalog import URUNLER
from app.services.water_service import estimate_water, water_catalog, WATER_PROFILES


def test_catalog_covers_all_products_and_exposes_uncertainty():
    assert set(WATER_PROFILES) == set(URUNLER)
    for item in water_catalog():
        assert 0 < item['water_low_m3_per_decare'] <= item['water_m3_per_decare'] <= item['water_high_m3_per_decare']
        assert item['source'].startswith('https://')
        assert item['assumptions']


def test_volume_conversion_and_method_efficiency():
    drip = estimate_water('DOMATES SALKIM', 'Spring', 'damla')
    surface = estimate_water('DOMATES SALKIM', 'Spring', 'salma')
    assert drip['water_m3_per_decare'] == pytest.approx(600 / .9)
    assert surface['water_m3_per_decare'] == pytest.approx(1000)
    assert surface['water_m3_per_decare'] > drip['water_m3_per_decare']


@pytest.mark.parametrize('product,season,method', [('unknown', 'Spring', 'damla'), ('MARUL','foo','damla'), ('MARUL','Winter','foo')])
def test_unknown_inputs_fail_explicitly(product, season, method):
    with pytest.raises(ValueError):
        estimate_water(product, season, method)
