# ADR-040 — Nutrition plan document extraction feeds the existing review boundary

## Status

Accepted.

## Context

NutriFlow already accepts pasted nutrition-plan text through `NutritionPlanImportSession` and requires every parsed proposal to be explicitly reviewed before materialization and activation.

Real professional plans frequently arrive as PDF or Word documents. Supporting those files should reduce manual copying without introducing a second trust path where document parsing could create active professional guidance directly.

Document extraction also has failure modes that are materially different from text interpretation: unsupported formats, encrypted files, scanned/image-only PDFs, very large documents and extraction libraries that return empty or partial text.

## Decision

Document ingestion is a text-extraction adapter in front of the existing nutrition-plan import/review boundary.

```text
PDF / DOCX / TXT / Markdown
-> bounded server-side text extraction
-> extracted text shown in the existing editable source-text field
-> deterministic or AI interpretation
-> explicit proposal review
-> apply confirmed proposals to draft NutritionPlan
-> separate activation
```

The extraction endpoint does not create a `NutritionPlan`, `NutritionConstraint`, `NutritionPlanGuideline` or active rule. It only returns extracted text and source metadata.

### Supported document inputs

The first adapter supports:

- PDF with selectable text;
- DOCX paragraphs and table cell text;
- UTF-8 TXT;
- UTF-8 Markdown.

The server enforces bounded processing:

- maximum upload size: 10 MB;
- maximum PDF pages: 60;
- maximum extracted text: 100,000 characters.

### Fail-closed behavior

Extraction fails explicitly for:

- unsupported file types;
- empty files;
- encrypted/protected PDFs;
- PDFs with no extractable text;
- malformed/corrupt documents;
- extracted output that is empty after normalization;
- documents exceeding configured limits.

A scanned or image-only PDF is not treated as an empty but successful import. OCR/vision is a separate future adapter and must return to the same editable text/review boundary.

### Provenance

The source filename is returned to the browser and may populate the import source reference when the user has not already supplied one.

The extracted text remains editable before interpretation. The user can correct extraction defects before creating parser proposals.

### Security and operational scope

Extraction happens in memory for this v1 slice. Uploaded files are not persisted as authoritative plan artefacts by the extraction endpoint.

Document parsing libraries are treated as untrusted-input decoders: inputs are size/page bounded and parser exceptions become controlled client-visible errors rather than partial rule creation.

## Consequences

Positive:

- professional PDF/DOCX plans enter the same trusted workflow as pasted text;
- the user can inspect and correct extracted text before interpretation;
- document parsing cannot bypass proposal review or plan activation;
- malformed, encrypted and scanned documents fail visibly rather than producing guessed guidance;
- OCR/photo support can be added later without changing downstream plan semantics.

Trade-offs:

- image-only PDFs and photographs are not yet supported;
- extraction does not preserve rich document layout as a first-class artefact;
- very large documents are intentionally rejected rather than processed opportunistically.
