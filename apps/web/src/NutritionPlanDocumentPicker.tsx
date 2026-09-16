import { useRef, useState } from "react";

import { ApiError } from "./api/client";
import { extractNutritionPlanDocument } from "./api/nutritionPlanImportClient";
import type { NutritionPlanDocumentExtraction } from "./api/nutritionPlanImportTypes";
import { useI18n } from "./i18n";

const COPY = {
  "pt-PT": {
    label: "Documento",
    choose: "Escolher PDF, Word ou texto",
    extracting: "A extrair texto…",
    supported: "PDF com texto, DOCX, TXT ou Markdown · máximo 10 MB",
    extracted: "Texto extraído",
    characters: "caracteres",
    scanned:
      "PDF digitalizado/fotografia ainda não tem OCR neste fluxo. O ficheiro deve conter texto selecionável.",
    genericError: "Não foi possível extrair o documento.",
  },
  en: {
    label: "Document",
    choose: "Choose PDF, Word or text",
    extracting: "Extracting text…",
    supported: "Text PDF, DOCX, TXT or Markdown · maximum 10 MB",
    extracted: "Text extracted",
    characters: "characters",
    scanned:
      "Scanned PDF/photo OCR is not yet enabled in this flow. The file must contain selectable text.",
    genericError: "Could not extract the document.",
  },
} as const;

function errorText(error: unknown, fallback: string): string {
  if (error instanceof ApiError) return `${error.message} (HTTP ${error.status})`;
  if (error instanceof Error) return error.message;
  return fallback;
}

export default function NutritionPlanDocumentPicker({
  personId,
  onExtracted,
}: {
  personId: string;
  onExtracted: (result: NutritionPlanDocumentExtraction) => void;
}) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<NutritionPlanDocumentExtraction | null>(null);

  async function selectFile(file: File | null) {
    if (!file) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const extracted = await extractNutritionPlanDocument(personId, file);
      setResult(extracted);
      onExtracted(extracted);
    } catch (caught: unknown) {
      setError(errorText(caught, copy.genericError));
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div className="nutrition-import__document">
      <div className="nutrition-import__document-copy">
        <strong>{copy.label}</strong>
        <span>{copy.supported}</span>
      </div>
      <input
        ref={inputRef}
        accept=".pdf,.docx,.txt,.md,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown"
        className="nutrition-import__file-input"
        disabled={busy}
        onChange={(event) => void selectFile(event.target.files?.[0] ?? null)}
        type="file"
      />
      <button
        className="button ghost"
        disabled={busy}
        onClick={() => inputRef.current?.click()}
        type="button"
      >
        {busy ? copy.extracting : copy.choose}
      </button>
      {result ? (
        <div className="nutrition-import__document-result">
          <strong>{copy.extracted}: {result.filename}</strong>
          <span>{result.character_count.toLocaleString(locale)} {copy.characters}</span>
          {result.warnings.map((warning) => (
            <span key={warning}>{warning}</span>
          ))}
        </div>
      ) : null}
      {error ? <div className="error-banner" role="alert"><span>{error}</span></div> : null}
      <small className="nutrition-import__hint">{copy.scanned}</small>
    </div>
  );
}
