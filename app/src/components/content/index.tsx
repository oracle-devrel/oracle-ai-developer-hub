import { Chat } from "./chat";
import { Summary } from "./summary";
import { Settings } from "./settings";
import { Upload } from "./upload";
import "preact";
import "ojs/ojinputsearch";
import "oj-c/message-toast";
import "oj-c/drawer-popup";
import "oj-c/select-single";
import "ojs/ojlistitemlayout";
import "ojs/ojhighlighttext";
import MutableArrayDataProvider = require("ojs/ojmutablearraydataprovider");
import { MessageToastItem } from "oj-c/message-toast";
import { InputSearchElement } from "ojs/ojinputsearch";
import { useState, useEffect, useRef, useContext } from "preact/hooks";

import { InitStomp, sendPrompt } from "./stomp-interface";
import { Client } from "@stomp/stompjs";
import { ConvoCtx } from "../app";
import { ojSelectSingle } from "@oracle/oraclejet/ojselectsingle";

type ServiceTypes = "text" | "summary" | "upload";
type Chat = {
  id?: number;
  question?: string;
  answer?: string;
  loading?: string;
};
type Model = {
  id: string;
  name: string;
  vendor: string;
  version: string;
  capabilities: Array<string>;
  timeCreated: string;
};

type Endpoint = {
  id: string;
  name: string;
  state: string;
  model: string;
  timeCreated: string;
};

const defaultServiceType: string = localStorage.getItem("service") || "text";
const backendType: "java" = "java";

type ContentProps = {
  settingsOpened: boolean;
  setSettingsOpened: (opened: boolean) => void;
  theme: string;
  setTheme: (theme: string) => void;
  language: string;
  setLanguage: (language: string) => void;
};

const Content = ({ settingsOpened, setSettingsOpened, theme, setTheme, language, setLanguage }: ContentProps) => {
  const conversationId = useContext(ConvoCtx);
  const [update, setUpdate] = useState<Array<object>>([]);
  const [busy, setBusy] = useState<boolean>(false);
  const [summaryResults, setSummaryResults] = useState<string>("");
  const [modelId, setModelId] = useState<string | null>(null);
  const [summaryPrompt, setSummaryPrompt] = useState<string>();
  const [serviceType, setServiceType] = useState<ServiceTypes>(
    defaultServiceType as ServiceTypes
  );
  const [ragEnabled, setRagEnabled] = useState<boolean>(false);
  const [questionText, setQuestionText] = useState<string>("");
  const chatData = useRef<Array<object>>([]);
  const finetune = useRef<boolean>(false);
  const [client, setClient] = useState<Client | null>(null);

  // Top-level model selector state
  const modelDP = useRef(new MutableArrayDataProvider<string, {}>([], { keyAttributes: "id" }));
  const endpoints = useRef<Array<Endpoint>>();
  const [selectedModelId, setSelectedModelId] = useState<string | null>(modelId);
  const [modelsLoaded, setModelsLoaded] = useState<boolean>(false);

  const messagesDP = useRef(
    new MutableArrayDataProvider<MessageToastItem["summary"], MessageToastItem>(
      [],
      { keyAttributes: "summary" }
    )
  );



  useEffect(() => {
    switch (serviceType) {
      case "text":
        setClient(
          InitStomp(setBusy, setUpdate, messagesDP, chatData, serviceType)
        );
        console.log("Running Generative service");
        return;
      case "summary":
        setClient(
          InitStomp(setBusy, setUpdate, messagesDP, chatData, serviceType)
        );
        console.log("Running Summarization service");
        return;
    }
    return () => {
      client?.deactivate();
    };
  }, [serviceType]);

  const handleQuestionChange = (question: string) => {
    const modifiedQuestion = language === "english" ? question : `Respond in ${language}: ${question}`;
    // if we are waiting for an answer to be returned, throw an alert and return
    if (busy) {
      messagesDP.current.data = [
        {
          summary: "Still waiting for an answer!",
          detail: "Hang in there a little longer.",
          autoTimeout: "on",
        },
      ];
      return;
    }
    if (question) {
      let tempArray = [...chatData.current];
      tempArray.push({
        id: tempArray.length as number,
        question: question,
      });
      chatData.current = tempArray;
      setUpdate(chatData.current);

      // adding loading animation while we wait for answer to come back
      let tempAnswerArray = [...chatData.current];
      tempAnswerArray.push({
        id: tempAnswerArray.length as number,
        loading: "loading",
      });
      chatData.current = tempAnswerArray;
      setUpdate(chatData.current);
      setBusy(true);

      if (ragEnabled) {
        // Use RAG endpoint for Java backend when RAG is enabled
        fetch("/api/genai/rag", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            question: modifiedQuestion,
            tenantId: "default",
            conversationId: conversationId,
            language: language
          }),
        })
          .then((response) => response.text())
          .then((answer) => {
            let tempArray = [...chatData.current];
            // Remove loading indicator
            tempArray.pop();
            // Add the answer
            tempArray.push({
              id: tempArray.length as number,
              answer: answer,
            });
            chatData.current = tempArray;
            setUpdate(chatData.current);
            setBusy(false);
          })
          .catch((error) => {
            console.error("RAG request failed:", error);
            let tempArray = [...chatData.current];
            tempArray.pop(); // Remove loading
            tempArray.push({
              id: tempArray.length as number,
              answer: "Sorry, I encountered an error while processing your question with RAG.",
            });
            chatData.current = tempArray;
            setUpdate(chatData.current);
            setBusy(false);
          });
      } else {
        sendPrompt(
          client,
          modifiedQuestion,
          modelId!,
          conversationId!,
          finetune.current
        );
      }

      // Clear the input field after question is published
      setQuestionText("");
    }
  };

  const handleFileUpload = (_file: ArrayBuffer | Uint8Array) => {
    // no-op in Java-only mode
  };

  const handleDrawerState = () => {
    setSettingsOpened(false);
  };
  const toggleDrawer = () => {
    setSettingsOpened(!settingsOpened);
  };
  const handleToastClose = () => {
    messagesDP.current.data = [];
  };

  const serviceTypeChangeHandler = (service: ServiceTypes) => {
    localStorage.setItem("service", service);
    setUpdate([]);
    chatData.current = [];
    setServiceType(service);
  };
  const backendTypeChangeHandler = (_backend: any) => {
    // Java-only: backend type is fixed to Java
  };
  const modelIdChangeHandler = (value: string, modelType: boolean) => {
    if (value != null) setModelId(value);
    finetune.current = modelType;
  };
  const clearSummary = () => {
    setSummaryResults("");
  };

  const updateSummaryPrompt = (val: string) => {
    setSummaryPrompt(val);
  };
  const updateSummaryResults = (summary: string) => {
    setSummaryResults(summary);
  };

  // Model selector support (top-level)
  const fetchModels = async (retries = 3) => {
    for (let attempt = 1; attempt <= retries; attempt++) {
      try {
        const primaryUrl = "/api/genai/models";

        let response: Response;
        try {
          response = await fetch(primaryUrl);
          if (!response.ok) throw new Error(`Response status: ${response.status}`);
        } catch (e) {
          throw e;
        }
        const json = await response.json();
        const result = json.filter(
          (m: Model) =>
            m.capabilities.includes("CHAT") &&
            (m.vendor === "cohere" || m.vendor === "meta" || m.vendor === "xai")
        );
        (modelDP.current as any).data = result;
        setModelsLoaded(true);
        return;
      } catch (error: any) {
        if (attempt === retries) {
          (modelDP.current as any).data = [];
          setModelsLoaded(true);
        } else {
          await new Promise((r) => setTimeout(r, 1000));
        }
      }
    }
  };

  const fetchEndpoints = async () => {
    try {
      const res = await fetch("/api/genai/endpoints");
      if (!res.ok) throw new Error(`Response status: ${res.status}`);
      const json = await res.json();
      endpoints.current = json;
    } catch {
      // ignore
    }
  };

  const modelTemplate = (item: any) => {
    return (
      <oj-list-item-layout class="oj-listitemlayout-padding-off">
        <span class="oj-typography-body-md oj-text-color-primary">
          <oj-highlight-text
            text={item.item.data.name}
            match-text={item.searchText}
          ></oj-highlight-text>
        </span>
        <span slot="secondary" class="oj-typography-body-sm oj-text-color-secondary">
          <oj-highlight-text
            text={JSON.stringify(item.item.data.capabilities)}
            match-text={item.searchText}
          ></oj-highlight-text>
        </span>
      </oj-list-item-layout>
    );
  };

  const modelChangeHandler = async (
    event: ojSelectSingle.valueChanged<string, {}>
  ) => {
    let selected = event.detail.value;
    let finetuned = false;

    const asyncIterator = (modelDP.current as any).fetchFirst()[Symbol.asyncIterator]();
    let result = await asyncIterator.next();
    let data = (result.value?.data as Array<Model>) || [];
    const model = data.find((e: Model) => e.id === selected);
    if (model?.capabilities.includes("FINE_TUNE")) {
      finetuned = true;
      const endpointId = endpoints.current?.find((e: Endpoint) => e.model === selected)?.id;
      selected = endpointId ? endpointId : selected;
    }
    setSelectedModelId(selected as string);
    modelIdChangeHandler(selected as string, finetuned);
  };

  async function ensureDefaultModel() {
    try {
      if (modelId || selectedModelId) return;
      const asyncIterator = (modelDP.current as any).fetchFirst()[Symbol.asyncIterator]();
      const result = await asyncIterator.next();
      const data = (result.value?.data as Array<Model>) || [];
      if (data.length === 0) return;

      let defaultId: string | null = null;
      if (backendType === "java") {
        try {
          const res = await fetch("/api/genai/default-model");
          if (res.ok) {
            const json = await res.json();
            if (json?.modelId) defaultId = json.modelId as string;
          }
        } catch {}
      }
      let chosen =
        defaultId && data.find((m) => m.id === defaultId) ? (defaultId as string) : data[0].id;

      let finetuned = false;
      const idx = data.find((e: Model) => e.id === chosen);
      if (idx?.capabilities.includes("FINE_TUNE")) {
        const endpointId = endpoints.current?.find((e: Endpoint) => e.model === chosen)?.id;
        if (endpointId) chosen = endpointId;
        finetuned = true;
      }

      setSelectedModelId(chosen);
      modelIdChangeHandler(chosen, finetuned);
    } catch {}
  }

  useEffect(() => {
    fetchEndpoints();
    fetchModels();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);


  useEffect(() => {
    if (modelsLoaded && !modelId && !selectedModelId) {
      ensureDefaultModel();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modelsLoaded, modelId, selectedModelId]);

  return (
    <div class="oj-web-applayout-max-width oj-web-applayout-content oj-flex oj-sm-flex-direction-column demo-bg-main">
      <oj-c-drawer-popup
        edge="end"
        opened={settingsOpened}
        onojBeforeClose={handleDrawerState}
        aria-label="Settings Drawer"
      >
        <Settings
          aiServiceType={serviceType}
          ragEnabled={ragEnabled}
          theme={theme}
          aiServiceChange={serviceTypeChangeHandler}
          ragToggle={setRagEnabled}
          themeChange={setTheme}
          modelIdChange={modelIdChangeHandler}
          onLanguageChange={setLanguage}
        />
      </oj-c-drawer-popup>
      <div class="oj-flex-bar oj-flex-item demo-header oj-sm-12">
        <oj-c-message-toast
          data={messagesDP.current}
          position="top"
          onojClose={handleToastClose}
        ></oj-c-message-toast>
      </div>
      {serviceType === "text" && (
        <div class="oj-sm-margin-4x">
          <h2 class="oj-typography-heading-sm">Model</h2>
          <oj-c-form-layout>
            <oj-c-select-single
              data={modelDP.current}
              labelHint={"Model"}
              itemText={"name"}
              value={selectedModelId as any}
              onvalueChanged={modelChangeHandler}
            >
              <template slot="itemTemplate" render={modelTemplate}></template>
            </oj-c-select-single>
          </oj-c-form-layout>
        </div>
      )}
      {serviceType === "text" && (
        <Chat
          data={update}
          questionValue={questionText}
          onQuestionValueChange={setQuestionText}
          onQuestionSubmit={handleQuestionChange}
          settingsOpened={settingsOpened}
        />
      )}

      {serviceType === "summary" && (
        <Summary
          fileChanged={handleFileUpload}
          summaryChanged={updateSummaryResults}
          summary={summaryResults}
          clear={clearSummary}
          prompt={updateSummaryPrompt}
          modelId={modelId}
        />
      )}
      {serviceType === "upload" && (
        <Upload backendType={backendType} modelId={modelId} />
      )}
    </div>
  );
};
export default Content;
