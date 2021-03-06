"""
Tests for zipline.data.ffc.frame.DataFrameFFCLoader
"""
from unittest import TestCase

from mock import patch
from numpy import arange
from numpy.testing import assert_array_equal
from pandas import (
    DataFrame,
    DatetimeIndex,
    Int64Index,
)

from zipline.lib.adjustment import (
    Float64Add,
    Float64Multiply,
    Float64Overwrite,
)
from zipline.data.equities import USEquityPricing
from zipline.data.ffc.frame import (
    ADD,
    DataFrameFFCLoader,
    MULTIPLY,
    OVERWRITE,
)
from zipline.utils.tradingcalendar import trading_day


class DataFrameFFCLoaderTestCase(TestCase):

    def setUp(self):
        self.nsids = 5
        self.ndates = 20

        self.sids = Int64Index(range(self.nsids))
        self.dates = DatetimeIndex(
            start='2014-01-02',
            freq=trading_day,
            periods=self.ndates,
        )

        self.mask = DataFrame(
            True,
            index=self.dates,
            columns=self.sids,
            dtype=bool,
        )

    def tearDown(self):
        pass

    def test_bad_input(self):
        data = arange(100).reshape(self.ndates, self.nsids)
        baseline = DataFrame(data, index=self.dates, columns=self.sids)
        loader = DataFrameFFCLoader(
            USEquityPricing.close,
            baseline,
        )

        with self.assertRaises(ValueError):
            # Wrong column.
            loader.load_adjusted_array([USEquityPricing.open], self.mask)

        with self.assertRaises(ValueError):
            # Too many columns.
            loader.load_adjusted_array(
                [USEquityPricing.open, USEquityPricing.close],
                self.mask
            )

    def test_baseline(self):
        data = arange(100).reshape(self.ndates, self.nsids)
        baseline = DataFrame(data, index=self.dates, columns=self.sids)
        loader = DataFrameFFCLoader(
            USEquityPricing.close,
            baseline,
        )

        dates_slice = slice(None, 10, None)
        sids_slice = slice(1, 3, None)
        adj_array = loader.load_adjusted_array(
            [USEquityPricing.close],
            self.mask.iloc[dates_slice, sids_slice]
        )

        for idx, window in enumerate(adj_array.traverse(window_length=3)):
            expected = baseline.values[dates_slice, sids_slice][idx:idx + 3]
            assert_array_equal(window, expected)

    def test_adjustments(self):
        data = arange(100).reshape(self.ndates, self.nsids)
        baseline = DataFrame(data, index=self.dates, columns=self.sids)

        # Use the dates from index 10 on and sids 1-3.
        dates_slice = slice(10, None, None)
        sids_slice = slice(1, 4, None)

        # Adjustments that should actually affect the output.
        relevant_adjustments = [
            {
                'sid': 1,
                'start_date': None,
                'end_date': self.dates[15],
                'apply_date': self.dates[16],
                'value': 0.5,
                'kind': MULTIPLY,
            },
            {
                'sid': 2,
                'start_date': self.dates[5],
                'end_date': self.dates[15],
                'apply_date': self.dates[16],
                'value': 1.0,
                'kind': ADD,
            },
            {
                'sid': 2,
                'start_date': self.dates[15],
                'end_date': self.dates[16],
                'apply_date': self.dates[17],
                'value': 1.0,
                'kind': ADD,
            },
            {
                'sid': 3,
                'start_date': self.dates[16],
                'end_date': self.dates[17],
                'apply_date': self.dates[18],
                'value': 99.0,
                'kind': OVERWRITE,
            },
        ]

        # These adjustments shouldn't affect the output.
        irrelevant_adjustments = [
            {  # Sid Not Requested
                'sid': 0,
                'start_date': self.dates[16],
                'end_date': self.dates[17],
                'apply_date': self.dates[18],
                'value': -9999.0,
                'kind': OVERWRITE,
            },
            {  # Sid Unknown
                'sid': 9999,
                'start_date': self.dates[16],
                'end_date': self.dates[17],
                'apply_date': self.dates[18],
                'value': -9999.0,
                'kind': OVERWRITE,
            },
            {  # Date Not Requested
                'sid': 2,
                'start_date': self.dates[1],
                'end_date': self.dates[2],
                'apply_date': self.dates[3],
                'value': -9999.0,
                'kind': OVERWRITE,
            },
            {  # Date Before Known Data
                'sid': 2,
                'start_date': self.dates[0] - (2 * trading_day),
                'end_date': self.dates[0] - trading_day,
                'apply_date': self.dates[0] - trading_day,
                'value': -9999.0,
                'kind': OVERWRITE,
            },
            {  # Date After Known Data
                'sid': 2,
                'start_date': self.dates[-1] + trading_day,
                'end_date': self.dates[-1] + (2 * trading_day),
                'apply_date': self.dates[-1] + (3 * trading_day),
                'value': -9999.0,
                'kind': OVERWRITE,
            },
        ]

        adjustments = DataFrame(relevant_adjustments + irrelevant_adjustments)
        loader = DataFrameFFCLoader(
            USEquityPricing.close,
            baseline,
            adjustments=adjustments,
        )

        expected_baseline = baseline.iloc[dates_slice, sids_slice]

        formatted_adjustments = loader.format_adjustments(
            self.dates[dates_slice],
            self.sids[sids_slice],
        )
        expected_formatted_adjustments = {
            6: [
                Float64Multiply(first_row=0, last_row=5, col=0, value=0.5),
                Float64Add(first_row=0, last_row=5, col=1, value=1.0),
            ],
            7: [
                Float64Add(first_row=5, last_row=6, col=1, value=1.0),
            ],
            8: [
                Float64Overwrite(first_row=6, last_row=7, col=2, value=99.0)
            ],
        }
        self.assertEqual(formatted_adjustments, expected_formatted_adjustments)

        mask = self.mask.iloc[dates_slice, sids_slice]
        with patch('zipline.data.ffc.frame.adjusted_array') as m:
            loader.load_adjusted_array(
                columns=[USEquityPricing.close],
                mask=mask,
            )

        self.assertEqual(m.call_count, 1)

        args, kwargs = m.call_args
        assert_array_equal(kwargs['data'], expected_baseline.values)
        assert_array_equal(kwargs['mask'], mask.values)
        self.assertEqual(kwargs['adjustments'], expected_formatted_adjustments)
