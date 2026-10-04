import unittest
from datetime import date

from recon.kpi import periods
from recon.kpi.periods import Period, Window

D = date.fromisoformat
AUG = periods.parse("month", "2026-08")
SEP = periods.parse("month", "2026-09")
OCT = periods.parse("month", "2026-10")
W40 = periods.parse("week", "2026-W40")  # Monday Sep 28 to Sunday Oct 4


class Ids(unittest.TestCase):
    def test_day_week_month(self):
        day, monday, sunday = D("2026-10-02"), D("2026-09-14"), D("2026-09-20")
        self.assertEqual(periods.parse("day", "2026-10-02"), Period("day", "2026-10-02", day, day))
        self.assertEqual(periods.parse("week", "2026-W38"), Period("week", "2026-W38", monday, sunday))
        self.assertEqual(SEP, Period("month", "2026-09", D("2026-09-01"), D("2026-09-30")))

    def test_containing(self):
        self.assertEqual(periods.containing("week", D("2026-10-04")), W40)  # a Sunday closes its week
        self.assertEqual(periods.containing("week", D("2026-10-05")).id, "2026-W41")
        self.assertEqual(periods.containing("month", D("2026-02-10")).end, D("2026-02-28"))
        self.assertEqual(periods.containing("day", D("2026-10-02")).id, "2026-10-02")

    def test_a_week_belongs_to_its_iso_year(self):
        self.assertEqual(periods.containing("week", D("2025-12-31")).id, "2026-W01")

    def test_bad_ids_are_refused(self):
        bad = (("day", "2026-10"), ("day", "20261002"), ("day", "2026-02-30"), ("week", "2026-38"),
               ("week", "2026-W54"), ("month", "2026-13"), ("month", "2026-9"), ("year", "2026"))
        for kind, text in bad:
            with self.subTest(kind=kind, text=text), self.assertRaises(ValueError):
                periods.parse(kind, text)

    def test_previous(self):
        self.assertEqual(periods.previous(SEP), AUG)
        self.assertEqual(periods.previous(W40).id, "2026-W39")
        self.assertEqual(periods.previous(periods.parse("day", "2026-10-01")).id, "2026-09-30")


class Windows(unittest.TestCase):
    def test_a_finished_period_is_reported_whole(self):
        win = periods.window(SEP, latest_stored=D("2026-10-04"))
        self.assertEqual((win.through, win.days, win.complete), (D("2026-09-30"), 30, True))

    def test_an_unfinished_period_is_reported_to_date(self):
        win = periods.window(OCT, latest_stored=D("2026-10-04"))
        self.assertEqual((win.through, win.days, win.complete), (D("2026-10-04"), 4, False))
        self.assertEqual(win.dates(), [D("2026-10-01"), D("2026-10-02"), D("2026-10-03"), D("2026-10-04")])

    def test_nothing_stored_yet_gives_the_first_day(self):
        for latest in (None, D("2026-09-30")):
            win = periods.window(OCT, latest_stored=latest)
            self.assertEqual((win.through, win.days, win.complete), (D("2026-10-01"), 1, False))

    def test_through_overrides_what_is_stored(self):
        win = periods.window(SEP, latest_stored=D("2026-10-04"), through=D("2026-09-15"))
        self.assertEqual((win.days, win.complete), (15, False))
        with self.assertRaises(ValueError):
            periods.window(SEP, latest_stored=D("2026-10-04"), through=D("2026-10-01"))


class Comparison(unittest.TestCase):
    def test_a_whole_period_is_compared_with_the_whole_period_before(self):
        self.assertEqual(periods.prior_window(Window(SEP, SEP.end)), Window(AUG, D("2026-08-31")))

    def test_a_period_to_date_is_compared_with_the_same_number_of_days(self):
        prior = periods.prior_window(Window(OCT, D("2026-10-04")))
        self.assertEqual((prior.start, prior.through, prior.days), (D("2026-09-01"), D("2026-09-04"), 4))
        before = periods.prior_window(prior)  # and so on: the window that gives growth its own prior value
        self.assertEqual((before.start, before.through), (D("2026-08-01"), D("2026-08-04")))

    def test_a_day_is_compared_with_the_day_before(self):
        prior = periods.prior_window(periods.window(periods.parse("day", "2026-10-01"), D("2026-10-04")))
        self.assertEqual((prior.start, prior.through), (D("2026-09-30"), D("2026-09-30")))

    def test_a_week_to_date(self):
        prior = periods.prior_window(Window(W40, D("2026-09-29")))
        self.assertEqual((prior.period.id, prior.start, prior.through), ("2026-W39", D("2026-09-21"), D("2026-09-22")))

    def test_the_comparison_stops_at_the_end_of_the_period_before(self):
        march = periods.parse("month", "2026-03")
        prior = periods.prior_window(Window(march, D("2026-03-30")))
        self.assertEqual((prior.through, prior.days), (D("2026-02-28"), 28))


class Labels(unittest.TestCase):
    def test_reported_window(self):
        self.assertEqual(periods.label(Window(SEP, SEP.end)), "September 2026")
        self.assertEqual(periods.label(Window(OCT, D("2026-10-04"))), "October 2026 (to date)")
        self.assertEqual(periods.label(Window(W40, W40.end)), "Week 40, 2026")
        self.assertEqual(periods.label(Window(W40, D("2026-09-29"))), "Week 40, 2026 (to date)")
        day = periods.parse("day", "2026-10-02")
        self.assertEqual(periods.label(Window(day, day.end)), "October 2, 2026")

    def test_comparison_window(self):
        self.assertEqual(periods.comparison_label(Window(AUG, AUG.end)), "August 2026")
        self.assertEqual(periods.comparison_label(Window(SEP, D("2026-09-04"))), "September 1 to 4, 2026")
        self.assertEqual(periods.comparison_label(Window(SEP, D("2026-09-01"))), "September 1, 2026")
        self.assertEqual(periods.comparison_label(Window(W40, D("2026-10-01"))), "Sep 28 to Oct 1, 2026")
        first_week = periods.parse("week", "2026-W01")
        self.assertEqual(periods.comparison_label(Window(first_week, D("2026-01-01"))), "Dec 29, 2025 to Jan 1, 2026")


if __name__ == "__main__":
    unittest.main()
