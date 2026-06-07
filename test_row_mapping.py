import unittest

from app import row_to_dict, rows_to_dicts


class FakeCursor:
	description = [("id",), ("title",), ("cnt",)]


class RowMappingTest(unittest.TestCase):
	def test_tuple_row_maps_with_cursor_description(self):
		self.assertEqual(
			row_to_dict((1, "poem", 3), FakeCursor()),
			{"id": 1, "title": "poem", "cnt": 3},
		)

	def test_tuple_rows_map_with_cursor_description(self):
		self.assertEqual(
			rows_to_dicts([(1, "poem", 3), (2, "ci", 4)], FakeCursor()),
			[
				{"id": 1, "title": "poem", "cnt": 3},
				{"id": 2, "title": "ci", "cnt": 4},
			],
		)


if __name__ == "__main__":
	unittest.main()
