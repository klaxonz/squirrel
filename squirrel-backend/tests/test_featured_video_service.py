import unittest

from domains.video.application.services.featured import order_featured_video_ids


class FeaturedVideoServiceTest(unittest.TestCase):
    def test_stable_featured_candidate_order_is_repeatable(self) -> None:
        self.assertEqual(order_featured_video_ids([9, 2, 7], stable=True), [2, 7, 9])
