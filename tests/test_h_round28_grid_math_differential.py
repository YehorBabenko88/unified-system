"""H R28 exact-source differential acceptance for Grid PR303 / Math PR167 / Terminan PR129.

Only pinned original functions are imported from a separate verifier-supplied SDK
directory; this test is inert. It is NOT an installed wheel, source-authenticity,
provider, native PostgreSQL or protected Root acceptance.
"""
from decimal import Decimal
import unittest
from types import SimpleNamespace

# In hosted source validation, isolate the three exact pinned repositories as
# independent source roots, then import these original symbols. Never create a
# second numerical kernel, provider or writer.
from market_math import aggregate_closed_minute_ohlcv, exact_sum
from market_data_v2.qualified_rollup import project_qualified_rollup
from market_data.provenance import digest


def _record(index, *, start, identity="H-R28", epoch="a61af02c-1358-4a69-90d5-462b2fa9dc4e",
            revision="a"*40, buy=1.0, sell=0.5):
    # Source input is an explicit synthetic verified-structure fixture, never a
    # fake provider attestation or a real Grid qualified snapshot.
    candle = {"open":100.0 + index, "high":102.0 + index,
              "low":99.0 + index, "close":101.0 + index,
              "buy_volume":buy, "sell_volume":sell, "delta":buy-sell,
              "trade_count":2, "poc_price":100.0+index}
    row = {
      "api_version":{"major":1,"minor":1}, "producer":"market_data",
      "source":{"identity":identity,"epoch":epoch,"source_revision":revision,
                "market_type":"linear","representation":"live_trade_aggregate"},
      "symbol":"BTCUSDT", "timeframe":"1m", "start_ms":start+index*60000,
      "end_ms":start+(index+1)*60000-1,
      "source_event_start_ms":start+index*60000+100,
      "source_event_end_ms":start+(index+1)*60000-100,
      "ingestion_ms":start+(index+1)*60000,
      "representation":"historical_aggregate", "execution_authority":False,
      "quality_status":"GOOD", "quality_reasons":[],
      "coverage":{"expected_minutes":1,"observed_minutes":1,
                  "missing_minutes":0,"exchange_completeness_attested":False},
      "source_identity_verified":True,"status":"PARTIAL",
      "reason":"EXCHANGE_COMPLETENESS_UNATTESTED",
      "candle":candle, "levels":[]
    }
    return dict(row,dataset_fingerprint=digest(row))


def _parent(records, status="PARTIAL"):
    data={
      "schema":"market_data.qualified-read-envelope.v1",
      "timeframe":"1m","producer":"market_data","record_integrity":"VERIFIED",
      "status":status,"reason":"EXCHANGE_COMPLETENESS_UNATTESTED",
      "source_authenticity":"NOT_INDEPENDENTLY_ATTESTED",
      "exchange_completeness":"NOT_ATTESTED",
      "storage_immutability":"NOT_ATTESTED","execution_authority":False,
      "trading_authorized":False,"paper_admitted":False,"read_only":True,
      "immutable":False, "rows":records,"symbol":"BTCUSDT",
      "source_revision":"a"*40,
      "producer_epoch":"a61af02c-1358-4a69-90d5-462b2fa9dc4e",
      "coverage":{"expected_minutes":len(records),"observed_minutes":len(records),
                  "missing_minutes":0}
    }
    return dict(data,dataset_fingerprint=digest(records))


class HGridMathDifferentialTests(unittest.TestCase):
    def test_grid_rollup_numerical_parity_with_canonical_math(self):
        for width,timeframe in ((5,"5m"),(15,"15m")):
            for buy,sell in ((1.0,0.5),(0.1,0.3),(0.0,0.0)):
                with self.subTest(timeframe=timeframe,buy=buy,sell=sell):
                    records=[_record(i,start=1800000000000//(width*60000)*(width*60000),
                                     buy=buy,sell=sell) for i in range(width)]
                    parent=_parent(records)
                    now=records[-1]["end_ms"]+1
                    output=project_qualified_rollup(parent,timeframe=timeframe,
                                                    limit=1,now_ms=now)
                    self.assertEqual(output["status"],"PARTIAL")
                    row=output["rows"][0]
                    source=[tuple(Decimal(str(r["candle"][key])) for key in
                            ("open","high","low","close","buy_volume","sell_volume"))
                            for r in records]
                    opened, high, low, closed, volume=aggregate_closed_minute_ohlcv(source)
                    self.assertEqual(row["open"],float(opened))
                    self.assertEqual(row["high"],float(high))
                    self.assertEqual(row["low"],float(low))
                    self.assertEqual(row["close"],float(closed))
                    self.assertEqual(row["buy_volume"]+row["sell_volume"],float(volume))
                    self.assertEqual(row["delta"],float(exact_sum(
                         (Decimal(str(row["buy_volume"])),
                          Decimal(str(row["sell_volume"])).copy_negate()))))
                    self.assertFalse(output["paper_admitted"])
                    self.assertFalse(output["execution_authority"])
                    self.assertFalse(output["trading_authorized"])
                    self.assertEqual(output["exchange_completeness"],"NOT_ATTESTED")

    def test_unverified_or_mixed_rows_denied_before_math(self):
        from market_data_v2.qualified_read_contract import ProvenanceReadError
        width=5
        start=(1800000000000//300000)*300000
        rows=[_record(i,start=start) for i in range(width)]
        for mutation in ("gap","mixed_revision","false_ready","nonclosed"):
            source=list(rows)
            parent=_parent(source)
            now=source[-1]["end_ms"]+1
            if mutation=="gap":
                source.pop(2)
            elif mutation=="mixed_revision":
                source[2]=_record(2,start=start,revision="b"*40)
            elif mutation=="false_ready":
                parent["status"]="READY"
            elif mutation=="nonclosed":
                now=source[-1]["end_ms"]
            with self.subTest(mutation=mutation), self.assertRaises(ProvenanceReadError):
                project_qualified_rollup(parent,timeframe="5m",limit=1,now_ms=now)

    def test_unsupported_timeframe_and_authority_refuse(self):
        from market_data_v2.qualified_read_contract import ProvenanceReadError
        start=(1800000000000//300000)*300000
        records=[_record(i,start=start) for i in range(5)]
        parent=_parent(records)
        now=records[-1]["end_ms"]+1
        with self.assertRaises(ProvenanceReadError):
            project_qualified_rollup(parent,timeframe="1h",limit=1,now_ms=now)
        parent["paper_admitted"]=True
        with self.assertRaises(ProvenanceReadError):
            project_qualified_rollup(parent,timeframe="5m",limit=1,now_ms=now)


if __name__ == "__main__":
    unittest.main()
