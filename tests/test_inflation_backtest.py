from app.scripts.inflation_backtest import run_inflation_backtest


def test_karma_enflasyon_tahmini_ham_modelden_daha_isabetli():
    # Uygulamanin karma tahmine gecmesinin gerekcesi; veri guncellendiginde bu test bozulursa
    # inflation_service.NAIVE_WEIGHT yeniden degerlendirilmelidir.
    frame = run_inflation_backtest()
    mae = {name: (frame[name] - frame["actual"]).abs().mean() for name in ["model", "naive", "blend"]}
    assert mae["blend"] < mae["model"]
