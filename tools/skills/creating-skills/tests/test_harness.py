import inspect
import unittest

from scripts.adapters import available_harnesses, get_harness
from scripts.harness import Harness


class HarnessContractTests(unittest.TestCase):
    def test_protocol_exposes_exactly_three_capabilities(self) -> None:
        capabilities = {
            name
            for name, _ in inspect.getmembers(Harness, inspect.isfunction)
            if not name.startswith("_")
        }

        self.assertEqual(capabilities, {"prepare_scope", "run", "probe_trigger"})

    def test_registry_selects_the_opencode_adapter_by_name(self) -> None:
        harness = get_harness("opencode")

        self.assertIsInstance(harness, Harness)
        self.assertEqual(available_harnesses(), ("opencode",))

    def test_registry_rejects_an_unknown_adapter(self) -> None:
        with self.assertRaisesRegex(ValueError, "available: opencode"):
            get_harness("unknown-harness")
