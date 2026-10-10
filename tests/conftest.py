import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import holdings_tracker_desktop.models  # noqa: F401  (registers all models)
from holdings_tracker_desktop.models import Asset, AssetType, Broker, Country, Currency
from holdings_tracker_desktop.models.base import Base


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def refs(db):
    """Minimal reference data: one country, currency, asset type and broker."""
    country = Country(name="Brasil")
    currency = Currency(name="Real", code="BRL", symbol="R$")
    db.add_all([country, currency])
    db.flush()

    asset_type = AssetType(name="Ação", country_id=country.id)
    broker = Broker(name="Corretora", country_id=country.id)
    db.add_all([asset_type, broker])
    db.commit()

    return {"asset_type": asset_type, "currency": currency, "broker": broker}


@pytest.fixture
def make_asset(db, refs):
    def _make(ticker: str) -> Asset:
        asset = Asset(
            ticker=ticker,
            type_id=refs["asset_type"].id,
            currency_id=refs["currency"].id,
        )
        db.add(asset)
        db.commit()
        return asset

    return _make
