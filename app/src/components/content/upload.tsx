import "preact";
import { useContext, useRef, useState, useEffect } from "preact/hooks";
import "ojs/ojtoolbar";
import "oj-c/file-picker";
import "oj-c/message-toast";
import "oj-c/progress-bar";
import "oj-c/button";
import MutableArrayDataProvider = require("ojs/ojmutablearraydataprovider");
import { CFilePickerElement } from "oj-c/file-picker";
import { CButtonElement } from "oj-c/button";
import { ConvoCtx } from "../app";
import { debugLog } from "../../libs/debug";
import { setKv, deleteKv } from "../../libs/memory";

type Props = {
  backendType: "java";
  modelId: string | null;
};

const acceptArr: string[] = ["application/pdf", "*.pdf"];
// Client-side limit aligned with backend: 100 MB
const FILE_SIZE = 100 * 1024 * 1024;

export const Upload = ({ backendType, modelId }: Props) => {
  const conversationId = useContext(ConvoCtx);

  const [fileNames, setFileNames] = useState<string[] | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const [messages, setMessages] = useState<
    { id: number; severity: "Info" | "Error" | "Warning" | "Confirmation"; summary: string }[]
  >([]);
  const messagesDP = new MutableArrayDataProvider<number, { id: number; severity: string; summary: string }>(
    messages,
    { keyAttributes: "id" }
  );

  const closeMessage = () => setMessages([]);

  const beforeSelectListener = (event: CFilePickerElement.ojBeforeSelect) => {
    const accept: (acceptPromise: Promise<void>) => void = event.detail.accept;
    const files: FileList = event.detail.files;
    // Enforce type and size early
    const f = files[0];
    if (!f) {
      accept(Promise.reject());
      return;
    }
    if (!(f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf"))) {
      setMessages([{ id: 1, severity: "Error", summary: "Only PDF files are supported." }]);
      accept(Promise.reject());
      return;
    }
    if (f.size > FILE_SIZE) {
      setMessages([
        {
          id: 2,
          severity: "Error",
          summary: `File "${f.name}" is too big. Maximum size is ${Math.round(FILE_SIZE / (1024 * 1024))}MB.`,
        },
      ]);
      accept(Promise.reject());
      return;
    }
    accept(Promise.resolve());
  };

  const invalidListener = (event: CFilePickerElement.ojInvalidSelect) => {
    const until = event.detail.until;
    if (until) until.then(() => void 0);
  };

  const selectListener = async (event: CFilePickerElement.ojSelect) => {
    const files: FileList = event.detail.files;
    if (!files || files.length === 0) {
      setFile(null);
      setFileNames(null);
      return;
    }
    setFile(files[0]);
    setFileNames([files[0].name]);
    setMessages([]);
    try {
      await setKv(conversationId, 'pendingUpload', { name: files[0].name, size: files[0].size, lastModified: files[0].lastModified }, 300);
    } catch (e) {
      // non-blocking
    }
  };

  const doUpload = async (_ev: CButtonElement.ojAction) => {
    if (!file) {
      setMessages([{ id: 4, severity: "Error", summary: "Please select a PDF file to upload." }]);
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);

      const headers: Record<string, string> = {
        conversationID: conversationId,
        // Enable KB ingestion during upload for RAG
        "X-RAG-Ingest": "true",
        // Use same tenant as RAG queries (defaults to "default")
        "X-Tenant-Id": "default"
        // Optionally set "Embedding-Model-Id" if you want to override server default (1024-dim)
      };
      if (modelId) headers["modelId"] = modelId;

      const res = await fetch("/api/upload", {
        method: "POST",
        body: formData,
        headers
      });

      if (!res.ok) {
        // Try to read JSON error if provided by Spring
        let detail = `${res.status} ${res.statusText}`;
        try {
          const json = await res.json();
          if (json?.error) detail = `${res.status} ${json.error}`;
        } catch {
          // ignore
        }
        throw new Error(`Upload failed: ${detail}`);
      }

      const json = await res.json();
      // Controller returns Answer { content, errorMessage }
      const content = json?.content ?? "";
      const errorMessage = json?.errorMessage ?? "";
      if (errorMessage) {
        setMessages([{ id: 6, severity: "Error", summary: `Server error: ${errorMessage}` }]);
      } else {
        setMessages([{ id: 7, severity: "Confirmation", summary: "Upload successful. You can now use RAG to ask about this document." }]);
        try {
          await deleteKv(conversationId, 'pendingUpload');
        } catch (e) {
          // non-blocking
        }
        // Auto-run KB diagnostics after a successful upload and log to console
        try {
          const diagRes = await fetch("/api/kb/diag?tenantId=default");
          if (diagRes.ok) {
            const diag = await diagRes.json();
            debugLog("KB DIAG after upload:", diag);
          } else {
            console.warn("KB DIAG after upload failed:", diagRes.status, diagRes.statusText);
          }
        } catch (e) {
          console.warn("KB DIAG after upload errored:", e);
        }
      }
    } catch (e: any) {
      setMessages([{ id: 8, severity: "Error", summary: e?.message || "Upload failed." }]);
    } finally {
      setLoading(false);
    }
  };

  const clearSelection = async (_ev: CButtonElement.ojAction) => {
    setFile(null);
    setFileNames(null);
    setMessages([]);
    setLoading(false);
    try {
      await deleteKv(conversationId, 'pendingUpload');
    } catch (e) {
      // non-blocking
    }
  };

  useEffect(() => {
    // no-op for now
  }, []);

  return (
    <>
      <oj-c-message-toast data={messagesDP} onojClose={closeMessage}></oj-c-message-toast>

      <div class="oj-flex-item oj-sm-margin-4x">
        <h1>RAG Knowledge Base</h1>
        <div class="oj-typography-body-md oj-sm-padding-1x-bottom">
          Upload a PDF to add it to your knowledge base. The backend will ingest and index it for RAG.
        </div>

        <oj-c-file-picker
          id="filepickerUpload"
          accept={acceptArr}
          selectionMode="single"
          onojBeforeSelect={beforeSelectListener}
          onojInvalidSelect={invalidListener}
          onojSelect={selectListener}
          secondaryText={`Maximum file size is ${Math.round(FILE_SIZE / (1024 * 1024))}MB.`}
        ></oj-c-file-picker>

        {fileNames && (
          <>
            <div class="oj-sm-margin-4x-top">
              <span class="oj-typography-bold">File: </span>
              {fileNames.join(", ")}
            </div>
            <oj-toolbar class="oj-sm-margin-6x-top" aria-label="upload toolbar" aria-controls="uploadContent">
              <oj-c-button label="Upload" disabled={!file || loading} onojAction={doUpload}></oj-c-button>
              <oj-c-button label="Clear" disabled={loading} onojAction={clearSelection}></oj-c-button>
            </oj-toolbar>
          </>
        )}

        {loading && (
          <>
            <div class="oj-sm-margin-4x oj-typography-subheading-md">Uploading...</div>
            <oj-c-progress-bar class="oj-sm-margin-4x oj-sm-width-full oj-md-width-1/2" value={-1}></oj-c-progress-bar>
          </>
        )}

        <div id="uploadContent" class="oj-sm-margin-6x-top oj-typography-body-sm oj-text-color-secondary">
          Tip: After a successful upload, enable RAG in Settings and ask a question about your document in Chat.
        </div>
      </div>
    </>
  );
};
