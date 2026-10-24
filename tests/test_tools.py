"""Synthetic consistency tests; none of these fixtures is engineering evidence."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]


def load_tool(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CLAIMS_PATH = ROOT / "skills/evidence-first/scripts/check_claims.py"
DELIVERY_PATH = ROOT / "skills/industrial-evidence-first/scripts/check_delivery.py"
claims = load_tool("public_claim_checker", CLAIMS_PATH)
delivery = load_tool("public_quantity_checker", DELIVERY_PATH)


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="synthetic-evidence-")
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.root = self.folder / "evidence"
        self.root.mkdir()
        self.content = b"Synthetic width: 12 mm\nSynthetic width: 13 mm\nSynthetic test: passed\n"
        (self.root / "notes.txt").write_bytes(self.content)
        self.digest = hashlib.sha256(self.content).hexdigest()

    def reference(self, line=1):
        return {"path": "notes.txt", "sha256": self.digest, "first_line": line, "last_line": line,
                "quote": self.content.decode().splitlines()[line - 1]}

    def claim_document(self, status="observed"):
        return {"schema_version": 1, "claims": [{"id": "synthetic-claim", "text": "The note states a width.",
                "status": status, "scope": "source text only", "rationale": "Synthetic test rationale",
                "references": [self.reference()]}]}

    def registry(self, fixture=True, value="12", line=1):
        return {"schema_version": 1, "sources": [{"id": "synthetic-source", "path": "notes.txt",
                "sha256": self.digest, "line": line, "quote": self.content.decode().splitlines()[line - 1],
                "fixture": fixture, "facts": [{"item_id": "width", "value": value, "unit": "mm", "basis": "source-stated"}]}]}

    def document(self, stage="release-candidate"):
        return {"schema_version": 1, "stage": stage, "summary": "Synthetic quantity table, not a real part.",
                "items": [{"id": "width", "value": "12", "unit": "mm", "status": "source-stated",
                "evidence_ids": ["synthetic-source"]}]}

    def reject_claim(self, document):
        with self.assertRaises((claims.ClaimError, ValueError)):
            claims.validate(document, self.root)

    def reject_delivery(self, document, registry=None):
        with self.assertRaises((delivery.DeliveryError, ValueError)):
            delivery.validate(document, registry or self.registry(), self.root)


class ClaimTests(Fixture):
    def test_consistent_observation_is_not_truth_certification(self):
        result = claims.validate(self.claim_document(), self.root)
        self.assertEqual(result["references_checked"], 1)
        self.assertFalse(result["truth_certified"])

    def test_reported_status_is_preserved(self):
        document = self.claim_document("reported")
        claims.validate(document, self.root)
        self.assertEqual(document["claims"][0]["status"], "reported")

    def test_unknown_without_reference_allowed(self):
        document = self.claim_document("unknown")
        document["claims"][0]["references"] = []
        self.assertEqual(claims.validate(document, self.root)["references_checked"], 0)

    def test_unknown_still_checks_supplied_reference(self):
        document = self.claim_document("unknown")
        document["claims"][0]["references"][0]["sha256"] = "0" * 64
        self.reject_claim(document)

    def test_inference_requires_rationale(self):
        document = self.claim_document("inferred")
        document["claims"][0]["rationale"] = " "
        self.reject_claim(document)

    def test_observation_requires_source(self):
        document = self.claim_document()
        document["claims"][0]["references"] = []
        self.reject_claim(document)

    def test_blank_claim_rejected(self):
        document = self.claim_document()
        document["claims"][0]["text"] = " "
        self.reject_claim(document)

    def test_empty_document_rejected(self):
        self.reject_claim({"schema_version": 1, "claims": []})

    def test_duplicate_claim_id_rejected(self):
        document = self.claim_document()
        document["claims"].append(copy.deepcopy(document["claims"][0]))
        self.reject_claim(document)

    def test_boolean_version_rejected(self):
        document = self.claim_document()
        document["schema_version"] = True
        self.reject_claim(document)

    def test_quote_mismatch_rejected(self):
        document = self.claim_document()
        document["claims"][0]["references"][0]["quote"] = "invented result"
        self.reject_claim(document)

    def test_hash_and_quote_cannot_use_different_snapshots(self):
        document = self.claim_document()
        replacement = "Synthetic replacement: 99 mm"
        document["claims"][0]["references"][0]["quote"] = replacement
        original_read = Path.read_text
        def changing_read(path, *args, **kwargs):
            if path == self.root / "notes.txt":
                path.write_text(replacement + "\n")
                return replacement + "\n"
            return original_read(path, *args, **kwargs)
        with patch.object(Path, "read_text", changing_read):
            self.reject_claim(document)

    def test_outside_line_range_rejected(self):
        document = self.claim_document()
        document["claims"][0]["references"][0]["last_line"] = 99
        self.reject_claim(document)

    def test_parent_traversal_rejected(self):
        document = self.claim_document()
        document["claims"][0]["references"][0]["path"] = "../notes.txt"
        self.reject_claim(document)

    def test_symlink_escape_rejected(self):
        (self.folder / "outside.txt").write_bytes(self.content)
        (self.root / "escape.txt").symlink_to(self.folder / "outside.txt")
        document = self.claim_document()
        document["claims"][0]["references"][0]["path"] = "escape.txt"
        self.reject_claim(document)

    def test_conflict_requires_distinct_locations(self):
        document = self.claim_document("conflict")
        document["claims"][0]["references"] *= 2
        self.reject_claim(document)

    def test_conflict_can_preserve_distinct_sources(self):
        document = self.claim_document("conflict")
        document["claims"][0]["references"] = [self.reference(), self.reference(2)]
        self.assertEqual(claims.validate(document, self.root)["references_checked"], 2)


class DeliveryTests(Fixture):
    def test_synthetic_evidence_never_passes_gate(self):
        result = delivery.validate(self.document(), self.registry(), self.root)
        self.assertEqual(result["evidence_gate"], "hold")
        self.assertFalse(result["engineering_certified"])
        self.assertFalse(result["publication_authorized"])

    def test_supported_gate_branch_is_not_engineering_approval(self):
        # A synthetic fixture deliberately exercises fixture=False. It is not real evidence.
        result = delivery.validate(self.document(), self.registry(fixture=False), self.root)
        self.assertEqual(result["evidence_gate"], "pass")
        self.assertFalse(result["engineering_certified"])

    def test_draft_never_passes_gate(self):
        result = delivery.validate(self.document("draft"), self.registry(fixture=False), self.root)
        self.assertEqual(result["evidence_gate"], "hold")

    def test_empty_summary_rejected(self):
        document = self.document()
        document["summary"] = " "
        self.reject_delivery(document)

    def test_empty_items_rejected(self):
        document = self.document()
        document["items"] = []
        self.reject_delivery(document)

    def test_missing_unit_not_defaulted(self):
        document = self.document()
        document["items"][0]["unit"] = None
        self.reject_delivery(document)

    def test_different_unit_not_silently_converted(self):
        document = self.document()
        document["items"][0]["unit"] = "m"
        self.reject_delivery(document)

    def test_numeric_mismatch_rejected(self):
        document = self.document()
        document["items"][0]["value"] = "99"
        self.reject_delivery(document)

    def test_equivalent_decimal_spelling_matches(self):
        document = self.document()
        document["items"][0]["value"] = "12.0"
        self.assertTrue(delivery.validate(document, self.registry(), self.root)["structural_ok"])

    def test_numeric_json_instead_of_string_rejected(self):
        document = self.document()
        document["items"][0]["value"] = 12
        self.reject_delivery(document)

    def test_nonfinite_quantity_rejected(self):
        document = self.document()
        document["items"][0]["value"] = "NaN"
        self.reject_delivery(document)

    def test_unknown_with_broken_reference_rejected(self):
        document = self.document()
        document["items"][0].update(status="unknown", value=None, unit=None, notes="No unit evidence", evidence_ids=["missing"])
        self.reject_delivery(document)

    def test_unknown_without_reference_holds_gate(self):
        document = self.document()
        document["items"][0].update(status="unknown", value=None, unit=None, notes="No evidence", evidence_ids=[])
        result = delivery.validate(document, {"schema_version": 1, "sources": []}, self.root)
        self.assertEqual(result["evidence_gate"], "hold")

    def test_estimate_requires_notes_and_holds_gate(self):
        document = self.document()
        document["items"][0].update(status="estimated", evidence_ids=[], notes="Synthetic assumption")
        self.assertEqual(delivery.validate(document, self.registry(), self.root)["evidence_gate"], "hold")
        document["items"][0]["notes"] = ""
        self.reject_delivery(document)

    def test_measured_requires_method_and_date(self):
        document, registry = self.document(), self.registry()
        document["items"][0]["status"] = "measured"
        registry["sources"][0]["facts"][0]["basis"] = "measured"
        self.reject_delivery(document, registry)
        registry["sources"][0]["facts"][0].update(method="Synthetic bench", measured_on="2000-01-01")
        self.assertTrue(delivery.validate(document, registry, self.root)["structural_ok"])

    def test_measured_invalid_date_rejected(self):
        document, registry = self.document(), self.registry()
        document["items"][0]["status"] = "measured"
        registry["sources"][0]["facts"][0].update(basis="measured", method="Synthetic bench", measured_on="2000-02-31")
        self.reject_delivery(document, registry)

    def test_conflict_requires_different_facts(self):
        document = self.document()
        document["items"][0].update(status="conflict", value=None, unit=None, notes="Two synthetic notes disagree")
        self.reject_delivery(document)
        registry = self.registry()
        other = self.registry(value="13", line=2)["sources"][0]
        other["id"] = "synthetic-source-two"
        registry["sources"].append(other)
        document["items"][0]["evidence_ids"].append(other["id"])
        self.assertEqual(delivery.validate(document, registry, self.root)["evidence_gate"], "hold")

    def test_unused_registry_reference_still_checked(self):
        registry = self.registry()
        other = copy.deepcopy(registry["sources"][0])
        other.update(id="unused", sha256="0" * 64)
        registry["sources"].append(other)
        self.reject_delivery(self.document(), registry)

    def test_registry_quote_mismatch_rejected(self):
        registry = self.registry()
        registry["sources"][0]["quote"] = "not in file"
        self.reject_delivery(self.document(), registry)

    def test_hash_and_quote_cannot_use_different_snapshots(self):
        registry = self.registry()
        replacement = "Synthetic replacement: 99 mm"
        registry["sources"][0]["quote"] = replacement
        original_read = Path.read_text
        def changing_read(path, *args, **kwargs):
            if path == self.root / "notes.txt":
                path.write_text(replacement + "\n")
                return replacement + "\n"
            return original_read(path, *args, **kwargs)
        with patch.object(Path, "read_text", changing_read):
            self.reject_delivery(self.document(), registry)

    def test_source_fact_cannot_bind_another_item(self):
        registry = self.registry()
        registry["sources"][0]["facts"][0]["item_id"] = "height"
        self.reject_delivery(self.document(), registry)


class CliTests(Fixture):
    def test_cli_exit_codes_and_no_file_mutation(self):
        claim_file, doc_file, reg_file = [self.folder / n for n in ("claims.json", "document.json", "registry.json")]
        claim_file.write_text(json.dumps(self.claim_document()))
        doc_file.write_text(json.dumps(self.document("draft")))
        reg_file.write_text(json.dumps(self.registry()))
        def snapshot():
            return {str(p.relative_to(self.folder)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in self.folder.rglob("*") if p.is_file()}
        before = snapshot()
        claim_cmd = [sys.executable, str(CLAIMS_PATH), str(claim_file), "--root", str(self.root)]
        delivery_cmd = [sys.executable, str(DELIVERY_PATH), str(doc_file), "--registry", str(reg_file), "--root", str(self.root)]
        ok = subprocess.run(claim_cmd, capture_output=True, text=True)
        held = subprocess.run(delivery_cmd + ["--require-gate"], capture_output=True, text=True)
        normal_draft = subprocess.run(delivery_cmd, capture_output=True, text=True)
        self.assertEqual((ok.returncode, held.returncode, normal_draft.returncode), (0, 2, 0))
        self.assertEqual(before, snapshot())

    def test_duplicate_json_key_cli_rejected(self):
        malformed = self.folder / "duplicate.json"
        malformed.write_text('{"schema_version":1,"schema_version":2,"claims":[]}')
        result = subprocess.run([sys.executable, str(CLAIMS_PATH), str(malformed), "--root", str(self.root)], capture_output=True)
        self.assertEqual(result.returncode, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
