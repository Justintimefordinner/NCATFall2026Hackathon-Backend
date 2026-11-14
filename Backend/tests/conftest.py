"""Tests run against a fixed copy of the instructions (tests/op_test.json), so
editing the real data/op10.json never breaks them. Must run before config is imported."""
import os

os.environ["MES_DATA"] = os.path.join(os.path.dirname(__file__), "op_test.json")
